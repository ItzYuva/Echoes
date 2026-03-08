"""
Echoes Data Pipeline — Classifier Unit Tests

Tests both the heuristic filter (Stage 1) and LLM classifier (Stage 2).
The heuristic tests run without any API dependencies.
LLM tests use a mock client to avoid actual API calls.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from classifiers.heuristic_filter import HeuristicFilter, HeuristicResult
from classifiers.llm_classifier import LLMClassifier
from storage.models import ClassificationResult


# ──────────────────────────────────────────────
# Heuristic Filter Tests
# ──────────────────────────────────────────────

class TestHeuristicFilter:
    """Tests for the rule-based heuristic filter."""

    def setup_method(self):
        self.heuristic = HeuristicFilter(threshold=0.3)

    def test_clear_retrospective_passes(self):
        """A clearly retrospective text should pass with high score."""
        text = (
            "Three years after leaving that job, I can honestly say it was "
            "the best decision I ever made. Looking back, the fear of leaving "
            "was worse than anything that actually happened after."
        )
        result = self.heuristic.evaluate(text)
        assert result.passed is True
        assert result.score >= 0.3
        assert len(result.signals) >= 2

    def test_update_post_passes(self):
        """An update post should pass."""
        text = (
            "Update: It's been 8 months since I ended things. For anyone "
            "wondering how it turned out — I'm doing so much better than "
            "I expected."
        )
        result = self.heuristic.evaluate(text)
        assert result.passed is True
        assert any("update" in s.lower() for s in result.signals)

    def test_hindsight_language_passes(self):
        """Text with 'in hindsight' should pass."""
        text = (
            "In hindsight, I should have listened to my mother. She told me "
            "not to take that job and I regret not listening. Two years later, "
            "I ended up exactly where she predicted."
        )
        result = self.heuristic.evaluate(text)
        assert result.passed is True

    def test_advice_seeking_rejected(self):
        """An advice-seeking post should not pass."""
        text = (
            "What should I do about my toxic boss? She undermines me in "
            "meetings and takes credit for my work. Any advice would be "
            "appreciated. Help me figure this out."
        )
        result = self.heuristic.evaluate(text)
        assert result.passed is False

    def test_in_the_moment_reaction_rejected(self):
        """An in-the-moment emotional reaction should not pass."""
        text = (
            "Just got dumped after 4 years. I'm sitting here right now "
            "feeling like the floor dropped out. How do you even start "
            "to move on? I don't know who I am without her."
        )
        result = self.heuristic.evaluate(text)
        assert result.passed is False

    def test_forward_looking_excitement_rejected(self):
        """Forward-looking excitement without reflection should not pass."""
        text = (
            "I'm so excited to start my new job next week! This is going "
            "to be the fresh start I needed. Wish me luck!"
        )
        result = self.heuristic.evaluate(text)
        assert result.passed is False

    def test_mixed_signals_score(self):
        """Text with some retrospective and some advice-seeking signals."""
        text = (
            "I've been thinking about the decision I made two years ago. "
            "What should I do now? Looking back, I think I was right, "
            "but I need advice on the next step."
        )
        result = self.heuristic.evaluate(text)
        # Should have both positive and negative signals
        assert len(result.signals) >= 2

    def test_empty_text(self):
        """Empty text should not pass."""
        result = self.heuristic.evaluate("")
        assert result.passed is False
        assert result.score == 0.0

    def test_batch_evaluate(self):
        """Batch evaluate should return results for all texts."""
        texts = [
            "Looking back, best decision ever.",
            "What should I do about my job?",
            "Five years ago I left. In hindsight, it was right.",
        ]
        results = self.heuristic.batch_evaluate(texts)
        assert len(results) == 3
        assert all(isinstance(r, HeuristicResult) for r in results)

    def test_time_markers_detected(self):
        """Various time markers should be detected."""
        time_texts = [
            "3 years ago I decided to leave.",
            "Six months later, everything changed.",
            "It's been 2 years since I moved.",
        ]
        for text in time_texts:
            result = self.heuristic.evaluate(text)
            assert result.score > 0, f"No signals detected for: {text}"

    def test_outcome_language_detected(self):
        """Outcome language should fire signals."""
        texts = [
            "It turned out to be the best decision.",
            "I ended up in a much better place.",
            "Ultimately, it was worth the risk.",
        ]
        for text in texts:
            result = self.heuristic.evaluate(text)
            assert result.score > 0, f"No signals for: {text}"


# ──────────────────────────────────────────────
# LLM Classifier Tests (with mocked LLM)
# ──────────────────────────────────────────────

class TestLLMClassifier:
    """Tests for the LLM classifier with mocked API calls."""

    def setup_method(self):
        self.mock_llm = MagicMock()
        self.mock_store = MagicMock()
        self.classifier = LLMClassifier(
            llm_client=self.mock_llm,
            store=self.mock_store,
            batch_size=5,
        )

    def test_classify_items_empty_list(self):
        """Classifying an empty list should return zero counts."""
        result = asyncio.run(
            self.classifier.classify_items([], show_progress=False)
        )
        assert result["retrospective"] == 0
        assert result["not_retrospective"] == 0

    def test_classify_items_all_retrospective(self):
        """All items classified as retrospective by mock LLM."""
        items = [
            {"id": f"item-{i}", "text": f"Retrospective story {i}"}
            for i in range(3)
        ]

        async def mock_classify_batch(texts):
            return [
                (ClassificationResult.RETROSPECTIVE, "RETROSPECTIVE")
                for _ in texts
            ]

        self.mock_llm.classify_batch = mock_classify_batch

        result = asyncio.run(
            self.classifier.classify_items(items, show_progress=False)
        )
        assert result["retrospective"] == 3
        assert result["not_retrospective"] == 0

    def test_classify_items_mixed_results(self):
        """Mixed classification results."""
        items = [
            {"id": "item-1", "text": "Retrospective text"},
            {"id": "item-2", "text": "Not retrospective text"},
            {"id": "item-3", "text": "Ambiguous text"},
        ]

        results_sequence = [
            (ClassificationResult.RETROSPECTIVE, "RETROSPECTIVE"),
            (ClassificationResult.NOT_RETROSPECTIVE, "NOT_RETROSPECTIVE"),
            (ClassificationResult.AMBIGUOUS, "AMBIGUOUS"),
        ]

        async def mock_classify_batch(texts):
            return results_sequence[:len(texts)]

        self.mock_llm.classify_batch = mock_classify_batch

        result = asyncio.run(
            self.classifier.classify_items(items, show_progress=False)
        )
        assert result["retrospective"] == 1
        assert result["not_retrospective"] == 1
        assert result["ambiguous"] == 1

    def test_content_hash_caching(self):
        """Same text content should produce the same hash for caching."""
        hash1 = self.classifier._content_hash("Hello world")
        hash2 = self.classifier._content_hash("Hello world")
        hash3 = self.classifier._content_hash("hello world")  # case insensitive
        hash4 = self.classifier._content_hash("Different text")

        assert hash1 == hash2
        assert hash1 == hash3  # normalized to lowercase
        assert hash1 != hash4


# ──────────────────────────────────────────────
# Run tests
# ──────────────────────────────────────────────

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
