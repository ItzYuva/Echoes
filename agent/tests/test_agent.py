"""
Tests for the agent orchestrator decision logic.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agent.config.agent_config import AgentSettings
from agent.orchestrator.agent import AgentOrchestrator
from agent.orchestrator.models import LiveStory
from rag.confidence.models import RetrievalConfidence


def _make_live_story(**kwargs) -> LiveStory:
    defaults = {
        "text": "Five years ago I made a big change. Looking back it was worth it. " * 5,
        "source": "reddit_live",
        "source_url": "https://reddit.com/test",
        "decision_type": "career",
        "emotional_richness": 7,
        "outcome_clarity": True,
        "key_themes": ["growth"],
        "hindsight_insight": "It worked out.",
        "validation_confidence": 0.9,
    }
    defaults.update(kwargs)
    return LiveStory(**defaults)


class TestAgentOrchestrator:
    def setup_method(self):
        self.mock_llm = AsyncMock()
        self.mock_reddit = AsyncMock()
        self.mock_web = AsyncMock()
        self.mock_validator = AsyncMock()

        self.settings = AgentSettings()
        self.settings.max_tool_calls = 3

        self.agent = AgentOrchestrator(
            llm_client=self.mock_llm,
            reddit_search=self.mock_reddit,
            web_search=self.mock_web,
            validator=self.mock_validator,
            agent_settings=self.settings,
        )

        # Default: LLM generates search queries
        self.mock_llm.build_search_queries = AsyncMock(
            return_value=["career change looking back", "left job years later"]
        )

    @pytest.mark.asyncio
    async def test_returns_validated_stories(self):
        """Agent should return validated stories from search tools."""
        raw_results = [{"text": "story text " * 30, "source": "reddit_live", "source_url": "https://reddit.com/1"}]
        self.mock_reddit.search = AsyncMock(return_value=raw_results)
        self.mock_reddit.get_subreddits_for_decision = MagicMock(return_value=["careerguidance"])
        self.mock_web.search = AsyncMock(return_value=[])
        self.mock_validator.validate_batch = AsyncMock(
            return_value=[_make_live_story()]
        )

        confidence = RetrievalConfidence(score=0.35, level="low", reasons=["test"])
        result = await self.agent.search_for_stories(
            decision_text="leaving my job",
            query_analysis={"decision_type": "career", "core_tension": "stability vs growth"},
            confidence=confidence,
        )

        assert result.stories_count >= 1
        assert result.tool_calls_made >= 1
        assert result.confidence_before == 0.35

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_results(self):
        """Agent should return empty result gracefully when tools find nothing."""
        self.mock_reddit.search = AsyncMock(return_value=[])
        self.mock_reddit.get_subreddits_for_decision = MagicMock(return_value=["AskReddit"])
        self.mock_web.search = AsyncMock(return_value=[])
        self.mock_validator.validate_batch = AsyncMock(return_value=[])

        confidence = RetrievalConfidence(score=0.30, level="insufficient", reasons=["test"])
        result = await self.agent.search_for_stories(
            decision_text="very niche decision",
            query_analysis={"decision_type": "other"},
            confidence=confidence,
        )

        assert result.stories_count == 0
        assert result.tool_calls_made >= 1

    @pytest.mark.asyncio
    async def test_respects_max_tool_calls(self):
        """Agent should not exceed the max tool calls limit."""
        self.settings.max_tool_calls = 1

        self.mock_reddit.search = AsyncMock(return_value=[])
        self.mock_reddit.get_subreddits_for_decision = MagicMock(return_value=["AskReddit"])
        self.mock_web.search = AsyncMock(return_value=[])
        self.mock_validator.validate_batch = AsyncMock(return_value=[])

        confidence = RetrievalConfidence(score=0.30, level="low", reasons=["test"])
        result = await self.agent.search_for_stories(
            decision_text="test",
            query_analysis={"decision_type": "career"},
            confidence=confidence,
        )

        assert result.tool_calls_made <= 1

    @pytest.mark.asyncio
    async def test_stops_when_enough_stories(self):
        """Agent should stop searching when it has enough stories."""
        stories = [_make_live_story(text=f"Story {i} " * 30) for i in range(6)]

        self.mock_reddit.search = AsyncMock(return_value=[{"text": "x" * 200}] * 6)
        self.mock_reddit.get_subreddits_for_decision = MagicMock(return_value=["AskReddit"])
        self.mock_validator.validate_batch = AsyncMock(return_value=stories)

        confidence = RetrievalConfidence(score=0.30, level="low", reasons=["test"])
        result = await self.agent.search_for_stories(
            decision_text="test",
            query_analysis={"decision_type": "career"},
            confidence=confidence,
        )

        # Should stop after first tool call since we got 6 stories (>= 5 threshold)
        assert result.tool_calls_made == 1

    @pytest.mark.asyncio
    async def test_handles_tool_failure_gracefully(self):
        """Agent should handle tool failures without crashing."""
        self.mock_reddit.search = AsyncMock(side_effect=Exception("Network error"))
        self.mock_reddit.get_subreddits_for_decision = MagicMock(return_value=["AskReddit"])
        self.mock_web.search = AsyncMock(return_value=[])
        self.mock_validator.validate_batch = AsyncMock(return_value=[])

        confidence = RetrievalConfidence(score=0.30, level="low", reasons=["test"])
        result = await self.agent.search_for_stories(
            decision_text="test",
            query_analysis={"decision_type": "career"},
            confidence=confidence,
        )

        # Should have recorded the error in tool calls
        assert any(tc.error is not None for tc in result.tool_calls)

    def test_career_decision_prioritizes_reddit(self):
        """Career decisions should search Reddit first."""
        order = self.agent._decide_tool_order("career")
        assert order[0] == "search_reddit_stories"

    def test_relationship_decision_prioritizes_reddit(self):
        order = self.agent._decide_tool_order("relationship")
        assert order[0] == "search_reddit_stories"

    def test_lifestyle_decision_prioritizes_web(self):
        """Lifestyle/existential decisions should search web first."""
        order = self.agent._decide_tool_order("lifestyle")
        assert order[0] == "search_web_stories"

    def test_other_decision_prioritizes_web(self):
        order = self.agent._decide_tool_order("other")
        assert order[0] == "search_web_stories"

    @pytest.mark.asyncio
    async def test_fallback_query_generation(self):
        """Agent should fall back to keyword extraction if LLM fails."""
        self.mock_llm.build_search_queries = AsyncMock(
            side_effect=Exception("LLM unavailable")
        )
        self.mock_reddit.search = AsyncMock(return_value=[])
        self.mock_reddit.get_subreddits_for_decision = MagicMock(return_value=["AskReddit"])
        self.mock_web.search = AsyncMock(return_value=[])
        self.mock_validator.validate_batch = AsyncMock(return_value=[])

        confidence = RetrievalConfidence(score=0.30, level="low", reasons=["test"])
        # Should not crash — falls back to keyword extraction
        result = await self.agent.search_for_stories(
            decision_text="leaving my corporate job for freelancing",
            query_analysis={"decision_type": "career"},
            confidence=confidence,
        )
        assert isinstance(result.stories, list)
