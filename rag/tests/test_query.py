"""
Echoes Phase 3 -- Query Understanding Tests

Tests for QueryAnalyzer and QueryEmbedder.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from rag.query.models import QueryAnalysis
from rag.query.query_analyzer import QueryAnalyzer
from rag.query.query_embedder import QueryEmbedder


class TestQueryAnalyzer:
    """Tests for the QueryAnalyzer component."""

    def setup_method(self):
        self.mock_llm = MagicMock()
        self.analyzer = QueryAnalyzer(self.mock_llm)

    def test_analyze_returns_structured_analysis(self):
        """analyze() should return a populated QueryAnalysis."""
        self.mock_llm.analyze_query = AsyncMock(return_value={
            "decision_type": "career",
            "decision_subcategory": "leaving corporate for freelance",
            "core_tension": "security vs. autonomy",
            "emotional_state": ["fear", "excitement"],
            "stakes": "high",
            "key_factors": ["mortgage", "kids", "desire for freedom"],
            "what_would_help": "Stories from people who left corporate jobs for freelance work",
        })

        result = asyncio.run(self.analyzer.analyze(
            "I'm thinking about leaving my corporate job to go freelance. "
            "I have a mortgage and two kids but I'm burning out."
        ))

        assert isinstance(result, QueryAnalysis)
        assert result.decision_type == "career"
        assert result.stakes == "high"
        assert "fear" in result.emotional_state
        assert len(result.key_factors) >= 2

    def test_analyze_short_query_returns_fallback(self):
        """Short queries should return a basic analysis without calling LLM."""
        result = asyncio.run(self.analyzer.analyze("help"))
        assert isinstance(result, QueryAnalysis)
        assert result.decision_type == "other"
        # LLM should not have been called
        self.mock_llm.analyze_query.assert_not_called()

    def test_analyze_llm_failure_returns_keyword_fallback(self):
        """When LLM fails, should fall back to keyword detection."""
        self.mock_llm.analyze_query = AsyncMock(side_effect=Exception("API error"))

        result = asyncio.run(self.analyzer.analyze(
            "I'm thinking about quitting my job and moving abroad"
        ))

        assert isinstance(result, QueryAnalysis)
        assert result.decision_type in ("career", "relocation")

    def test_fallback_analysis_detects_relationship(self):
        """Keyword fallback should detect relationship decisions."""
        result = self.analyzer._fallback_analysis(
            "I'm considering ending my marriage after 10 years"
        )
        assert result.decision_type == "relationship"

    def test_fallback_analysis_detects_financial(self):
        """Keyword fallback should detect financial decisions."""
        result = self.analyzer._fallback_analysis(
            "Should I invest my savings in this opportunity?"
        )
        assert result.decision_type == "financial"


class TestQueryEmbedder:
    """Tests for the QueryEmbedder component."""

    def setup_method(self):
        self.mock_embedder = MagicMock()
        self.query_embedder = QueryEmbedder(self.mock_embedder)

    @patch("rag.query.query_embedder.genai")
    def test_embed_query_returns_vector(self, mock_genai):
        """embed_query() should return a list of floats."""
        mock_genai.embed_content.return_value = {
            "embedding": [0.1] * 3072,
        }

        result = self.query_embedder.embed_query("test query")
        assert result is not None
        assert len(result) == 3072
        mock_genai.embed_content.assert_called_once()

    def test_embed_query_empty_returns_none(self):
        """Empty query should return None without calling API."""
        result = self.query_embedder.embed_query("")
        assert result is None

    @patch("rag.query.query_embedder.genai")
    def test_embed_dual_returns_both(self, mock_genai):
        """embed_dual() should return both primary and focused embeddings."""
        mock_genai.embed_content.return_value = {
            "embedding": [0.2] * 3072,
        }

        primary, focused = self.query_embedder.embed_dual(
            "Should I leave my job?",
            "Stories from people who left corporate jobs"
        )
        assert primary is not None
        assert focused is not None
        assert mock_genai.embed_content.call_count == 2
