"""
Echoes Data Pipeline — Pipeline Orchestrator

The main end-to-end pipeline that orchestrates all four components:
  1. SCRAPE  → Pull retrospective content from Reddit
  2. CLASSIFY → Heuristic filter + LLM classification
  3. TAG → Extract structured metadata from classified stories
  4. EMBED & STORE → Chunk, embed, and upsert into Qdrant

Each stage operates on SQLite status fields, making the pipeline
fully resumable. If it crashes at any point, restarting picks up
exactly where it left off.
"""

from __future__ import annotations

import asyncio
import sys
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
)
from rich.table import Table

from classifiers.heuristic_filter import HeuristicFilter
from classifiers.llm_classifier import LLMClassifier
from config.logging_config import get_logger
from config.settings import Settings
from llm.base_client import BaseLLMClient
from llm.gemini_client import GeminiClient
from processors.chunker import TextChunker
from processors.embedder import EmbeddingGenerator
from processors.tagger import StoryTagger
from scrapers.reddit_scraper import RedditScraper
from storage.models import PipelineStats, PipelineStatus
from storage.qdrant_store import QdrantStore
from storage.sqlite_store import SQLiteStore

logger = get_logger(__name__)
console = Console()


class PipelineOrchestrator:
    """Orchestrates the complete Echoes data pipeline.

    Coordinates scraping, classification, tagging, and embedding/storage
    in a resumable, status-driven flow.

    Args:
        settings: Application settings.
    """

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.stats = PipelineStats()

        # ── Initialize components ──
        self.store = SQLiteStore(settings.pipeline.staging_db_path)
        self.heuristic = HeuristicFilter(settings.pipeline.heuristic_min_score)
        self.llm_client: BaseLLMClient = GeminiClient(settings.gemini)
        self.classifier = LLMClassifier(
            self.llm_client, self.store, settings.pipeline.llm_batch_size
        )
        self.tagger = StoryTagger(
            self.llm_client, self.store, settings.pipeline.llm_batch_size
        )
        self.chunker = TextChunker(settings.pipeline)
        self.embedder = EmbeddingGenerator(settings.gemini)

        # Qdrant (optional — may fail if Docker isn't running)
        self._qdrant: Optional[QdrantStore] = None

    @property
    def qdrant(self) -> QdrantStore:
        """Lazy-initialize Qdrant connection."""
        if self._qdrant is None:
            self._qdrant = QdrantStore(
                self.settings.qdrant,
                vector_size=3072,  # gemini-embedding-001 dimensions
            )
            self._qdrant.ensure_collection()
        return self._qdrant

    # ──────────────────────────────────────────
    # Full pipeline
    # ──────────────────────────────────────────

    async def run(
        self,
        scrape: bool = True,
        classify: bool = True,
        tag: bool = True,
        embed: bool = True,
    ) -> PipelineStats:
        """Execute the full pipeline (or selected stages).

        Each stage can be toggled independently. Useful for re-running
        only classification after tweaking the heuristic, for example.

        Args:
            scrape: Whether to run the scraping stage.
            classify: Whether to run classification (heuristic + LLM).
            tag: Whether to run metadata extraction.
            embed: Whether to run embedding and Qdrant storage.

        Returns:
            PipelineStats with aggregate counts from all stages.
        """
        console.print(
            Panel(
                "[bold cyan]Echoes Data Pipeline[/]\n"
                "Scrape → Classify → Tag → Embed & Store",
                title="[*] Starting Pipeline",
                border_style="cyan",
            )
        )

        if scrape:
            await self._stage_scrape()

        if classify:
            await self._stage_classify()

        if tag:
            await self._stage_tag()

        if embed:
            await self._stage_embed()

        self._print_summary()
        return self.stats

    # ──────────────────────────────────────────
    # Stage 1: Scrape
    # ──────────────────────────────────────────

    async def _stage_scrape(self) -> None:
        """Execute the scraping stage."""
        console.print("\n[bold yellow]═══ Stage 1: SCRAPE ═══[/]")

        try:
            scraper = RedditScraper(self.settings.reddit, self.store)
            items = scraper.scrape()
            self.stats.total_scraped = len(items)

            # Count duplicates from the store
            status_counts = self.store.count_by_status()
            total_in_db = self.store.get_total_count()
            logger.info(
                "Scrape stage complete: %d new items (DB total: %d)",
                len(items), total_in_db,
            )
        except Exception as e:
            logger.error("Scrape stage failed: %s", e)
            self.stats.errors += 1

    # ──────────────────────────────────────────
    # Stage 2: Classify
    # ──────────────────────────────────────────

    async def _stage_classify(self) -> None:
        """Execute the classification stage (heuristic + LLM)."""
        console.print("\n[bold yellow]═══ Stage 2: CLASSIFY ═══[/]")

        # 2a. Heuristic filter on 'raw' items
        raw_items = self.store.get_items_by_status(PipelineStatus.RAW)
        if raw_items:
            console.print(
                f"  Running heuristic filter on [cyan]{len(raw_items)}[/] raw items..."
            )
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
            ) as progress:
                task = progress.add_task(
                    "[green]Heuristic filtering...", total=len(raw_items)
                )
                for item in raw_items:
                    result = self.heuristic.evaluate(item["text"])
                    self.store.update_heuristic_result(
                        item["id"], result.passed, result.score
                    )
                    if result.passed:
                        self.stats.heuristic_passed += 1
                    else:
                        self.stats.heuristic_rejected += 1
                    progress.advance(task)

            logger.info(
                "Heuristic: %d passed, %d rejected",
                self.stats.heuristic_passed,
                self.stats.heuristic_rejected,
            )
        else:
            console.print("  No raw items to filter")

        # 2b. LLM classification on 'heuristic_pass' items
        heuristic_items = self.store.get_items_by_status(
            PipelineStatus.HEURISTIC_PASS
        )
        if heuristic_items:
            console.print(
                f"  Running LLM classifier on [cyan]{len(heuristic_items)}[/] items..."
            )
            classify_stats = await self.classifier.classify_items(heuristic_items)
            self.stats.llm_retrospective += classify_stats.get("retrospective", 0)
            self.stats.llm_rejected += classify_stats.get("not_retrospective", 0)
            self.stats.llm_ambiguous += classify_stats.get("ambiguous", 0)
        else:
            console.print("  No heuristic-passed items to classify")

    # ──────────────────────────────────────────
    # Stage 3: Tag
    # ──────────────────────────────────────────

    async def _stage_tag(self) -> None:
        """Execute the tagging/metadata extraction stage."""
        console.print("\n[bold yellow]═══ Stage 3: TAG ═══[/]")

        classified_items = self.store.get_items_by_status(
            PipelineStatus.CLASSIFIED_RETROSPECTIVE
        )
        if classified_items:
            console.print(
                f"  Extracting metadata from [cyan]{len(classified_items)}[/] stories..."
            )
            tag_stats = await self.tagger.tag_items(classified_items)
            self.stats.tagged += tag_stats.get("tagged", 0)
            self.stats.tag_failed += tag_stats.get("failed", 0)
        else:
            console.print("  No classified items to tag")

    # ──────────────────────────────────────────
    # Stage 4: Embed & Store
    # ──────────────────────────────────────────

    async def _stage_embed(self) -> None:
        """Execute the embedding and vector storage stage."""
        console.print("\n[bold yellow]═══ Stage 4: EMBED & STORE ═══[/]")

        tagged_items = self.store.get_items_by_status(PipelineStatus.TAGGED)
        if not tagged_items:
            console.print("  No tagged items to embed")
            return

        console.print(
            f"  Processing [cyan]{len(tagged_items)}[/] tagged stories..."
        )

        # 4a. Chunk stories
        all_chunks = []
        for item in tagged_items:
            chunks = self.chunker.chunk_story(item)
            all_chunks.extend(chunks)
        self.stats.chunks_total = len(all_chunks)
        console.print(f"  Generated [cyan]{len(all_chunks)}[/] chunks")

        # 4b. Generate embeddings
        chunk_texts = [chunk.text for chunk in all_chunks]
        console.print("  Generating embeddings...")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
        ) as progress:
            task = progress.add_task(
                "[blue]Embedding...",
                total=len(chunk_texts),
            )
            embeddings = self.embedder.embed_texts(chunk_texts)
            progress.advance(task, len(chunk_texts))

        # 4c. Upsert into Qdrant
        try:
            upserted = self.qdrant.upsert_chunks(all_chunks, embeddings)
            self.stats.indexed = upserted
            console.print(
                f"  Upserted [green]{upserted}[/] points into Qdrant"
            )

            # Mark items as indexed in SQLite
            indexed_parent_ids = {chunk.parent_id for chunk in all_chunks}
            for parent_id in indexed_parent_ids:
                self.store.mark_indexed(parent_id)

        except Exception as e:
            logger.error("Qdrant upsert failed: %s", e)
            console.print(f"  [red]Qdrant upsert failed:[/] {e}")
            console.print(
                "  [yellow]Hint: Is Qdrant running? "
                "Try: docker compose up -d[/]"
            )
            self.stats.errors += 1

    # ──────────────────────────────────────────
    # Summary
    # ──────────────────────────────────────────

    def _print_summary(self) -> None:
        """Print a formatted summary table of the pipeline run."""
        table = Table(
            title="Pipeline Run Summary",
            show_header=True,
            header_style="bold magenta",
        )
        table.add_column("Metric", style="cyan")
        table.add_column("Count", justify="right", style="green")

        rows = [
            ("Total Scraped", self.stats.total_scraped),
            ("Duplicates Skipped", self.stats.duplicates_skipped),
            ("─── Classification ───", ""),
            ("Heuristic Passed", self.stats.heuristic_passed),
            ("Heuristic Rejected", self.stats.heuristic_rejected),
            ("LLM → Retrospective", self.stats.llm_retrospective),
            ("LLM → Rejected", self.stats.llm_rejected),
            ("LLM → Ambiguous", self.stats.llm_ambiguous),
            ("─── Tagging ───", ""),
            ("Stories Tagged", self.stats.tagged),
            ("Tagging Failed", self.stats.tag_failed),
            ("─── Embedding ───", ""),
            ("Chunks Generated", self.stats.chunks_total),
            ("Points Indexed", self.stats.indexed),
            ("─── Errors ───", ""),
            ("Total Errors", self.stats.errors),
        ]

        for label, count in rows:
            table.add_row(label, str(count))

        console.print()
        console.print(table)

        # Also print DB status summary
        status_counts = self.store.count_by_status()
        if status_counts:
            db_table = Table(
                title="Database Status Summary",
                show_header=True,
                header_style="bold blue",
            )
            db_table.add_column("Status", style="cyan")
            db_table.add_column("Count", justify="right", style="yellow")
            for status, count in sorted(status_counts.items()):
                db_table.add_row(status, str(count))
            console.print(db_table)
