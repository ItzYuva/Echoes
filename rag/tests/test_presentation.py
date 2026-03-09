"""
Echoes Phase 3 -- Presentation Tests

Tests for prompt building and story presentation.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock

from rag.presentation.models import PresentationResult
from rag.presentation.presenter import StoryPresenter
from rag.presentation.prompts import (
    build_presentation_prompt,
    format_stories_for_prompt,
)
from rag.query.models import QueryAnalysis
from rag.ranking.models import ScoredStory


def _make_story(**kwargs) -> ScoredStory:
    return ScoredStory(
        point_id=kwargs.get("id", "test"),
        text=kwargs.get("text", "I left my job three years ago..."),
        decision_type=kwargs.get("decision_type", "career"),
        decision_subcategory=kwargs.get("subcategory", "leaving corporate"),
        outcome_sentiment=kwargs.get("sentiment", "positive"),
        time_elapsed_months=kwargs.get("months", 36),
        key_themes=kwargs.get("themes", ["change", "growth"]),
        relevance_note=kwargs.get("note", ""),
    )


class TestPromptFormatting:
    """Tests for prompt construction."""

    def test_format_stories_includes_metadata(self):
        """Formatted stories should include decision type, time, and themes."""
        stories = [_make_story(months=60)]
        formatted = format_stories_for_prompt(stories)
        assert "career" in formatted
        assert "5 year" in formatted
        assert "change" in formatted

    def test_format_stories_month_display(self):
        """Stories < 12 months should show months."""
        stories = [_make_story(months=8)]
        formatted = format_stories_for_prompt(stories)
        assert "8 month" in formatted

    def test_build_prompt_contains_all_sections(self):
        """Full prompt should contain user text, analysis, and stories."""
        prompt = build_presentation_prompt(
            user_text="Should I leave my job?",
            decision_type="career",
            decision_subcategory="leaving corporate",
            core_tension="security vs. autonomy",
            stakes="high",
            stories=[_make_story()],
        )
        assert "Should I leave my job?" in prompt
        assert "career" in prompt
        assert "security vs. autonomy" in prompt
        assert "Do NOT give advice" in prompt


class TestStoryPresenter:
    """Tests for the StoryPresenter component."""

    def test_present_calls_llm(self):
        """present() should call the LLM and return PresentationResult."""
        mock_llm = MagicMock()
        mock_llm.present_stories = AsyncMock(
            return_value="Here are stories from people who stood where you're standing..."
        )

        presenter = StoryPresenter(mock_llm)
        analysis = QueryAnalysis(
            decision_type="career",
            decision_subcategory="leaving corporate",
            core_tension="security vs autonomy",
            stakes="high",
        )

        result = asyncio.run(presenter.present(
            user_text="Should I leave my job?",
            query_analysis=analysis,
            stories=[_make_story()],
        ))

        assert isinstance(result, PresentationResult)
        assert result.stories_presented == 1
        assert "standing" in result.text

    def test_present_empty_stories(self):
        """No stories should return a graceful message."""
        mock_llm = MagicMock()
        presenter = StoryPresenter(mock_llm)
        analysis = QueryAnalysis()

        result = asyncio.run(presenter.present(
            user_text="test",
            query_analysis=analysis,
            stories=[],
        ))

        assert "enough relevant stories" in result.text
        assert result.stories_presented == 0
