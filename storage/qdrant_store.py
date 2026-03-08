"""
Echoes Data Pipeline — Qdrant Vector Store

Manages the Qdrant collection for storing and retrieving embedded stories.
Handles collection creation, upserting vectors with metadata payloads,
and search operations for Phase 2+.
"""

from __future__ import annotations

from typing import Optional

from qdrant_client import QdrantClient
from qdrant_client.http.exceptions import UnexpectedResponse
from qdrant_client.models import (
    Distance,
    PointStruct,
    VectorParams,
)

from config.logging_config import get_logger
from config.settings import QdrantSettings
from storage.models import StoryChunk

logger = get_logger(__name__)


class QdrantStore:
    """Interface to the Qdrant vector database for story embeddings.

    Handles collection creation, upserting story chunks with their
    metadata as searchable payloads, and basic retrieval.

    Args:
        settings: Qdrant connection settings.
        vector_size: Dimension of the embedding vectors (768 for Gemini text-embedding-004).
    """

    def __init__(
        self,
        settings: QdrantSettings,
        vector_size: int = 1536,
    ) -> None:
        self.settings = settings
        self.vector_size = vector_size
        self.client = QdrantClient(
            host=settings.host,
            port=settings.port,
            timeout=60,
        )
        self.collection_name = settings.collection_name

    def ensure_collection(self) -> None:
        """Create the stories collection if it doesn't already exist.

        Uses cosine distance and the configured vector size. Safe to call
        multiple times — idempotent.
        """
        try:
            info = self.client.get_collection(self.collection_name)
            logger.info(
                "Collection '%s' already exists (%d points)",
                self.collection_name,
                info.points_count,
            )
        except (UnexpectedResponse, Exception):
            distance_map = {
                "Cosine": Distance.COSINE,
                "Euclid": Distance.EUCLID,
                "Dot": Distance.DOT,
            }
            distance = distance_map.get(
                self.settings.distance_metric, Distance.COSINE
            )
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=self.vector_size,
                    distance=distance,
                ),
            )
            logger.info(
                "Created collection '%s' (size=%d, distance=%s)",
                self.collection_name,
                self.vector_size,
                self.settings.distance_metric,
            )

    def upsert_chunks(
        self,
        chunks: list[StoryChunk],
        embeddings: list[list[float]],
    ) -> int:
        """Upsert story chunks with their embedding vectors into Qdrant.

        Each chunk's metadata is stored as the point payload for filtered
        retrieval in later phases.

        Args:
            chunks: List of story chunks with metadata.
            embeddings: Corresponding embedding vectors (same order as chunks).

        Returns:
            Number of points upserted.

        Raises:
            ValueError: If chunks and embeddings lists have different lengths.
        """
        if len(chunks) != len(embeddings):
            raise ValueError(
                f"Mismatch: {len(chunks)} chunks vs {len(embeddings)} embeddings"
            )

        if not chunks:
            return 0

        points = []
        for chunk, embedding in zip(chunks, embeddings):
            payload = {
                "text": chunk.text,
                "source": chunk.source,
                "subreddit": chunk.subreddit,
                "author_hash": chunk.author_hash,
                "scraped_at": chunk.scraped_at.isoformat() if chunk.scraped_at else None,
                "original_score": chunk.original_score,
                "decision_type": chunk.decision_type,
                "decision_subcategory": chunk.decision_subcategory,
                "outcome_sentiment": chunk.outcome_sentiment,
                "time_elapsed_months": chunk.time_elapsed_months,
                "emotional_richness": chunk.emotional_richness,
                "outcome_clarity": chunk.outcome_clarity,
                "key_themes": chunk.key_themes,
                "hindsight_insight": chunk.hindsight_insight,
                "classification_confidence": chunk.classification_confidence,
                "chunk_index": chunk.chunk_index,
                "total_chunks": chunk.total_chunks,
                "parent_id": chunk.parent_id,
            }
            points.append(
                PointStruct(
                    id=chunk.chunk_id,
                    vector=embedding,
                    payload=payload,
                )
            )

        # Qdrant supports batch upsert
        self.client.upsert(
            collection_name=self.collection_name,
            points=points,
            wait=True,
        )
        logger.info("Upserted %d points into '%s'", len(points), self.collection_name)
        return len(points)

    def get_collection_info(self) -> dict:
        """Return basic info about the collection.

        Returns:
            Dict with point count and other collection metadata.
        """
        try:
            info = self.client.get_collection(self.collection_name)
            return {
                "collection": self.collection_name,
                "points_count": info.points_count,
                "vectors_count": info.vectors_count,
                "status": str(info.status),
            }
        except Exception as e:
            logger.warning("Could not fetch collection info: %s", e)
            return {"collection": self.collection_name, "error": str(e)}

    def search(
        self,
        query_vector: list[float],
        limit: int = 10,
        filters: Optional[dict] = None,
    ) -> list[dict]:
        """Search for similar stories by vector similarity.

        Args:
            query_vector: The query embedding vector.
            limit: Maximum number of results.
            filters: Optional Qdrant filter conditions.

        Returns:
            List of result dicts with id, score, and payload.
        """
        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            limit=limit,
            query_filter=filters,
        )
        return [
            {
                "id": str(r.id),
                "score": r.score,
                "payload": r.payload,
            }
            for r in results
        ]

    def count_points(self) -> int:
        """Return the total number of points in the collection."""
        try:
            info = self.client.get_collection(self.collection_name)
            return info.points_count or 0
        except Exception:
            return 0
