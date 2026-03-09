"""
Echoes Phase 3 -- Retrieval Tests

Tests for personality weighting and hybrid retrieval.
"""

import pytest
from unittest.mock import MagicMock

from personality.models.values_vector import ValuesVector
from rag.query.models import QueryAnalysis, RetrievalQuery
from rag.retrieval.hybrid_retriever import HybridRetriever
from rag.retrieval.models import RetrievalResult, StoryCandidate
from rag.retrieval.personality_weighting import (
    build_boost_themes,
    build_counter_themes,
    build_retrieval_query,
    get_dominant_dimensions,
    get_preferred_time_range,
)


class TestPersonalityWeighting:
    """Tests for personality → retrieval behavior mapping."""

    def test_high_risk_boosts_risk_themes(self):
        """High risk tolerance should boost risk-related themes."""
        values = ValuesVector(risk_tolerance=0.8)
        themes = build_boost_themes(values)
        assert "risk" in themes or "leap of faith" in themes

    def test_low_risk_boosts_caution_themes(self):
        """Low risk tolerance should boost caution themes."""
        values = ValuesVector(risk_tolerance=0.2)
        themes = build_boost_themes(values)
        assert "caution" in themes or "stability" in themes

    def test_counter_themes_oppose_dominant(self):
        """Counter themes should challenge the user's dominant traits."""
        values = ValuesVector(risk_tolerance=0.9, action_bias=0.8)
        counter = build_counter_themes(values)
        # Should contain opposite themes
        assert any(
            t in counter
            for t in ["caution", "patience", "stability", "waited"]
        )

    def test_dominant_dimensions_sorted_by_extremity(self):
        """get_dominant_dimensions should return most extreme first."""
        values = ValuesVector(
            risk_tolerance=0.9,  # Very extreme
            action_bias=0.1,  # Very extreme
            social_weight=0.5,  # Neutral
        )
        dominants = get_dominant_dimensions(values, top_n=3)
        # risk_tolerance and action_bias should be before social_weight
        dim_names = [d[0] for d in dominants]
        assert "risk_tolerance" in dim_names[:2]
        assert "action_bias" in dim_names[:2]

    def test_time_range_high_horizon(self):
        """High time horizon users should prefer 3+ year stories."""
        values = ValuesVector(time_horizon=0.8)
        time_range = get_preferred_time_range(values)
        assert time_range is not None
        assert time_range[0] >= 36  # 3 years minimum

    def test_time_range_neutral_returns_none(self):
        """Neutral time horizon should have no preference."""
        values = ValuesVector(time_horizon=0.5)
        assert get_preferred_time_range(values) is None

    def test_build_retrieval_query_full(self):
        """build_retrieval_query should produce a complete query."""
        analysis = QueryAnalysis(
            decision_type="career",
            what_would_help="Stories from job changers",
        )
        values = ValuesVector(risk_tolerance=0.8, action_bias=0.7)
        embedding = [0.1] * 3072
        focused = [0.2] * 3072

        query = build_retrieval_query(analysis, values, embedding, focused)
        assert isinstance(query, RetrievalQuery)
        assert query.decision_type == "career"
        assert len(query.primary_embedding) == 3072
        assert len(query.focused_embedding) == 3072
        assert len(query.boost_themes) > 0
        assert len(query.counter_narrative_themes) > 0
        assert query.counter_narrative_quota == 0.25


class TestHybridRetriever:
    """Tests for the dual-pass retriever."""

    def setup_method(self):
        self.mock_qdrant = MagicMock()
        self.retriever = HybridRetriever(self.mock_qdrant)

    def _make_qdrant_result(self, id: str, score: float) -> dict:
        return {
            "id": id,
            "score": score,
            "payload": {
                "text": f"Story {id}",
                "decision_type": "career",
                "outcome_sentiment": "positive",
                "key_themes": ["change"],
            },
        }

    def test_retrieval_merges_and_deduplicates(self):
        """Dual-pass results should be merged with deduplication."""
        self.mock_qdrant.search.side_effect = [
            # Broad pass
            [
                self._make_qdrant_result("a", 0.9),
                self._make_qdrant_result("b", 0.8),
                self._make_qdrant_result("c", 0.7),
            ],
            # Focused pass
            [
                self._make_qdrant_result("b", 0.95),  # Duplicate with higher score
                self._make_qdrant_result("d", 0.85),
            ],
        ]

        query = RetrievalQuery(
            primary_embedding=[0.1] * 3072,
            focused_embedding=[0.2] * 3072,
        )

        result = self.retriever.retrieve(query)
        assert isinstance(result, RetrievalResult)
        assert result.deduplicated_count == 4  # a, b (higher), c, d
        ids = {c.point_id for c in result.candidates}
        assert ids == {"a", "b", "c", "d"}

        # b should have the higher score from focused pass
        b_candidate = next(c for c in result.candidates if c.point_id == "b")
        assert b_candidate.semantic_score == 0.95

    def test_retrieval_no_primary_embedding(self):
        """Should handle missing primary embedding gracefully."""
        self.mock_qdrant.search.return_value = [
            self._make_qdrant_result("x", 0.8),
        ]

        query = RetrievalQuery(
            primary_embedding=[],
            focused_embedding=[0.2] * 3072,
        )

        result = self.retriever.retrieve(query)
        assert result.primary_count == 0
        assert result.deduplicated_count >= 1

    def test_story_candidate_from_qdrant(self):
        """StoryCandidate.from_qdrant_result should extract all fields."""
        result = self._make_qdrant_result("test", 0.85)
        result["payload"]["time_elapsed_months"] = 60
        result["payload"]["emotional_richness"] = 8

        candidate = StoryCandidate.from_qdrant_result(result, "primary")
        assert candidate.point_id == "test"
        assert candidate.semantic_score == 0.85
        assert candidate.time_elapsed_months == 60
        assert candidate.emotional_richness == 8
        assert candidate.search_pass == "primary"
