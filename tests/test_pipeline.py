"""
Echoes Data Pipeline — Integration Tests

End-to-end tests for the pipeline using a temporary SQLite database
and mock API clients. Verifies the full flow:
  scrape (mock) → heuristic → classify (mock) → tag (mock) → chunk → embed (mock) → store (mock)
"""

from __future__ import annotations

import asyncio
import hashlib
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from classifiers.heuristic_filter import HeuristicFilter
from processors.chunker import TextChunker
from config.settings import PipelineSettings
from storage.models import (
    ClassificationResult,
    ContentType,
    PipelineStatus,
    ScrapedItem,
    StoryMetadata,
    DecisionType,
    OutcomeSentiment,
)
from storage.sqlite_store import SQLiteStore


class TestSQLiteStore:
    """Integration tests for the SQLite store."""

    def setup_method(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.tmp_dir, "test.db")
        self.store = SQLiteStore(self.db_path)

    def _make_item(self, text: str = "Test story about looking back on life", **kwargs):
        """Create a test ScrapedItem."""
        content_hash = hashlib.sha256(text.strip().lower().encode()).hexdigest()
        defaults = {
            "source": "reddit",
            "subreddit": "AskReddit",
            "content_type": ContentType.POST,
            "reddit_id": f"test_{content_hash[:8]}",
            "author_hash": "abc123",
            "text": text,
            "content_hash": content_hash,
            "score": 100,
            "created_utc": datetime.now(timezone.utc),
        }
        defaults.update(kwargs)
        return ScrapedItem(**defaults)

    def test_insert_and_retrieve(self):
        """Insert an item and retrieve it by status."""
        item = self._make_item()
        assert self.store.insert_item(item) is True

        raw_items = self.store.get_items_by_status(PipelineStatus.RAW)
        assert len(raw_items) == 1
        assert raw_items[0]["text"] == item.text

    def test_dedup_by_content_hash(self):
        """Duplicate content should be rejected."""
        item = self._make_item("Same text for dedup test")
        assert self.store.insert_item(item) is True
        assert self.store.content_hash_exists(item.content_hash) is True

        # Try inserting a different item with the same content hash
        item2 = self._make_item("Same text for dedup test")
        assert self.store.insert_item(item2) is False

    def test_status_transitions(self):
        """Test the pipeline status lifecycle."""
        item = self._make_item()
        self.store.insert_item(item)

        # raw → heuristic_pass
        self.store.update_heuristic_result(item.id, True, 0.7)
        items = self.store.get_items_by_status(PipelineStatus.HEURISTIC_PASS)
        assert len(items) == 1

        # heuristic_pass → classified_retrospective
        self.store.update_classification(
            item.id, ClassificationResult.RETROSPECTIVE, "RETROSPECTIVE"
        )
        items = self.store.get_items_by_status(PipelineStatus.CLASSIFIED_RETROSPECTIVE)
        assert len(items) == 1

        # classified_retrospective → tagged
        metadata = StoryMetadata(
            decision_type=DecisionType.CAREER,
            decision_subcategory="leaving a job",
            outcome_sentiment=OutcomeSentiment.POSITIVE,
            time_elapsed_months=36,
            emotional_richness=8,
            outcome_clarity=True,
            key_themes=["growth", "fear"],
            hindsight_insight="Change is good.",
        )
        self.store.update_metadata(item.id, metadata)
        items = self.store.get_items_by_status(PipelineStatus.TAGGED)
        assert len(items) == 1
        assert items[0]["decision_type"] == "career"

        # tagged → indexed
        self.store.mark_indexed(item.id)
        items = self.store.get_items_by_status(PipelineStatus.INDEXED)
        assert len(items) == 1

    def test_count_by_status(self):
        """Status counts should be accurate."""
        for i in range(5):
            self.store.insert_item(self._make_item(f"Story number {i}"))

        counts = self.store.count_by_status()
        assert counts.get("raw", 0) == 5

    def test_bulk_hash_check(self):
        """Bulk hash check should return existing hashes."""
        items = [self._make_item(f"Unique story {i}") for i in range(3)]
        for item in items:
            self.store.insert_item(item)

        existing_hashes = [items[0].content_hash, items[2].content_hash]
        fake_hash = "nonexistent_hash_000"

        found = self.store.bulk_check_hashes(existing_hashes + [fake_hash])
        assert items[0].content_hash in found
        assert items[2].content_hash in found
        assert fake_hash not in found

    def test_scrape_state(self):
        """Scrape state tracking for incremental runs."""
        assert self.store.get_last_scraped("AskReddit", "looking back") is None

        self.store.update_scrape_state(
            "AskReddit", "looking back", "2025-01-15T10:00:00", 50
        )
        result = self.store.get_last_scraped("AskReddit", "looking back")
        assert result == "2025-01-15T10:00:00"


