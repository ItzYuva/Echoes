"""
Echoes Phase 3 -- CSV Seeder (Component 0)

Reads stories from a CSV file and feeds them into the Phase 1 pipeline
for tagging, embedding, and storage in Qdrant.
"""

from __future__ import annotations

import csv
import hashlib
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from config.logging_config import get_logger
from config.settings import Settings
from llm.gemini_client import GeminiClient
from processors.embedder import EmbeddingGenerator
from storage.models import StoryChunk, StoryMetadata
from storage.qdrant_store import QdrantStore

logger = get_logger(__name__)


class CSVSeeder:
    """Seeds stories from a CSV file into Qdrant.

    CSV format: text,decision_type,source_note

    Each story goes through the Phase 1 pipeline:
    metadata extraction → embedding → Qdrant storage.

    Args:
        settings: Application settings.
    """

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.llm_client = GeminiClient(settings.gemini)
        self.embedder = EmbeddingGenerator(settings.gemini)
        self.qdrant = QdrantStore(settings.qdrant, vector_size=3072)

    async def seed_from_csv(self, csv_path: str | Path) -> dict:
        """Read a CSV file and seed stories into Qdrant.

        Args:
            csv_path: Path to the CSV file.

        Returns:
            Stats dict with processing counts.
        """
        csv_path = Path(csv_path)
        if not csv_path.exists():
            raise FileNotFoundError(f"CSV file not found: {csv_path}")

        stats = {
            "total_rows": 0,
            "tagged": 0,
            "embedded": 0,
            "stored": 0,
            "errors": 0,
        }

        self.qdrant.ensure_collection()

        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                stats["total_rows"] += 1
                try:
                    text = row.get("text", "").strip()
                    decision_type = row.get("decision_type", "other").strip()
                    source_note = row.get("source_note", "csv_seed").strip()

                    if not text or len(text) < 50:
                        logger.warning("Skipping short/empty row %d", stats["total_rows"])
                        continue

                    # Extract metadata
                    metadata = await self.llm_client.extract_metadata(text)
                    if metadata:
                        stats["tagged"] += 1
                    else:
                        metadata = StoryMetadata(decision_type=decision_type)

                    # Build chunk
                    content_hash = hashlib.sha256(text.encode()).hexdigest()
                    chunk = StoryChunk(
                        chunk_id=str(uuid.uuid4()),
                        parent_id=str(uuid.uuid4()),
                        text=text,
                        source=source_note,
                        subreddit="manual_seed",
                        author_hash=content_hash[:16],
                        scraped_at=datetime.now(timezone.utc),
                        decision_type=metadata.decision_type or decision_type,
                        decision_subcategory=metadata.decision_subcategory,
                        outcome_sentiment=metadata.outcome_sentiment,
                        time_elapsed_months=metadata.time_elapsed_months,
                        emotional_richness=metadata.emotional_richness,
                        outcome_clarity=metadata.outcome_clarity,
                        key_themes=metadata.key_themes,
                        hindsight_insight=metadata.hindsight_insight,
                        classification_confidence="RETROSPECTIVE",
                    )

                    # Embed
                    embedding = self.embedder.embed_single(text)
                    if not embedding:
                        logger.warning("Embedding failed for row %d", stats["total_rows"])
                        stats["errors"] += 1
                        continue
                    stats["embedded"] += 1

                    # Store
                    self.qdrant.upsert_chunks([chunk], [embedding])
                    stats["stored"] += 1

                except Exception as e:
                    logger.error("Error on row %d: %s", stats["total_rows"], e)
                    stats["errors"] += 1

        return stats
