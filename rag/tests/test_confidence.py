"""
Echoes Phase 3 -- Confidence Tests

Tests for retrieval confidence scoring.
"""

import pytest

from rag.confidence.confidence_scorer import ConfidenceScorer
from rag.confidence.models import RetrievalConfidence
from rag.query.models import QueryAnalysis
from rag.ranking.models import ScoredStory


class TestConfidenceScorer:
    """Tests for the confidence scoring system."""

    def setup_method(self):
        self.scorer = ConfidenceScorer()
        self.query = QueryAnalysis(decision_type="career")

    def _make_story(self, sem: float = 0.8, **kwargs) -> ScoredStory:
        return ScoredStory(
            point_id="test",
            semantic_relevance=sem,
            decision_type=kwargs.get("decision_type", "career"),
            emotional_richness=kwargs.get("emotional_richness", 7),
            time_elapsed_months=kwargs.get("time_elapsed", 36),
        )

    def test_high_confidence_with_good_stories(self):
        """Many relevant stories should produce high confidence."""
        stories = [self._make_story(0.85) for _ in range(10)]
        result = self.scorer.score(stories, self.query)
        assert result.level == "high"
        assert result.score >= 0.75

    def test_low_confidence_with_weak_stories(self):
        """Weak scores and few stories should produce low confidence."""
        stories = [self._make_story(0.3, decision_type="other") for _ in range(2)]
        result = self.scorer.score(stories, self.query)
        assert result.level in ("low", "insufficient")
        assert result.score < 0.55

    def test_no_stories_is_insufficient(self):
        """No stories should always be insufficient."""
        result = self.scorer.score([], self.query)
        assert result.level == "insufficient"
        assert result.score == 0.0

    def test_should_present_logic(self):
        """should_present should be False only for insufficient."""
        conf_high = RetrievalConfidence(score=0.8, level="high")
        conf_medium = RetrievalConfidence(score=0.6, level="medium")
        conf_insuf = RetrievalConfidence(score=0.1, level="insufficient")

        assert conf_high.should_present is True
        assert conf_medium.should_present is True
        assert conf_insuf.should_present is False

    def test_needs_disclaimer_logic(self):
        """needs_disclaimer should be True for medium, low, insufficient."""
        assert RetrievalConfidence(level="high").needs_disclaimer is False
        assert RetrievalConfidence(level="medium").needs_disclaimer is True
        assert RetrievalConfidence(level="low").needs_disclaimer is True
        assert RetrievalConfidence(level="insufficient").needs_disclaimer is True
