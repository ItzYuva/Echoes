"""
Echoes Data Pipeline — Story Tagger (Component 3)

Extracts structured metadata from classified retrospective stories
using the LLM client. Handles batch processing with progress tracking
and graceful failure handling (one bad story doesn't crash the batch).
"""

from __future__ import annotations

import asyncio
from typing import Optional

from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

from config.logging_config import get_logger
from llm.base_client import BaseLLMClient
from storage.models import StoryMetadata
from storage.sqlite_store import SQLiteStore

logger = get_logger(__name__)


class StoryTagger:
    """Extracts structured metadata from retrospective stories.

    Uses the LLM to analyze each story and extract:
      - Decision type and subcategory
      - Outcome sentiment
      - Time elapsed
      - Emotional richness score
      - Key themes
      - Hindsight insight summary

    Processes in batches with async concurrency and updates SQLite.

    Args:
        llm_client: LLM client for metadata extraction.
        store: SQLite store for reading stories and writing metadata.
        batch_size: Number of stories per async batch.
    """

    def __init__(
        self,
        llm_client: BaseLLMClient,
        store: SQLiteStore,
        batch_size: int = 20,
    ) -> None:
        self.llm = llm_client
        self.store = store
        self.batch_size = batch_size

    async def tag_items(
        self,
        items: list[dict],
        show_progress: bool = True,
    ) -> dict[str, int]:
        """Tag a list of classified retrospective items with metadata.

        Processes items in batches. If metadata extraction fails for
        an individual item, it's marked as failed and skipped — the
        pipeline continues.

        Args:
            items: List of item dicts (status = classified_retrospective).
            show_progress: Whether to show a rich progress bar.

        Returns:
            Dict with counts: tagged, failed.
        """
        stats = {"tagged": 0, "failed": 0}

        if not items:
            logger.info("No items to tag")
            return stats

        batches = [
            items[i: i + self.batch_size]
            for i in range(0, len(items), self.batch_size)
        ]

        if show_progress:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
            ) as progress:
                task = progress.add_task(
                    "[magenta]Tagging stories...", total=len(items)
                )
                for batch in batches:
                    batch_stats = await self._tag_batch(batch)
                    for key, val in batch_stats.items():
                        stats[key] += val
                    progress.advance(task, len(batch))
        else:
            for batch in batches:
                batch_stats = await self._tag_batch(batch)
                for key, val in batch_stats.items():
                    stats[key] += val

        logger.info(
            "[bold]Tagging complete:[/] %d tagged, %d failed",
            stats["tagged"],
            stats["failed"],
        )
        return stats

    async def _tag_batch(self, items: list[dict]) -> dict[str, int]:
        """Tag a single batch of items.

        Args:
            items: Batch of item dicts.

        Returns:
            Stats dict for this batch.
        """
        stats = {"tagged": 0, "failed": 0}

        texts = [item["text"] for item in items]

        try:
            results = await self.llm.extract_metadata_batch(texts)

            for item, metadata in zip(items, results):
                if metadata is not None:
                    self.store.update_metadata(item["id"], metadata)
                    stats["tagged"] += 1
                else:
                    logger.warning(
                        "Metadata extraction returned None for item %s",
                        item["id"],
                    )
                    self.store.mark_failed(item["id"])
                    stats["failed"] += 1

        except Exception as e:
            logger.error("Batch tagging error: %s", e)
            for item in items:
                self.store.mark_failed(item["id"])
                stats["failed"] += 1

        return stats
