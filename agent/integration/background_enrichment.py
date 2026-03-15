"""
Echoes Phase 4 -- Background Enrichment

Silently enriches the Qdrant database when confidence is "medium".
Runs in the background — the current user doesn't wait. The NEXT user
with a similar query benefits from the added stories.

This is the silent growth engine that makes the database more complete
over time, reducing the need for live search.
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from agent.config.agent_config import AgentSettings
from agent.orchestrator.agent import AgentOrchestrator
from agent.orchestrator.models import LiveStory
from agent.tools.search_utils import content_hash
from config.logging_config import get_logger
from rag.confidence.models import RetrievalConfidence

logger = get_logger(__name__)


async def background_enrichment(
    agent: AgentOrchestrator,
    decision_text: str,
    query_analysis: Dict[str, Any],
    embedder,
    qdrant_store,
) -> int:
    """Search for stories and add them to Qdrant for future queries.

    The current user doesn't see these results — the NEXT user with a
    similar query will find them in the database.

    Args:
        agent: Agent orchestrator instance.
        decision_text: The user's decision description.
        query_analysis: Structured query analysis.
        embedder: EmbeddingGenerator for creating vectors.
        qdrant_store: QdrantStore for upserting stories.

    Returns:
        Number of stories added to Qdrant.
    """
    try:
        # Create a synthetic medium-confidence trigger
        confidence = RetrievalConfidence(
            score=0.6,
            level="medium",
            reasons=["background enrichment"],
        )

        agent_result = await agent.search_for_stories(
            decision_text=decision_text,
            query_analysis=query_analysis,
            confidence=confidence,
        )

        if not agent_result.stories:
            logger.info("Background enrichment found no new stories")
            return 0

        # Check for existing stories in Qdrant before adding
        added = 0
        for story in agent_result.stories:
            try:
                added += await _embed_and_store(story, embedder, qdrant_store)
            except Exception as e:
                logger.error("Failed to store enrichment story: %s", e)
                continue

        logger.info(
            "Background enrichment added %d stories to Qdrant", added
        )
        return added

    except Exception as e:
        logger.error("Background enrichment failed: %s", e)
        return 0


async def _embed_and_store(
    story: LiveStory,
    embedder,
    qdrant_store,
) -> int:
    """Embed a single story and store it in Qdrant.

    Args:
        story: Validated LiveStory to store.
        embedder: EmbeddingGenerator instance.
        qdrant_store: QdrantStore instance.

    Returns:
        1 if stored successfully, 0 otherwise.
    """
    from storage.models import StoryChunk

    # Generate embedding
    embedding = embedder.embed_single(story.text)
    if not embedding:
        logger.warning("Failed to embed story for enrichment")
        return 0

    # Build a StoryChunk to match the Qdrant upsert interface
    chunk = StoryChunk(
        chunk_id=str(uuid.uuid4()),
        parent_id=f"enrichment_{story.id}",
        text=story.text,
        source=f"live_enrichment_{story.source}",
        decision_type=story.decision_type,
        decision_subcategory=story.decision_subcategory,
        outcome_sentiment=story.outcome_sentiment,
        time_elapsed_months=story.time_elapsed_months,
        emotional_richness=story.emotional_richness,
        outcome_clarity=story.outcome_clarity,
        key_themes=story.key_themes,
        hindsight_insight=story.hindsight_insight,
        classification_confidence="RETROSPECTIVE",
    )

    count = qdrant_store.upsert_chunks([chunk], [embedding])
    return count