class TestChunker:
    """Integration tests for the text chunker."""

    def setup_method(self):
        settings = PipelineSettings()
        self.chunker = TextChunker(settings)

    def test_short_text_single_chunk(self):
        """Short text should produce a single chunk."""
        item = {
            "id": "test-1",
            "text": "A short story about looking back. " * 20,
            "source": "reddit",
            "subreddit": "AskReddit",
            "author_hash": "abc",
            "scraped_at": datetime.now(timezone.utc).isoformat(),
            "score": 100,
        }
        chunks = self.chunker.chunk_story(item)
        assert len(chunks) == 1
        assert chunks[0].chunk_index == 0
        assert chunks[0].total_chunks == 1
        assert chunks[0].parent_id == "test-1"

    def test_long_text_multiple_chunks(self):
        """Long text should be split into multiple chunks."""
        # Create text with 1500+ words across paragraphs
        paragraphs = []
        for i in range(15):
            paragraphs.append(
                f"This is paragraph {i}. " + "Word " * 100
            )
        long_text = "\n\n".join(paragraphs)

        item = {
            "id": "test-long",
            "text": long_text,
            "source": "reddit",
            "subreddit": "AskReddit",
            "author_hash": "abc",
            "scraped_at": datetime.now(timezone.utc).isoformat(),
            "score": 50,
        }
        chunks = self.chunker.chunk_story(item)
        assert len(chunks) > 1
        assert chunks[0].chunk_index == 0
        assert chunks[-1].chunk_index == len(chunks) - 1
        assert all(c.total_chunks == len(chunks) for c in chunks)
        assert all(c.parent_id == "test-long" for c in chunks)

    def test_metadata_carried_to_chunks(self):
        """Metadata from the item should be carried to each chunk."""
        item = {
            "id": "test-meta",
            "text": "Short story. " * 20,
            "source": "reddit",
            "subreddit": "careerguidance",
            "author_hash": "xyz",
            "scraped_at": datetime.now(timezone.utc).isoformat(),
            "score": 200,
            "decision_type": "career",
            "outcome_sentiment": "positive",
            "key_themes": '["growth", "change"]',
        }
        chunks = self.chunker.chunk_story(item)
        assert chunks[0].subreddit == "careerguidance"
        assert chunks[0].decision_type == "career"
        assert chunks[0].outcome_sentiment == "positive"


class TestHeuristicIntegration:
    """Integration test for the heuristic filter with realistic texts."""

    def setup_method(self):
        self.heuristic = HeuristicFilter(threshold=0.3)

    def test_realistic_retrospective_batch(self):
        """Batch of realistic retrospective texts should mostly pass."""
        texts = [
            "Looking back on my divorce, I realize the signs were there for years. I just wasn't ready to see them.",
            "Three years after leaving that job, I can honestly say it was the best decision I ever made. At the time I was terrified.",
            "Update: It's been 8 months since I ended things. For anyone wondering how it turned out...",
            "I moved across the country 5 years ago. Here's what actually happened.",
        ]
        results = self.heuristic.batch_evaluate(texts)
        passed = sum(1 for r in results if r.passed)
        assert passed >= 3  # at least 3 out of 4 should pass

    def test_realistic_non_retrospective_batch(self):
        """Batch of non-retrospective texts should mostly fail."""
        texts = [
            "What should I do about my toxic boss? Any advice?",
            "Just got dumped. Feeling terrible right now.",
            "I'm thinking about quitting my job. Should I?",
            "So excited to start this new chapter! Wish me luck!",
        ]
        results = self.heuristic.batch_evaluate(texts)
        rejected = sum(1 for r in results if not r.passed)
        assert rejected >= 3  # at least 3 out of 4 should be rejected


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
