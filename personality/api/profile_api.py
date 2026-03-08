"""
Echoes Phase 2 -- Profile API

High-level profile operations that combine the storage layer
with business logic. This is the interface that Phase 3+ will use.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from config.logging_config import get_logger
from personality.models.user_profile import IntakeMessage, UserProfile
from personality.models.values_vector import ValuesVector
from personality.storage.postgres_store import PostgresProfileStore

logger = get_logger(__name__)


class ProfileAPI:
    """High-level API for user profile operations.

    Wraps the PostgreSQL store with business logic and model conversion.

    Args:
        store: The PostgreSQL profile store instance.
    """

    def __init__(self, store: PostgresProfileStore):
        self.store = store

    async def create_profile(
        self,
        values_vector: ValuesVector,
        intake_transcript: List[Dict[str, str]],
        intake_turns: int,
        intake_duration_seconds: int = 0,
    ) -> str:
        """Create a new user profile from an intake conversation.

        Args:
            values_vector: The parsed values vector.
            intake_transcript: List of conversation messages.
            intake_turns: Number of Q&A exchanges.
            intake_duration_seconds: Duration of the intake.

        Returns:
            The generated user_id.
        """
        values_dict = values_vector.to_dict()
        values_dict["confidence_notes"] = values_vector.confidence_notes

        user_id = await self.store.create_profile(
            values_vector=values_dict,
            intake_transcript=intake_transcript,
            intake_turns=intake_turns,
            intake_duration_seconds=intake_duration_seconds,
        )

        logger.info(
            "Profile created via API: %s (turns=%d, duration=%ds)",
            user_id,
            intake_turns,
            intake_duration_seconds,
        )
        return user_id

    async def get_profile(self, user_id: str) -> Optional[UserProfile]:
        """Retrieve a user profile as a Pydantic model.

        Returns:
            UserProfile or None if not found.
        """
        data = await self.store.get_profile(user_id)
        if data is None:
            return None

        return UserProfile(
            user_id=data["user_id"],
            created_at=data["created_at"],
            updated_at=data["updated_at"],
            values_vector=ValuesVector(**data["values_vector"]),
            intake_version=data["intake_version"],
            intake_turns=data["intake_turns"],
            intake_duration_seconds=data["intake_duration_seconds"],
            version=data["profile_version"],
            intake_transcript=[
                IntakeMessage(**msg) for msg in data.get("intake_transcript", [])
            ],
        )

    async def update_profile(
        self,
        user_id: str,
        new_vector: ValuesVector,
        source: str = "follow_up",
    ) -> bool:
        """Update a user's values vector.

        Preserves the old version in profile_versions.

        Returns:
            True if update succeeded.
        """
        values_dict = new_vector.to_dict()
        values_dict["confidence_notes"] = new_vector.confidence_notes
        return await self.store.update_profile(user_id, values_dict, source)

    async def get_profile_history(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all historical versions of a profile."""
        return await self.store.get_profile_history(user_id)

    async def compute_similarity(self, user_id_a: str, user_id_b: str) -> float:
        """Compute cosine similarity between two users' profiles.

        Returns:
            Float in [-1.0, 1.0]. 1.0 = identical.
        """
        profile_a = await self.get_profile(user_id_a)
        profile_b = await self.get_profile(user_id_b)

        if profile_a is None or profile_b is None:
            logger.warning("Cannot compute similarity: profile not found")
            return 0.0

        return profile_a.values_vector.similarity(profile_b.values_vector)

    async def find_similar_profiles(
        self, user_id: str, top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """Find users with the most similar values profiles."""
        return await self.store.find_similar_profiles(user_id, top_k)
