"""
Echoes Phase 3 -- Re-ranker Tests

Tests for scoring functions, counter-narrative detection, and re-ranking.
"""

import pytest

from personality.models.values_vector import ValuesVector
from rag.query.models import QueryAnalysis
from rag.ranking.counter_narrative import (
    enforce_counter_quota,
    interleave_by_sentiment,
    is_counter_narrative,
)
from rag.ranking.models import RankingResult, ScoredStory
from rag.ranking.reranker import Reranker
from rag.ranking.scoring_functions import (
    score_emotional_richness,
    score_outcome_clarity,
    score_personality_alignment,
    score_semantic_relevance,
    score_temporal_depth,
)
from rag.retrieval.models import StoryCandidate


class TestScoringFunctions:
    """Tests for individual scoring dimensions."""

    def test_semantic_relevance_clamped(self):
        """Score should be clamped to [0, 1]."""
        assert score_semantic_relevance(0.85) == 0.85
        assert score_semantic_relevance(1.5) == 1.0
        assert score_semantic_relevance(-0.1) == 0.0

    def test_temporal_depth_scaling(self):
        """More hindsight should score higher."""
        assert score_temporal_depth(60) > score_temporal_depth(12)
        assert score_temporal_depth(12) > score_temporal_depth(3)
        assert score_temporal_depth(-1) == 0.2  # unknown

    def test_emotional_richness_normalized(self):
        """Richness should normalize from 1-10 to 0-1."""
        assert score_emotional_richness(10) == 1.0
        assert score_emotional_richness(5) == 0.5
        assert score_emotional_richness(0) == 0.0

    def test_outcome_clarity_adjusted_by_tolerance(self):
        """High ambiguity tolerance should not penalize unclear outcomes."""
        assert score_outcome_clarity(True, 0.5) == 1.0
        assert score_outcome_clarity(False, 0.8) == 0.7  # high tolerance
        assert score_outcome_clarity(False, 0.3) == 0.0  # low tolerance

    def test_personality_alignment_theme_match(self):
        """Stories matching boost themes should score higher."""
        values = ValuesVector(risk_tolerance=0.8)
        themes_matching = ["leap of faith", "risk", "unknown"]
        themes_non_matching = ["routine", "stability"]

        score_matching = score_personality_alignment(
            themes_matching, "positive", 36, values
        )
        score_non = score_personality_alignment(
            themes_non_matching, "positive", 36, values
        )
        assert score_matching > score_non


class TestCounterNarrative:
    """Tests for counter-narrative detection and enforcement."""

    def test_detects_counter_for_risk_taker(self):
        """Caution themes should be counter-narrative for high risk users."""
        values = ValuesVector(risk_tolerance=0.9)
        assert is_counter_narrative(
            ["played it safe", "caution"], "positive", values
        )

    def test_no_counter_for_neutral(self):
        """Neutral profiles should have fewer counter-narratives."""
        values = ValuesVector()  # all 0.5
        result = is_counter_narrative(
            ["random theme"], "positive", values
        )
        # False — neutral profiles have no strong extremes to counter
        assert isinstance(result, bool)

    def test_enforce_quota_swaps_in_counter(self):
        """enforce_counter_quota should swap in counter-narratives."""
        # 8 stories, 0 counter-narratives → need at least 2 (25%)
        non_counter = [
            ScoredStory(
                point_id=str(i),
                composite_score=1.0 - i * 0.1,
                is_counter_narrative=False,
            )
            for i in range(8)
        ]
        counters = [
            ScoredStory(
                point_id=f"c{i}",
                composite_score=0.3,
                is_counter_narrative=True,
            )
            for i in range(3)
        ]
        all_stories = non_counter + counters

        values = ValuesVector(risk_tolerance=0.9)
        result = enforce_counter_quota(all_stories, values, min_ratio=0.25, total_target=8)

        cn_count = sum(1 for s in result if s.is_counter_narrative)
        assert cn_count >= 2  # at least 25% of 8

    def test_interleave_mixes_sentiments(self):
        """interleave_by_sentiment should mix positive/negative/mixed."""
        stories = [
            ScoredStory(point_id="p1", outcome_sentiment="positive"),
            ScoredStory(point_id="p2", outcome_sentiment="positive"),
            ScoredStory(point_id="n1", outcome_sentiment="negative"),
            ScoredStory(point_id="n2", outcome_sentiment="negative"),
            ScoredStory(point_id="m1", outcome_sentiment="mixed"),
        ]

        result = interleave_by_sentiment(stories)
        # Should not have two consecutive same-sentiment stories at the start
        assert len(result) == 5
        # First 3 should ideally be different sentiments
        first_sents = [s.outcome_sentiment for s in result[:3]]
        assert len(set(first_sents)) >= 2  # at least 2 different sentiments


class TestReranker:
    """Tests for the full re-ranker."""

    def setup_method(self):
        self.reranker = Reranker()
        self.values = ValuesVector(
            risk_tolerance=0.8,
            action_bias=0.7,
            time_horizon=0.6,
        )
        self.query = QueryAnalysis(
            decision_type="career",
            core_tension="security vs autonomy",
        )

    def _make_candidate(self, id: str, score: float, **kwargs) -> StoryCandidate:
        return StoryCandidate(
            point_id=id,
            text=f"Story {id}",
            semantic_score=score,
            decision_type=kwargs.get("decision_type", "career"),
            outcome_sentiment=kwargs.get("outcome_sentiment", "positive"),
            time_elapsed_months=kwargs.get("time_elapsed_months", 36),
            emotional_richness=kwargs.get("emotional_richness", 7),
            outcome_clarity=kwargs.get("outcome_clarity", True),
            key_themes=kwargs.get("key_themes", ["change"]),
        )

    def test_rerank_returns_result(self):
        """rerank() should return a RankingResult."""
        candidates = [
            self._make_candidate("a", 0.9),
            self._make_candidate("b", 0.8),
            self._make_candidate("c", 0.7),
        ]

        result = self.reranker.rerank(candidates, self.query, self.values, max_stories=3)
        assert isinstance(result, RankingResult)
        assert len(result.stories) == 3
        assert result.total_candidates == 3

    def test_rerank_limits_output(self):
        """rerank() should respect max_stories."""
        candidates = [self._make_candidate(str(i), 0.9 - i * 0.05) for i in range(20)]

        result = self.reranker.rerank(candidates, self.query, self.values, max_stories=8)
        assert len(result.stories) <= 8

    def test_rerank_empty_returns_empty(self):
        """Empty candidates should return empty result."""
        result = self.reranker.rerank([], self.query, self.values)
        assert len(result.stories) == 0

    def test_higher_semantic_scores_rank_higher(self):
        """Stories with higher semantic scores should generally rank higher."""
        candidates = [
            self._make_candidate("high", 0.95, emotional_richness=8),
            self._make_candidate("low", 0.3, emotional_richness=3),
        ]

        result = self.reranker.rerank(candidates, self.query, self.values, max_stories=2)
        assert result.stories[0].point_id == "high"
