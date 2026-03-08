"""
Echoes Phase 2 -- PostgreSQL Profile Store

Async PostgreSQL operations for user profile CRUD.
Uses asyncpg for high-performance async access.
Falls back gracefully when PostgreSQL is not available (for local dev).
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from config.logging_config import get_logger

logger = get_logger(__name__)

# Migration file path
MIGRATION_DIR = Path(__file__).parent / "migrations"


class PostgresProfileStore:
    """Async PostgreSQL store for user profiles.

    Handles all profile CRUD operations, versioning, and queries.

    Args:
        dsn: PostgreSQL connection string.
    """

    def __init__(self, dsn: str):
        self.dsn = dsn
        self._pool = None

    async def initialize(self) -> None:
        """Connect to PostgreSQL and run migrations."""
        try:
            import asyncpg

            self._pool = await asyncpg.create_pool(self.dsn, min_size=2, max_size=10)
            await self._run_migrations()
            logger.info("PostgreSQL profile store initialized")
        except Exception as e:
            logger.error("Failed to initialize PostgreSQL: %s", e)
            raise

    async def close(self) -> None:
        """Close the connection pool."""
        if self._pool:
            await self._pool.close()
            logger.info("PostgreSQL connection pool closed")

    async def _run_migrations(self) -> None:
        """Run SQL migration files in order."""
        migration_file = MIGRATION_DIR / "001_create_profiles.sql"
        if not migration_file.exists():
            logger.warning("Migration file not found: %s", migration_file)
            return

        sql = migration_file.read_text(encoding="utf-8")
        async with self._pool.acquire() as conn:
            await conn.execute(sql)
        logger.info("Migrations applied successfully")

    # -- Profile CRUD ---------------------------------------------------------

    async def create_profile(
        self,
        values_vector: Dict[str, Any],
        intake_transcript: List[Dict[str, str]],
        intake_turns: int,
        intake_duration_seconds: int = 0,
    ) -> str:
        """Create a new user profile.

        Args:
            values_vector: Dict with 8 dimension values + confidence_notes.
            intake_transcript: List of conversation messages.
            intake_turns: Number of Q&A exchanges.
            intake_duration_seconds: How long the intake took.

        Returns:
            The generated user_id (UUID string).
        """
        user_id = str(uuid.uuid4())
        confidence_notes = values_vector.get("confidence_notes", {})

        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO user_profiles (
                    user_id, risk_tolerance, change_orientation, security_vs_growth,
                    action_bias, social_weight, time_horizon, loss_sensitivity,
                    ambiguity_tolerance, confidence_notes, intake_turns,
                    intake_duration_seconds, intake_transcript
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
                """,
                uuid.UUID(user_id),
                values_vector.get("risk_tolerance", 0.5),
                values_vector.get("change_orientation", 0.5),
                values_vector.get("security_vs_growth", 0.5),
                values_vector.get("action_bias", 0.5),
                values_vector.get("social_weight", 0.5),
                values_vector.get("time_horizon", 0.5),
                values_vector.get("loss_sensitivity", 0.5),
                values_vector.get("ambiguity_tolerance", 0.5),
                json.dumps(confidence_notes),
                intake_turns,
                intake_duration_seconds,
                json.dumps([msg for msg in intake_transcript]),
            )

            # Create initial version snapshot
            await conn.execute(
                """
                INSERT INTO profile_versions (user_id, version, values_snapshot, source)
                VALUES ($1, 1, $2, 'intake')
                """,
                uuid.UUID(user_id),
                json.dumps(values_vector),
            )

        logger.info("Profile created: %s (%d turns)", user_id, intake_turns)
        return user_id

    async def get_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a user profile by ID.

        Returns:
            Dict with profile data, or None if not found.
        """
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM user_profiles WHERE user_id = $1",
                uuid.UUID(user_id),
            )

        if row is None:
            return None

        return self._row_to_dict(row)

    async def update_profile(
        self,
        user_id: str,
        new_values: Dict[str, Any],
        source: str = "follow_up",
    ) -> bool:
        """Update a user's values vector.

        Creates a version snapshot of the old values before updating.

        Args:
            user_id: The user's ID.
            new_values: Dict with updated dimension values.
            source: What triggered the update.

        Returns:
            True if update succeeded, False if user not found.
        """
        async with self._pool.acquire() as conn:
            # Get current version
            current = await conn.fetchrow(
                "SELECT profile_version, risk_tolerance, change_orientation, "
                "security_vs_growth, action_bias, social_weight, time_horizon, "
                "loss_sensitivity, ambiguity_tolerance, confidence_notes "
                "FROM user_profiles WHERE user_id = $1",
                uuid.UUID(user_id),
            )

            if current is None:
                return False

            new_version = current["profile_version"] + 1

            # Snapshot current values
            old_snapshot = {
                "risk_tolerance": float(current["risk_tolerance"]),
                "change_orientation": float(current["change_orientation"]),
                "security_vs_growth": float(current["security_vs_growth"]),
                "action_bias": float(current["action_bias"]),
                "social_weight": float(current["social_weight"]),
                "time_horizon": float(current["time_horizon"]),
                "loss_sensitivity": float(current["loss_sensitivity"]),
                "ambiguity_tolerance": float(current["ambiguity_tolerance"]),
            }

            await conn.execute(
                """
                INSERT INTO profile_versions (user_id, version, values_snapshot, source)
                VALUES ($1, $2, $3, $4)
                """,
                uuid.UUID(user_id),
                current["profile_version"],
                json.dumps(old_snapshot),
                source,
            )

            # Update profile
            confidence = new_values.get("confidence_notes", {})
            await conn.execute(
                """
                UPDATE user_profiles SET
                    risk_tolerance = $2, change_orientation = $3,
                    security_vs_growth = $4, action_bias = $5,
                    social_weight = $6, time_horizon = $7,
                    loss_sensitivity = $8, ambiguity_tolerance = $9,
                    confidence_notes = $10, profile_version = $11,
                    updated_at = NOW()
                WHERE user_id = $1
                """,
                uuid.UUID(user_id),
                new_values.get("risk_tolerance", 0.5),
                new_values.get("change_orientation", 0.5),
                new_values.get("security_vs_growth", 0.5),
                new_values.get("action_bias", 0.5),
                new_values.get("social_weight", 0.5),
                new_values.get("time_horizon", 0.5),
                new_values.get("loss_sensitivity", 0.5),
                new_values.get("ambiguity_tolerance", 0.5),
                json.dumps(confidence),
                new_version,
            )

        logger.info("Profile %s updated to version %d", user_id, new_version)
        return True

    async def get_profile_history(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all historical versions of a profile.

        Returns:
            List of version snapshots ordered by version number.
        """
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM profile_versions
                WHERE user_id = $1
                ORDER BY version ASC
                """,
                uuid.UUID(user_id),
            )

        return [
            {
                "id": str(row["id"]),
                "user_id": str(row["user_id"]),
                "version": row["version"],
                "values_snapshot": json.loads(row["values_snapshot"]),
                "created_at": row["created_at"].isoformat(),
                "source": row["source"],
            }
            for row in rows
        ]

    async def find_similar_profiles(
        self, user_id: str, top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """Find profiles most similar to the given user.

        Uses SQL-based cosine similarity approximation across all 8 dimensions.

        Returns:
            List of profiles sorted by similarity (descending).
        """
        async with self._pool.acquire() as conn:
            # Get the target user's vector
            target = await conn.fetchrow(
                """
                SELECT risk_tolerance, change_orientation, security_vs_growth,
                       action_bias, social_weight, time_horizon,
                       loss_sensitivity, ambiguity_tolerance
                FROM user_profiles WHERE user_id = $1
                """,
                uuid.UUID(user_id),
            )

            if target is None:
                return []

            # SQL cosine similarity (dot product / (mag_a * mag_b))
            # This is a simplified version that works well for our use case
            rows = await conn.fetch(
                """
                SELECT user_id, risk_tolerance, change_orientation,
                       security_vs_growth, action_bias, social_weight,
                       time_horizon, loss_sensitivity, ambiguity_tolerance,
                       created_at,
                       (
                           risk_tolerance * $2 +
                           change_orientation * $3 +
                           security_vs_growth * $4 +
                           action_bias * $5 +
                           social_weight * $6 +
                           time_horizon * $7 +
                           loss_sensitivity * $8 +
                           ambiguity_tolerance * $9
                       ) / (
                           GREATEST(
                               SQRT(
                                   risk_tolerance^2 + change_orientation^2 +
                                   security_vs_growth^2 + action_bias^2 +
                                   social_weight^2 + time_horizon^2 +
                                   loss_sensitivity^2 + ambiguity_tolerance^2
                               ) *
                               SQRT(
                                   $2^2 + $3^2 + $4^2 + $5^2 +
                                   $6^2 + $7^2 + $8^2 + $9^2
                               ),
                               0.0001  -- avoid division by zero
                           )
                       ) AS similarity
                FROM user_profiles
                WHERE user_id != $1
                ORDER BY similarity DESC
                LIMIT $10
                """,
                uuid.UUID(user_id),
                float(target["risk_tolerance"]),
                float(target["change_orientation"]),
                float(target["security_vs_growth"]),
                float(target["action_bias"]),
                float(target["social_weight"]),
                float(target["time_horizon"]),
                float(target["loss_sensitivity"]),
                float(target["ambiguity_tolerance"]),
                top_k,
            )

        return [
            {
                "user_id": str(row["user_id"]),
                "similarity": float(row["similarity"]),
                "values": {
                    "risk_tolerance": float(row["risk_tolerance"]),
                    "change_orientation": float(row["change_orientation"]),
                    "security_vs_growth": float(row["security_vs_growth"]),
                    "action_bias": float(row["action_bias"]),
                    "social_weight": float(row["social_weight"]),
                    "time_horizon": float(row["time_horizon"]),
                    "loss_sensitivity": float(row["loss_sensitivity"]),
                    "ambiguity_tolerance": float(row["ambiguity_tolerance"]),
                },
            }
            for row in rows
        ]

    async def get_profile_count(self) -> int:
        """Get total number of profiles in the database."""
        async with self._pool.acquire() as conn:
            return await conn.fetchval("SELECT COUNT(*) FROM user_profiles")

    # -- Helpers --------------------------------------------------------------

    @staticmethod
    def _row_to_dict(row) -> Dict[str, Any]:
        """Convert an asyncpg Row to a dictionary."""
        return {
            "user_id": str(row["user_id"]),
            "created_at": row["created_at"].isoformat(),
            "updated_at": row["updated_at"].isoformat(),
            "values_vector": {
                "risk_tolerance": float(row["risk_tolerance"]),
                "change_orientation": float(row["change_orientation"]),
                "security_vs_growth": float(row["security_vs_growth"]),
                "action_bias": float(row["action_bias"]),
                "social_weight": float(row["social_weight"]),
                "time_horizon": float(row["time_horizon"]),
                "loss_sensitivity": float(row["loss_sensitivity"]),
                "ambiguity_tolerance": float(row["ambiguity_tolerance"]),
            },
            "confidence_notes": json.loads(row["confidence_notes"])
            if row["confidence_notes"]
            else {},
            "intake_version": row["intake_version"],
            "intake_turns": row["intake_turns"],
            "intake_duration_seconds": row["intake_duration_seconds"],
            "profile_version": row["profile_version"],
            "intake_transcript": json.loads(row["intake_transcript"])
            if row["intake_transcript"]
            else [],
        }
