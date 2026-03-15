"""
Echoes Phase 4 -- Pipeline Integration Hook

Hooks Phase 4's agent into Phase 3's RAG pipeline. Converts live stories
into StoryCandidate objects so they integrate seamlessly with the existing
re-ranking pipeline.
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from agent.orchestrator.models import AgentResult, LiveStory
from config.logging_config import get_logger
from rag.retrieval.models import StoryCandidate

logger = get_logger(__name__)


def live_stories_to_candidates(
    live_stories: List[LiveStory],
    default_semantic_score: float = 0.5,
) -> List[StoryCandidate]:
    """Convert validated LiveStory objects into StoryCandidate objects.

    This bridges Phase 4 and Phase 3: live stories become candidates
    that can be re-ranked alongside database stories using the exact
    same scoring functions.

    Args:
        live_stories: Validated stories from the agent.
        default_semantic_score: Default semantic score for live stories
            (they don't have Qdrant similarity scores).

    Returns:
        List of StoryCandidate objects ready for re-ranking.
    """
    candidates = []

    for story in live_stories:
        candidate = StoryCandidate(
            point_id=f"live_{story.id}",
            text=story.text,
            semantic_score=default_semantic_score,
            source=story.source,
            subreddit="",
            decision_type=story.decision_type,
            decision_subcategory=story.decision_subcategory,
            outcome_sentiment=story.outcome_sentiment,
            time_elapsed_months=story.time_elapsed_months,
            emotional_richness=story.emotional_richness,
            outcome_clarity=story.outcome_clarity,
            key_themes=story.key_themes,
            hindsight_insight=story.hindsight_insight,
            search_pass="live_search",
        )
        candidates.append(candidate)

    logger.info(
        "Converted %d live stories to candidates", len(candidates)
    )

    return candidates


def merge_candidates(
    db_candidates: List[StoryCandidate],
    live_candidates: List[StoryCandidate],
) -> List[StoryCandidate]:
    """Merge database and live search candidates.

    Deduplicates by checking for text overlap between live and DB stories.

    Args:
        db_candidates: Candidates from Qdrant retrieval.
        live_candidates: Candidates from live search.

    Returns:
        Merged and deduplicated candidate list.
    """
    # Simple dedup: check if live story text is very similar to any DB story
    db_texts = {c.text[:200].lower() for c in db_candidates}

    unique_live = []
    for live in live_candidates:
        prefix = live.text[:200].lower()
        if prefix not in db_texts:
            unique_live.append(live)
            db_texts.add(prefix)

    merged = db_candidates + unique_live

    logger.info(
        "Merged %d DB + %d live candidates (%d live deduplicated away)",
        len(db_candidates),
        len(unique_live),
        len(live_candidates) - len(unique_live),
    )

    return merged
