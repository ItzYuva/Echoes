"""
Tests for background enrichment (silent database growth).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agent.config.agent_config import AgentSettings
from agent.orchestrator.models import AgentResult, LiveStory


def _make_live_story(**kwargs) -> LiveStory:
    defaults = {
        "text": "A validated retrospective story about career change. " * 10,
        "source": "reddit_live",
        "decision_type": "career",
        "emotional_richness": 7,
        "outcome_clarity": True,
        "key_themes": ["growth"],
        "hindsight_insight": "Worth it.",
        "validation_confidence": 0.9,
    }
    defaults.update(kwargs)
    return LiveStory(**defaults)


class TestBackgroundEnrichment:
    @pytest.mark.asyncio
    async def test_stores_stories_in_qdrant(self):
        """Enrichment should embed and upsert validated stories."""
        from agent.integration.background_enrichment import _embed_and_store

        story = _make_live_story()
        mock_embedder = MagicMock()
        mock_embedder.embed_single = MagicMock(return_value=[0.1] * 3072)

        mock_qdrant = MagicMock()
        mock_qdrant.upsert_chunks = MagicMock(return_value=1)

        count = await _embed_and_store(story, mock_embedder, mock_qdrant)

        assert count == 1
        mock_embedder.embed_single.assert_called_once_with(story.text)
        mock_qdrant.upsert_chunks.assert_called_once()

        # Verify the chunk has the right source
        chunk = mock_qdrant.upsert_chunks.call_args[0][0][0]
        assert "live_enrichment" in chunk.source

    @pytest.mark.asyncio
    async def test_handles_embedding_failure(self):
        """Should return 0 if embedding fails."""
        from agent.integration.background_enrichment import _embed_and_store

        story = _make_live_story()
        mock_embedder = MagicMock()
        mock_embedder.embed_single = MagicMock(return_value=None)

        mock_qdrant = MagicMock()

        count = await _embed_and_store(story, mock_embedder, mock_qdrant)

        assert count == 0
        mock_qdrant.upsert_chunks.assert_not_called()

    @pytest.mark.asyncio
    async def test_full_enrichment_flow(self):
        """Full background enrichment should run agent and store results."""
        from agent.integration.background_enrichment import background_enrichment

        stories = [_make_live_story(), _make_live_story(text="Another story " * 20)]

        mock_agent = AsyncMock()
        mock_agent.search_for_stories = AsyncMock(
            return_value=AgentResult(stories=stories)
        )

        mock_embedder = MagicMock()
        mock_embedder.embed_single = MagicMock(return_value=[0.1] * 3072)

        mock_qdrant = MagicMock()
        mock_qdrant.upsert_chunks = MagicMock(return_value=1)

        added = await background_enrichment(
            agent=mock_agent,
            decision_text="career change",
            query_analysis={"decision_type": "career"},
            embedder=mock_embedder,
            qdrant_store=mock_qdrant,
        )

        assert added == 2
        assert mock_qdrant.upsert_chunks.call_count == 2

    @pytest.mark.asyncio
    async def test_enrichment_handles_agent_failure(self):
        """Should return 0 if agent search fails."""
        from agent.integration.background_enrichment import background_enrichment

        mock_agent = AsyncMock()
        mock_agent.search_for_stories = AsyncMock(
            side_effect=Exception("Agent failed")
        )

        added = await background_enrichment(
            agent=mock_agent,
            decision_text="test",
            query_analysis={"decision_type": "other"},
            embedder=MagicMock(),
            qdrant_store=MagicMock(),
        )

        assert added == 0

    @pytest.mark.asyncio
    async def test_enrichment_with_no_stories(self):
        """Should return 0 when agent finds nothing."""
        from agent.integration.background_enrichment import background_enrichment

        mock_agent = AsyncMock()
        mock_agent.search_for_stories = AsyncMock(
            return_value=AgentResult(stories=[])
        )

        added = await background_enrichment(
            agent=mock_agent,
            decision_text="test",
            query_analysis={"decision_type": "other"},
            embedder=MagicMock(),
            qdrant_store=MagicMock(),
        )

        assert added == 0
