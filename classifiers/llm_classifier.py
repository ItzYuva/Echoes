"""
Echoes Data Pipeline — LLM Classifier (Classifier Stage 2)

Wraps the LLM client to perform batch classification of texts
that passed the heuristic filter. Handles:
  - Content hash–based caching (don't re-classify the same text)
  - Batched async execution
  - Result mapping back to item IDs
  - Status updates in the SQLite store
"""

from __future__ import annotations

import asyncio
import hashlib
from typing import Optional

from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

from config.logging_config import get_logger
from llm.base_client import BaseLLMClient
from storage.models import ClassificationResult
from storage.sqlite_store import SQLiteStore

logger = get_logger(__name__)


class LLMClassifier:
    """Stage 2 LLM-based retrospective classifier.

    Takes texts that passed the heuristic filter and uses the LLM
    to make a final determination. Results are cached by content
    hash so repeated runs don't re-classify the same text.

    Args:
        llm_client: An LLM client implementing BaseLLMClient.
        store: SQLite store for reading items and updating status.
        batch_size: Number of texts per async batch (default: 20).
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
        self._cache: dict[str, tuple[ClassificationResult, str]] = {}

    def _content_hash(self, text: str) -> str:
        """Generate a cache key from text content."""
        return hashlib.sha256(text.strip().lower().encode()).hexdigest()

    async def classify_items(
        self,
        items: list[dict],
        show_progress: bool = True,
    ) -> dict[str, int]:
        """Classify a list of items from the SQLite store.

        Processes items in batches, using cached results where available.
        Updates each item's status in SQLite after classification.

        Args:
            items: List of item dicts (from SQLiteStore.get_items_by_status).
            show_progress: Whether to show a rich progress bar.

        Returns:
            Dict with counts: retrospective, not_retrospective, ambiguous, errors.
        """
        stats = {
            "retrospective": 0,
            "not_retrospective": 0,
            "ambiguous": 0,
            "cached": 0,
            "errors": 0,
        }

        if not items:
            logger.info("No items to classify")
            return stats

        # Split into batches
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
                    "[cyan]Classifying...", total=len(items)
                )
                for batch in batches:
                    batch_stats = await self._classify_batch(batch)
                    for key, val in batch_stats.items():
                        stats[key] += val
                    progress.advance(task, len(batch))
        else:
            for batch in batches:
                batch_stats = await self._classify_batch(batch)
                for key, val in batch_stats.items():
                    stats[key] += val

        logger.info(
            "[bold]Classification complete:[/] %d retrospective, "
            "%d rejected, %d ambiguous, %d cached, %d errors",
            stats["retrospective"],
            stats["not_retrospective"],
            stats["ambiguous"],
            stats["cached"],
            stats["errors"],
        )
        return stats

    async def _classify_batch(self, items: list[dict]) -> dict[str, int]:
        """Classify a single batch of items.

        Checks cache first, then sends uncached items to the LLM.

        Args:
            items: Batch of item dicts.

        Returns:
            Stats dict for this batch.
        """
        stats = {
            "retrospective": 0,
            "not_retrospective": 0,
            "ambiguous": 0,
            "cached": 0,
            "errors": 0,
        }

        # Separate cached from uncached
        to_classify: list[dict] = []
        for item in items:
            content_hash = self._content_hash(item["text"])
            if content_hash in self._cache:
                result, raw = self._cache[content_hash]
                self.store.update_classification(item["id"], result, f"[cached] {raw}")
                stats["cached"] += 1
                stats[self._result_key(result)] += 1
            else:
                to_classify.append(item)

        if not to_classify:
            return stats

        # Batch classify via LLM
        texts = [item["text"] for item in to_classify]
        try:
            results = await self.llm.classify_batch(texts)

            for item, (result, raw) in zip(to_classify, results):
                content_hash = self._content_hash(item["text"])
                self._cache[content_hash] = (result, raw)
                self.store.update_classification(item["id"], result, raw)
                stats[self._result_key(result)] += 1

        except Exception as e:
            logger.error("Batch classification error: %s", e)
            for item in to_classify:
                self.store.update_classification(
                    item["id"],
                    ClassificationResult.AMBIGUOUS,
                    f"BATCH_ERROR: {e}",
                )
                stats["errors"] += 1

        return stats

    @staticmethod
    def _result_key(result: ClassificationResult) -> str:
        """Map ClassificationResult to stats dict key."""
        mapping = {
            ClassificationResult.RETROSPECTIVE: "retrospective",
            ClassificationResult.NOT_RETROSPECTIVE: "not_retrospective",
            ClassificationResult.AMBIGUOUS: "ambiguous",
        }
        return mapping.get(result, "ambiguous")
