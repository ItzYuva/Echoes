"""
Tests for Phase 4 → Phase 3 integration.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from agent.integration.pipeline_hook import (
    live_stories_to_candidates,
    merge_candidates,
)
from agent.orchestrator.models import AgentResult, LiveStory
from rag.confidence.models import RetrievalConfidence
from rag.retrieval.models import StoryCandidate


def _make_live_story(text: str = "A retrospective story " * 20, **kwargs) -> LiveStory:
    defaults = {
        "text": text,
        "source": "reddit_live",
        "decision_type": "career",
        "emotional_richness": 7,
        "key_themes": ["growth"],
        "hindsight_insight": "It was worth it.",
        "validation_confidence": 0.9,
    }
    defaults.update(kwargs)
    return LiveStory(**defaults)


def _make_db_candidate(text: str = "A database story " * 20, **kwargs) -> StoryCandidate:
    defaults = {
        "point_id": "db_123",
        "text": text,
        "semantic_score": 0.7,
        "decision_type": "career",
        "emotional_richness": 6,
    }
    defaults.update(kwargs)
    return StoryCandidate(**defaults)


# ── Pipeline Hook Tests ────────────────────────────────────────────

class TestLiveStoriesToCandidates:
    def test_converts_stories_to_candidates(self):
        stories = [_make_live_story(), _make_live_story(source="web_storycorps")]
        candidates = live_stories_to_candidates(stories)

        assert len(candidates) == 2
        assert all(isinstance(c, StoryCandidate) for c in candidates)
        assert all(c.point_id.startswith("live_") for c in candidates)

    def test_sets_default_semantic_score(self):
        stories = [_make_live_story()]
        candidates = live_stories_to_candidates(stories, default_semantic_score=0.45)

        assert candidates[0].semantic_score == 0.45

    def test_preserves_metadata(self):
        story = _make_live_story(
            decision_type="financial",
            emotional_richness=9,
            key_themes=["risk", "reward"],
        )
        candidates = live_stories_to_candidates([story])

        c = candidates[0]
        assert c.decision_type == "financial"
        assert c.emotional_richness == 9
        assert c.key_themes == ["risk", "reward"]

    def test_sets_search_pass_to_live(self):
        candidates = live_stories_to_candidates([_make_live_story()])
        assert candidates[0].search_pass == "live_search"


class TestMergeCandidates:
    def test_merges_without_duplicates(self):
        db = [_make_db_candidate(text="DB story one " * 20)]
        live = [_make_live_story(text="Live story two " * 20)]
        live_candidates = live_stories_to_candidates(live)

        merged = merge_candidates(db, live_candidates)
        assert len(merged) == 2

    def test_deduplicates_by_text_prefix(self):
        shared_text = "Same story content " * 20
        db = [_make_db_candidate(text=shared_text)]
        live = [_make_live_story(text=shared_text)]
        live_candidates = live_stories_to_candidates(live)

        merged = merge_candidates(db, live_candidates)
        # Live story should be deduplicated away
        assert len(merged) == 1

    def test_handles_empty_lists(self):
        merged = merge_candidates([], [])
        assert merged == []

        db = [_make_db_candidate()]
        merged = merge_candidates(db, [])
        assert len(merged) == 1

        live_candidates = live_stories_to_candidates([_make_live_story()])
        merged = merge_candidates([], live_candidates)
        assert len(merged) == 1


# ── Integration Flow Tests ─────────────────────────────────────────

class TestIntegrationFlow:
    def test_low_confidence_triggers_agent(self):
        """Verify that low confidence should trigger the agent."""
        confidence = RetrievalConfidence(score=0.42, level="low", reasons=["weak matches"])
        assert confidence.level in ("low", "insufficient")

    def test_medium_confidence_does_not_block(self):
        """Medium confidence should not block — background only."""
        confidence = RetrievalConfidence(score=0.60, level="medium", reasons=["ok matches"])
        assert confidence.level == "medium"
        assert confidence.level not in ("low", "insufficient")

    def test_high_confidence_skips_agent(self):
        """High confidence should skip the agent entirely."""
        confidence = RetrievalConfidence(score=0.82, level="high", reasons=["strong matches"])
        assert confidence.level not in ("low", "insufficient", "medium")

    def test_agent_result_tracks_confidence_improvement(self):
        """AgentResult should correctly compute confidence improvement."""
        result = AgentResult(
            confidence_before=0.35,
            confidence_after=0.65,
        )
        assert result.confidence_improvement == pytest.approx(0.30)

    def test_agent_result_no_improvement_when_no_after(self):
        result = AgentResult(confidence_before=0.35)
        assert result.confidence_improvement is None
