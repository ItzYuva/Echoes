"""
Echoes Phase 4 -- Agent Log Store

Async PostgreSQL storage for agent activity logs. Every agent invocation
is logged with its trigger context, tool calls, results, and performance
metrics. Powers cost monitoring and agent effectiveness analysis.
"""

from __future__ import annotations

import json
import uuid
from typing import Any, Dict, List, Optional

from agent.orchestrator.models import AgentResult
from config.logging_config import get_logger

logger = get_logger(__name__)


class AgentLogStore:
    """Async PostgreSQL store for agent activity logs.

    Logs every agent invocation with confidence context, tool call
    details, story counts, and latency breakdown.

    Args:
        dsn: PostgreSQL connection string.
    """

    def __init__(self, dsn: str) -> None:
        self.dsn = dsn
        self._pool = None

    async def initialize(self) -> None:
        """Connect to PostgreSQL and run agent_logs migration."""
        try:
            import asyncpg

            self._pool = await asyncpg.create_pool(self.dsn, min_size=1, max_size=3)
            await self._run_migration()
            logger.info("Agent log store initialized")
        except Exception as e:
            logger.error("Failed to initialize agent log store: %s", e)
            raise

    async def close(self) -> None:
        """Close the connection pool."""
        if self._pool:
            await self._pool.close()

    async def _run_migration(self) -> None:
        """Run the agent_logs migration."""
        from pathlib import Path

        migration_path = (
            Path(__file__).resolve().parent.parent.parent
            / "personality"
            / "storage"
            / "migrations"
            / "003_create_agent_logs.sql"
        )

        if not migration_path.exists():
            logger.warning("Agent log migration not found: %s", migration_path)
            return

        sql = migration_path.read_text(encoding="utf-8")
        async with self._pool.acquire() as conn:
            await conn.execute(sql)
        logger.info("Agent log migration applied")

    async def log_agent_run(
        self,
        query_log_id: Optional[str],
        agent_result: AgentResult,
    ) -> Optional[str]:
        """Log an agent run to PostgreSQL.

        Args:
            query_log_id: Optional ID of the query_logs row that triggered this.
            agent_result: Complete agent result with all metadata.

        Returns:
            The generated log ID or None on failure.
        """
        if not self._pool:
            logger.warning("Agent log store not initialized — skipping log")
            return None

        try:
            log_id = str(uuid.uuid4())

            tools_used = [tc.tool_name for tc in agent_result.tool_calls]
            tool_details = [tc.model_dump() for tc in agent_result.tool_calls]

            async with self._pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO agent_logs (
                        id, query_log_id,
                        trigger_confidence_level, trigger_confidence_score, trigger_reasons,
                        tool_calls_made, tools_used,
                        total_candidates_found, validated_count, rejected_count,
                        stories_returned, sources,
                        total_latency_ms, search_latency_ms, validation_latency_ms,
                        tokens_used,
                        confidence_before, confidence_after, confidence_improvement
                    ) VALUES (
                        $1, $2, $3, $4, $5, $6, $7, $8, $9, $10,
                        $11, $12, $13, $14, $15, $16, $17, $18, $19
                    )
                    """,
                    uuid.UUID(log_id),
                    uuid.UUID(query_log_id) if query_log_id else None,
                    "low",  # trigger level
                    agent_result.confidence_before,
                    json.dumps([]),
                    agent_result.tool_calls_made,
                    json.dumps(tools_used),
                    agent_result.total_candidates_found,
                    agent_result.validated_count,
                    agent_result.rejected_count,
                    agent_result.stories_count,
                    json.dumps(agent_result.sources_searched),
                    agent_result.total_latency_ms,
                    agent_result.search_latency_ms,
                    agent_result.validation_latency_ms,
                    agent_result.tokens_used,
                    agent_result.confidence_before,
                    agent_result.confidence_after,
                    agent_result.confidence_improvement,
                )

            logger.info(
                "Agent run logged: %s (stories=%d, latency=%dms)",
                log_id[:8], agent_result.stories_count, agent_result.total_latency_ms,
            )
            return log_id

        except Exception as e:
            logger.error("Failed to log agent run: %s", e)
            return None
