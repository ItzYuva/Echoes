"""
Echoes Phase 3 -- Synthetic Story Generator (Component 0)

Uses Gemini Flash to generate realistic retrospective stories,
then runs them through the Phase 1 pipeline (tag + embed + store).
"""

from __future__ import annotations

import asyncio
import hashlib
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from config.logging_config import get_logger
from config.settings import Settings
from llm.gemini_client import GeminiClient
from processors.embedder import EmbeddingGenerator
from processors.tagger import StoryTagger
from seeder.generation_matrix import GENERATION_MATRIX, StorySpec
from storage.models import (
    ClassificationResult,
    ContentType,
    PipelineStatus,
    ScrapedItem,
    StoryChunk,
    StoryMetadata,
)
from storage.qdrant_store import QdrantStore
from storage.sqlite_store import SQLiteStore

logger = get_logger(__name__)


class SyntheticGenerator:
    """Generates synthetic retrospective stories and seeds them into Qdrant.

    Uses Gemini Flash to generate realistic stories, then processes
    them through the existing Phase 1 pipeline (tag → embed → store).

    Args:
        settings: Application settings.
    """

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.llm_client = GeminiClient(settings.gemini)
        self.embedder = EmbeddingGenerator(settings.gemini)
        self.tagger = StoryTagger(
            self.llm_client,
            SQLiteStore(settings.pipeline.staging_db_path),
            batch_size=10,
        )
        self.qdrant = QdrantStore(settings.qdrant, vector_size=3072)

    async def generate_and_seed(
        self,
        max_stories: Optional[int] = None,
        start_from: int = 0,
    ) -> dict:
        """Generate stories and seed them into Qdrant.

        Args:
            max_stories: Maximum stories to generate (None = all).
            start_from: Index in the generation matrix to start from.

        Returns:
            Stats dict with counts of generated, tagged, and stored stories.
        """
        specs = GENERATION_MATRIX[start_from:]
        if max_stories:
            specs = specs[:max_stories]

        stats = {
            "total_specs": len(specs),
            "generated": 0,
            "tag_success": 0,
            "tag_failed": 0,
            "embedded": 0,
            "stored": 0,
            "errors": 0,
        }

        # Ensure Qdrant collection exists
        self.qdrant.ensure_collection()

        for i, spec in enumerate(specs):
            try:
                logger.info(
                    "[%d/%d] Generating: %s — %s (%s, %s)",
                    i + 1, len(specs),
                    spec.decision_type, spec.scenario,
                    spec.outcome_tone, spec.time_elapsed,
                )

                # Generate story via LLM
                story_text = await self.llm_client.generate_synthetic_story(
                    decision_type=spec.decision_type,
                    scenario=spec.scenario,
                    time_elapsed=spec.time_elapsed,
                    outcome_tone=spec.outcome_tone,
                )
                stats["generated"] += 1

                # Extract metadata via tagger
                metadata = await self.llm_client.extract_metadata(story_text)
                if metadata:
                    stats["tag_success"] += 1
                else:
                    stats["tag_failed"] += 1
                    metadata = StoryMetadata(
                        decision_type=spec.decision_type,
                        outcome_sentiment=spec.outcome_tone,
                    )

                # Build chunk for Qdrant
                chunk = self._build_chunk(story_text, spec, metadata)

                # Embed
                embedding = self.embedder.embed_single(story_text)
                if not embedding:
                    logger.warning("Embedding failed for story %d", i)
                    stats["errors"] += 1
                    continue
                stats["embedded"] += 1

                # Store in Qdrant
                self.qdrant.upsert_chunks([chunk], [embedding])
                stats["stored"] += 1

                # Rate limit: small delay between generations
                await asyncio.sleep(1.0)

            except Exception as e:
                logger.error("Error on story %d: %s", i, e)
                stats["errors"] += 1

        return stats

    @staticmethod
    def _build_chunk(
        text: str, spec: StorySpec, metadata: StoryMetadata
    ) -> StoryChunk:
        """Build a StoryChunk from generated text and metadata."""
        content_hash = hashlib.sha256(text.encode()).hexdigest()
        parent_id = str(uuid.uuid4())

        # Parse time elapsed string to months
        time_months = _parse_time_to_months(spec.time_elapsed)

        return StoryChunk(
            chunk_id=str(uuid.uuid4()),
            parent_id=parent_id,
            text=text,
            source="synthetic",
            subreddit="generated",
            author_hash=content_hash[:16],
            scraped_at=datetime.now(timezone.utc),
            decision_type=metadata.decision_type if metadata.decision_type else spec.decision_type,
            decision_subcategory=metadata.decision_subcategory or spec.scenario,
            outcome_sentiment=metadata.outcome_sentiment if metadata.outcome_sentiment else spec.outcome_tone,
            time_elapsed_months=metadata.time_elapsed_months if metadata.time_elapsed_months > 0 else time_months,
            emotional_richness=metadata.emotional_richness,
            outcome_clarity=metadata.outcome_clarity,
            key_themes=metadata.key_themes,
            hindsight_insight=metadata.hindsight_insight,
            classification_confidence="RETROSPECTIVE",
        )


def _parse_time_to_months(time_str: str) -> int:
    """Convert time elapsed string to months."""
    parts = time_str.lower().split()
    if len(parts) >= 2:
        try:
            num = int(parts[0])
            if "year" in parts[1]:
                return num * 12
            elif "month" in parts[1]:
                return num
        except ValueError:
            pass
    return 24  # default: 2 years
