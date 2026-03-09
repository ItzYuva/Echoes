"""
Echoes Phase 3 -- Query Log Store

Async PostgreSQL storage for RAG query logs. Every query is logged
with its analysis, confidence score, stories shown, and latency metrics.
This data powers gap analysis and system diagnostics.
"""

from __future__ import annotations

import json
import uuid
from typing import Any, Dict, List, Optional

from config.logging_config import get_logger
from personality.storage.postgres_store import MIGRATION_DIR

logger = get_logger(__name__)

QUERY_LOG_MIGRATION = MIGRATION_DIR / "002_create_query_logs.sql"


class QueryLogStore:
    """Async PostgreSQL store for RAG query logs.

    Logs every user query with confidence scores, stories shown,
    and latency breakdown for diagnostics and gap analysis.

    Args:
        dsn: PostgreSQL connection string.
    """

    def __init__(self, dsn: str) -> None:
        self.dsn = dsn
        self._pool = None

    async def initialize(self) -> None:
        """Connect to PostgreSQL and run query_logs migration."""
        try:
            import asyncpg

            self._pool = await asyncpg.create_pool(self.dsn, min_size=1, max_size=5)
            await self._run_migration()
            logger.info("Query log store initialized")
        except Exception as e:
            logger.error("Failed to initialize query log store: %s", e)
            raise

    async def close(self) -> None:
        """Close the connection pool."""
        if self._pool:
            await self._pool.close()

    async def _run_migration(self) -> None:
        """Run the query_logs migration."""
        if not QUERY_LOG_MIGRATION.exists():
            logger.warning("Migration file not found: %s", QUERY_LOG_MIGRATION)
            return

        sql = QUERY_LOG_MIGRATION.read_text(encoding="utf-8")
        async with self._pool.acquire() as conn:
            await conn.execute(sql)
        logger.info("Query log migration applied")

    async def log_query(
        self,
        user_id: Optional[str],
        query_text: str,
        query_analysis: dict,
        candidates_found: int,
        stories_presented: int,
        story_ids: List[str],
        confidence_score: float,
        confidence_level: str,
        confidence_reasons: List[str],
        total_latency_ms: int = 0,
        embedding_latency_ms: int = 0,
        retrieval_latency_ms: int = 0,
        reranking_latency_ms: int = 0,
        presentation_latency_ms: int = 0,
        tokens_input: int = 0,
        tokens_output: int = 0,
    ) -> Optional[str]:
        """Log a query and its results to PostgreSQL.

        Args:
            user_id: Optional user UUID string.
            query_text: The user's decision description.
            query_analysis: Structured analysis as dict.
            candidates_found: Number of retrieval candidates.
            stories_presented: Number of stories shown.
            story_ids: List of Qdrant point IDs shown.
            confidence_score: 0.0-1.0 confidence score.
            confidence_level: high/medium/low/insufficient.
            confidence_reasons: List of reason strings.
            total_latency_ms: Total pipeline latency.
            embedding_latency_ms: Embedding step latency.
            retrieval_latency_ms: Retrieval step latency.
            reranking_latency_ms: Reranking step latency.
            presentation_latency_ms: Presentation step latency.
            tokens_input: Input tokens used.
            tokens_output: Output tokens used.

        Returns:
            The generated log ID (UUID string), or None on failure.
        """
        if not self._pool:
            logger.warning("Query log store not initialized — skipping log")
            return None

        try:
            log_id = str(uuid.uuid4())
            async with self._pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO query_logs (
                        id, user_id, query_text, query_analysis,
                        candidates_found, stories_presented, story_ids,
                        confidence_score, confidence_level, confidence_reasons,
                        total_latency_ms, embedding_latency_ms,
                        retrieval_latency_ms, reranking_latency_ms,
                        presentation_latency_ms, tokens_input, tokens_output
                    ) VALUES (
                        $1, $2, $3, $4, $5, $6, $7, $8, $9, $10,
                        $11, $12, $13, $14, $15, $16, $17
                    )
                    """,
                    uuid.UUID(log_id),
                    uuid.UUID(user_id) if user_id else None,
                    query_text,
                    json.dumps(query_analysis),
                    candidates_found,
                    stories_presented,
                    json.dumps(story_ids),
                    confidence_score,
                    confidence_level,
                    json.dumps(confidence_reasons),
                    total_latency_ms,
                    embedding_latency_ms,
                    retrieval_latency_ms,
                    reranking_latency_ms,
                    presentation_latency_ms,
                    tokens_input,
                    tokens_output,
                )

            logger.info(
                "Query logged: %s (confidence=%s, stories=%d)",
                log_id[:8], confidence_level, stories_presented,
            )
            return log_id

        except Exception as e:
            logger.error("Failed to log query: %s", e)
            return None

    async def get_recent_queries(
        self, limit: int = 20, confidence_level: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Retrieve recent query logs.

        Args:
            limit: Maximum number of results.
            confidence_level: Optional filter by confidence level.

        Returns:
            List of query log dicts, most recent first.
        """
        if not self._pool:
            return []

        async with self._pool.acquire() as conn:
            if confidence_level:
                rows = await conn.fetch(
                    """
                    SELECT * FROM query_logs
                    WHERE confidence_level = $1
                    ORDER BY created_at DESC
                    LIMIT $2
                    """,
                    confidence_level,
                    limit,
                )
            else:
                rows = await conn.fetch(
                    """
                    SELECT * FROM query_logs
                    ORDER BY created_at DESC
                    LIMIT $1
                    """,
                    limit,
                )

        return [self._row_to_dict(row) for row in rows]

    async def get_gap_analysis(self) -> Dict[str, Any]:
        """Analyze query logs for data gaps.

        Returns stats on confidence levels, most-queried decision types,
        and queries that couldn't be served well.

        Returns:
            Dict with gap analysis stats.
        """
        if not self._pool:
            return {}

        async with self._pool.acquire() as conn:
            # Confidence distribution
            confidence_dist = await conn.fetch(
                """
                SELECT confidence_level, COUNT(*) as count,
                       AVG(confidence_score) as avg_score
                FROM query_logs
                GROUP BY confidence_level
                ORDER BY count DESC
                """
            )

            # Decision type distribution
            type_dist = await conn.fetch(
                """
                SELECT query_analysis->>'decision_type' as decision_type,
                       COUNT(*) as count,
                       AVG(confidence_score) as avg_confidence
                FROM query_logs
                GROUP BY query_analysis->>'decision_type'
                ORDER BY count DESC
                """
            )

            # Latency stats
            latency_stats = await conn.fetchrow(
                """
                SELECT
                    AVG(total_latency_ms) as avg_total,
                    AVG(embedding_latency_ms) as avg_embed,
                    AVG(retrieval_latency_ms) as avg_retrieve,
                    AVG(reranking_latency_ms) as avg_rerank,
                    AVG(presentation_latency_ms) as avg_present,
                    COUNT(*) as total_queries
                FROM query_logs
                """
            )

            # Low confidence queries (data gaps)
            gap_queries = await conn.fetch(
                """
                SELECT query_text, confidence_score, confidence_level,
                       confidence_reasons, query_analysis->>'decision_type' as decision_type,
                       created_at
                FROM query_logs
                WHERE confidence_level IN ('low', 'insufficient')
                ORDER BY created_at DESC
                LIMIT 20
                """
            )

        return {
            "confidence_distribution": [
                {
                    "level": row["confidence_level"],
                    "count": row["count"],
                    "avg_score": round(float(row["avg_score"]), 3),
                }
                for row in confidence_dist
            ],
            "decision_type_distribution": [
                {
                    "decision_type": row["decision_type"],
                    "count": row["count"],
                    "avg_confidence": round(float(row["avg_confidence"]), 3),
                }
                for row in type_dist
            ],
            "latency": {
                "avg_total_ms": round(float(latency_stats["avg_total"] or 0)),
                "avg_embed_ms": round(float(latency_stats["avg_embed"] or 0)),
                "avg_retrieve_ms": round(float(latency_stats["avg_retrieve"] or 0)),
                "avg_rerank_ms": round(float(latency_stats["avg_rerank"] or 0)),
                "avg_present_ms": round(float(latency_stats["avg_present"] or 0)),
                "total_queries": latency_stats["total_queries"],
            },
            "data_gaps": [
                {
                    "query": row["query_text"][:100],
                    "decision_type": row["decision_type"],
                    "confidence": round(float(row["confidence_score"]), 3),
                    "level": row["confidence_level"],
                    "reasons": json.loads(row["confidence_reasons"]) if row["confidence_reasons"] else [],
                    "created_at": row["created_at"].isoformat(),
                }
                for row in gap_queries
            ],
        }

    @staticmethod
    def _row_to_dict(row) -> Dict[str, Any]:
        """Convert an asyncpg Row to a dictionary."""
        return {
            "id": str(row["id"]),
            "user_id": str(row["user_id"]) if row["user_id"] else None,
            "created_at": row["created_at"].isoformat(),
            "query_text": row["query_text"],
            "query_analysis": json.loads(row["query_analysis"]) if row["query_analysis"] else {},
            "candidates_found": row["candidates_found"],
            "stories_presented": row["stories_presented"],
            "story_ids": json.loads(row["story_ids"]) if row["story_ids"] else [],
            "confidence_score": float(row["confidence_score"]),
            "confidence_level": row["confidence_level"],
            "confidence_reasons": json.loads(row["confidence_reasons"]) if row["confidence_reasons"] else [],
            "total_latency_ms": row["total_latency_ms"],
            "embedding_latency_ms": row["embedding_latency_ms"],
            "retrieval_latency_ms": row["retrieval_latency_ms"],
            "reranking_latency_ms": row["reranking_latency_ms"],
            "presentation_latency_ms": row["presentation_latency_ms"],
            "tokens_input": row["tokens_input"],
            "tokens_output": row["tokens_output"],
        }
