"""
Echoes Phase 2 -- User Profile Model

The complete user profile including their values vector,
intake metadata, and versioning information.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from personality.models.values_vector import ValuesVector


class IntakeMessage(BaseModel):
    """A single message in the intake conversation."""

    role: str  # "assistant" or "user"
    content: str


class UserProfile(BaseModel):
    """Complete user personality profile.

    Created during the intake conversation and stored in PostgreSQL.
    The values_vector is the bridge between who the user is and
    what stories they see.
    """

    user_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Core values vector
    values_vector: ValuesVector

    # Intake metadata
    intake_version: int = 1
    intake_turns: int = 0
    intake_duration_seconds: int = 0

    # Profile evolution
    version: int = 1
    previous_versions: List[str] = []

    # The full intake transcript
    intake_transcript: List[IntakeMessage] = []


class ProfileVersion(BaseModel):
    """A historical snapshot of a user's values vector."""

    id: str
    user_id: str
    version: int
    values_snapshot: Dict[str, Any]
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source: str  # "intake", "follow_up", "manual_update"
