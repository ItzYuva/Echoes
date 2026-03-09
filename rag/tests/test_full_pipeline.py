"""
Echoes Phase 3 -- Full Pipeline Integration Test

Tests the complete RAG flow: query → analyze → embed → retrieve → rerank → present.
Uses mocks to avoid requiring live services.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from personality.models.values_vector import ValuesVector
from rag.pipeline.rag_pipeline import EchoesResponse, RAGPipeline


class TestRAGPipeline:
    """Integration test for the full RAG pipeline."""

    def setup_method(self):
        self.settings = MagicMock()

        # Mock LLM client
        self.mock_llm = MagicMock()
        self.mock_llm.analyze_query = AsyncMock(return_value={
            "decision_type": "career",
            "decision_subcategory": "leaving corporate",
            "core_tension": "security vs autonomy",
            "emotional_state": ["fear", "excitement"],
            "stakes": "high",
            "key_factors": ["mortgage", "burnout"],
            "what_would_help": "Stories from people who left corporate jobs",
        })
        self.mock_llm.present_stories = AsyncMock(
            return_value="Stories from people who stood where you stand..."
        )

        # Mock Qdrant
        self.mock_qdrant = MagicMock()
        self.mock_qdrant.search.return_value = [
            {
                "id": f"story-{i}",
                "score": 0.9 - i * 0.05,
                "payload": {
                    "text": f"Test story {i} about leaving a job",
                    "decision_type": "career",
                    "outcome_sentiment": ["positive", "mixed", "negative"][i % 3],
                    "time_elapsed_months": 36 + i * 6,
                    "emotional_richness": 7,
                    "outcome_clarity": True,
                    "key_themes": ["change", "growth"],
                    "hindsight_insight": "Looking back...",
                },
            }
            for i in range(10)
        ]

        # Mock embedder
        self.mock_embedder = MagicMock()

    @patch("rag.query.query_embedder.genai")
    def test_full_pipeline(self, mock_genai):
        """Full pipeline should produce an EchoesResponse."""
        mock_genai.embed_content.return_value = {"embedding": [0.1] * 3072}

        pipeline = RAGPipeline(
            settings=self.settings,
            llm_client=self.mock_llm,
            qdrant=self.mock_qdrant,
            embedder=self.mock_embedder,
        )

        values = ValuesVector(risk_tolerance=0.7, action_bias=0.6)

        response = asyncio.run(pipeline.query(
            user_text="I'm thinking about leaving my corporate job to freelance",
            values_vector=values,
        ))

        assert isinstance(response, EchoesResponse)
        assert response.query_analysis.decision_type == "career"
        assert response.confidence.level in ("high", "medium", "low", "insufficient")
        assert len(response.ranking.stories) > 0
        assert response.total_latency_ms >= 0  # Mocked pipeline can be sub-ms

    @patch("rag.query.query_embedder.genai")
    def test_pipeline_with_empty_qdrant(self, mock_genai):
        """Pipeline should handle empty Qdrant results gracefully."""
        mock_genai.embed_content.return_value = {"embedding": [0.1] * 3072}
        self.mock_qdrant.search.return_value = []

        pipeline = RAGPipeline(
            settings=self.settings,
            llm_client=self.mock_llm,
            qdrant=self.mock_qdrant,
            embedder=self.mock_embedder,
        )

        values = ValuesVector()
        response = asyncio.run(pipeline.query(
            user_text="Should I move to Japan?",
            values_vector=values,
        ))

        assert isinstance(response, EchoesResponse)
        assert response.confidence.level == "insufficient"
        assert len(response.ranking.stories) == 0
