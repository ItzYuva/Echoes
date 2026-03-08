"""
Echoes Data Pipeline — Tagger Unit Tests

Tests for the metadata extraction parser. Uses mock LLM responses
to verify that JSON parsing and fallback handling work correctly.
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from llm.gemini_client import GeminiClient
from storage.models import DecisionType, OutcomeSentiment, StoryMetadata


class TestMetadataParsing:
    """Tests for the metadata JSON parsing logic."""

    def test_valid_json_parsing(self):
        """Valid JSON response should parse correctly."""
        raw = json.dumps({
            "decision_type": "career",
            "decision_subcategory": "leaving a job",
            "outcome_sentiment": "positive",
            "time_elapsed": 36,
            "emotional_richness": 8,
            "outcome_clarity": True,
            "key_themes": ["regret", "growth", "fear of unknown"],
            "hindsight_insight": "The fear of leaving was worse than anything that actually happened.",
        })

        result = GeminiClient._parse_metadata(raw)

        assert result is not None
        assert result.decision_type == DecisionType.CAREER
        assert result.decision_subcategory == "leaving a job"
        assert result.outcome_sentiment == OutcomeSentiment.POSITIVE
        assert result.time_elapsed_months == 36
        assert result.emotional_richness == 8
        assert result.outcome_clarity is True
        assert len(result.key_themes) == 3
        assert "regret" in result.key_themes

    def test_json_with_markdown_fences(self):
        """JSON wrapped in markdown code fences should still parse."""
        raw = '```json\n{"decision_type": "relationship", "decision_subcategory": "breakup", "outcome_sentiment": "mixed", "time_elapsed": 12, "emotional_richness": 7, "outcome_clarity": true, "key_themes": ["healing"], "hindsight_insight": "It had to end."}\n```'

        result = GeminiClient._parse_metadata(raw)
        assert result is not None
        assert result.decision_type == DecisionType.RELATIONSHIP

    def test_invalid_json(self):
        """Invalid JSON should return None without crashing."""
        raw = "This is not JSON at all"
        result = GeminiClient._parse_metadata(raw)
        assert result is None

    def test_unknown_decision_type_defaults(self):
        """Unknown decision type should default to 'other'."""
        raw = json.dumps({
            "decision_type": "unknown_type",
            "decision_subcategory": "something",
            "outcome_sentiment": "positive",
            "time_elapsed": 12,
            "emotional_richness": 5,
            "outcome_clarity": True,
            "key_themes": [],
            "hindsight_insight": "Test",
        })

        result = GeminiClient._parse_metadata(raw)
        assert result is not None
        assert result.decision_type == DecisionType.OTHER

    def test_emotional_richness_clamped(self):
        """Emotional richness should be clamped between 1 and 10."""
        raw = json.dumps({
            "decision_type": "career",
            "decision_subcategory": "test",
            "outcome_sentiment": "positive",
            "time_elapsed": 12,
            "emotional_richness": 15,  # Should be clamped to 10
            "outcome_clarity": True,
            "key_themes": [],
            "hindsight_insight": "Test",
        })

        result = GeminiClient._parse_metadata(raw)
        assert result is not None
        assert result.emotional_richness == 10

    def test_themes_limited_to_five(self):
        """Key themes should be limited to 5 items."""
        raw = json.dumps({
            "decision_type": "career",
            "decision_subcategory": "test",
            "outcome_sentiment": "neutral",
            "time_elapsed": -1,
            "emotional_richness": 5,
            "outcome_clarity": False,
            "key_themes": ["a", "b", "c", "d", "e", "f", "g"],
            "hindsight_insight": "Test",
        })

        result = GeminiClient._parse_metadata(raw)
        assert result is not None
        assert len(result.key_themes) == 5

    def test_missing_fields_use_defaults(self):
        """Missing fields should use sensible defaults."""
        raw = json.dumps({})

        result = GeminiClient._parse_metadata(raw)
        assert result is not None
        assert result.decision_type == DecisionType.OTHER
        assert result.time_elapsed_months == -1
        assert result.emotional_richness == 5
        assert result.key_themes == []


class TestClassificationParsing:
    """Tests for classification response parsing."""

    def test_exact_retrospective(self):
        result = GeminiClient._parse_classification("RETROSPECTIVE")
        assert result.value == "RETROSPECTIVE"

    def test_exact_not_retrospective(self):
        result = GeminiClient._parse_classification("NOT_RETROSPECTIVE")
        assert result.value == "NOT_RETROSPECTIVE"

    def test_exact_ambiguous(self):
        result = GeminiClient._parse_classification("AMBIGUOUS")
        assert result.value == "AMBIGUOUS"

    def test_lowercase_retrospective(self):
        result = GeminiClient._parse_classification("retrospective")
        assert result.value == "RETROSPECTIVE"

    def test_whitespace_handling(self):
        result = GeminiClient._parse_classification("  RETROSPECTIVE  \n")
        assert result.value == "RETROSPECTIVE"

    def test_unexpected_response_defaults_ambiguous(self):
        result = GeminiClient._parse_classification("I'm not sure about this one")
        assert result.value == "AMBIGUOUS"

    def test_not_retrospective_with_space(self):
        result = GeminiClient._parse_classification("NOT RETROSPECTIVE")
        assert result.value == "NOT_RETROSPECTIVE"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
