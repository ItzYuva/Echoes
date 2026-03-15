"""
Tests for story validation pipeline.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from agent.config.agent_config import AgentSettings
from agent.tools.story_validator import StoryValidator


def _make_retrospective_text() -> str:
    """A text that should pass heuristic + LLM classification."""
    return (
        "Five years ago I left my corporate job to become a freelance designer. "
        "Looking back, it was the scariest thing I've ever done. I remember the "
        "sleepless nights, the fear of failure, the judgment from my family. "
        "But three years later, I realize it was the best decision I ever made. "
        "The freedom, the creativity, the growth — none of it would have happened "
        "if I'd stayed in that cubicle. I wish I had done it sooner. The fear of "
        "leaving was worse than anything that actually happened after."
    )


def _make_non_retrospective_text() -> str:
    """A text that should fail — advice-seeking, not retrospective."""
    return (
        "I'm thinking about leaving my job to start freelancing. Should I do it? "
        "Any advice? What should I consider? I'm really scared right now and "
        "I don't know what to do. Help me decide please."
    )


def _make_low_quality_text() -> str:
    """A text that is retrospective but low quality."""
    return (
        "Yeah I changed jobs a while back. It was fine I guess. "
        "Things worked out okay. Nothing special really happened."
    )


class TestStoryValidator:
    def setup_method(self):
        """Set up validator with mock dependencies."""
        from classifiers.heuristic_filter import HeuristicFilter

        self.heuristic = HeuristicFilter()
        self.mock_llm = AsyncMock()
        self.settings = AgentSettings()
        self.settings.min_emotional_richness = 3

        self.validator = StoryValidator(
            self.heuristic, self.mock_llm, self.settings
        )

    @pytest.mark.asyncio
    async def test_retrospective_passes_all_stages(self):
        """A genuine retrospective text should pass heuristic + LLM + metadata."""
        from storage.models import (
            ClassificationResult,
            DecisionType,
            OutcomeSentiment,
            StoryMetadata,
        )

        self.mock_llm.classify = AsyncMock(
            return_value=(ClassificationResult.RETROSPECTIVE, "RETROSPECTIVE")
        )
        self.mock_llm.extract_metadata = AsyncMock(
            return_value=StoryMetadata(
                decision_type=DecisionType.CAREER,
                decision_subcategory="leaving corporate for freelance",
                outcome_sentiment=OutcomeSentiment.POSITIVE,
                time_elapsed_months=60,
                emotional_richness=8,
                outcome_clarity=True,
                key_themes=["fear", "growth", "freedom"],
                hindsight_insight="The fear of leaving was worse than the reality.",
            )
        )

        result = await self.validator.validate(_make_retrospective_text())

        assert result.is_retrospective is True
        assert result.confidence == 0.9
        assert result.rejection_reason is None
        assert result.metadata is not None
        assert result.metadata["decision_type"] == "career"
        assert result.metadata["emotional_richness"] == 8

    @pytest.mark.asyncio
    async def test_non_retrospective_fails_at_heuristic(self):
        """Advice-seeking text should fail at heuristic stage."""
        result = await self.validator.validate(_make_non_retrospective_text())

        assert result.is_retrospective is False
        assert result.rejection_reason == "failed_heuristic"
        # LLM should not have been called
        self.mock_llm.classify.assert_not_called()

    @pytest.mark.asyncio
    async def test_fails_at_llm_classification(self):
        """Text that passes heuristic but LLM says not retrospective."""
        from storage.models import ClassificationResult

        self.mock_llm.classify = AsyncMock(
            return_value=(ClassificationResult.NOT_RETROSPECTIVE, "NOT_RETROSPECTIVE")
        )

        result = await self.validator.validate(_make_retrospective_text())

        assert result.is_retrospective is False
        assert result.rejection_reason == "not_retrospective"
        # Metadata extraction should not have been called
        self.mock_llm.extract_metadata.assert_not_called()

    @pytest.mark.asyncio
    async def test_fails_at_quality_floor(self):
        """Retrospective text with low emotional richness should be rejected."""
        from storage.models import (
            ClassificationResult,
            DecisionType,
            OutcomeSentiment,
            StoryMetadata,
        )

        self.mock_llm.classify = AsyncMock(
            return_value=(ClassificationResult.RETROSPECTIVE, "RETROSPECTIVE")
        )
        self.mock_llm.extract_metadata = AsyncMock(
            return_value=StoryMetadata(
                decision_type=DecisionType.CAREER,
                emotional_richness=2,  # Below threshold of 3
            )
        )

        result = await self.validator.validate(_make_retrospective_text())

        assert result.is_retrospective is False
        assert result.rejection_reason == "low_quality"

    @pytest.mark.asyncio
    async def test_handles_llm_error_gracefully(self):
        """LLM errors should not crash — return rejected result."""
        self.mock_llm.classify = AsyncMock(side_effect=Exception("API error"))

        result = await self.validator.validate(_make_retrospective_text())

        assert result.is_retrospective is False
        assert result.rejection_reason == "classification_error"

    @pytest.mark.asyncio
    async def test_handles_metadata_extraction_error(self):
        """Metadata extraction failure should not crash."""
        from storage.models import ClassificationResult

        self.mock_llm.classify = AsyncMock(
            return_value=(ClassificationResult.RETROSPECTIVE, "RETROSPECTIVE")
        )
        self.mock_llm.extract_metadata = AsyncMock(return_value=None)

        result = await self.validator.validate(_make_retrospective_text())

        assert result.is_retrospective is False
        assert result.rejection_reason == "metadata_extraction_failed"

    @pytest.mark.asyncio
    async def test_batch_validation(self):
        """Batch validation should filter and return only validated stories."""
        from storage.models import (
            ClassificationResult,
            DecisionType,
            OutcomeSentiment,
            StoryMetadata,
        )

        self.mock_llm.classify = AsyncMock(
            return_value=(ClassificationResult.RETROSPECTIVE, "RETROSPECTIVE")
        )
        self.mock_llm.extract_metadata = AsyncMock(
            return_value=StoryMetadata(
                decision_type=DecisionType.CAREER,
                emotional_richness=7,
                outcome_clarity=True,
                key_themes=["growth"],
                hindsight_insight="It worked out.",
            )
        )

        stories = [
            {"text": _make_retrospective_text(), "source": "reddit_live", "source_url": "https://reddit.com/1"},
            {"text": _make_non_retrospective_text(), "source": "reddit_live", "source_url": "https://reddit.com/2"},
        ]

        validated = await self.validator.validate_batch(stories)

        # Only the retrospective one should pass
        assert len(validated) == 1
        assert validated[0].source == "reddit_live"
