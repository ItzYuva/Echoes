"""
Echoes Phase 2 -- Intake Configuration

Settings specific to the intake conversation flow.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class IntakeConfig(BaseSettings):
    """Configuration for the intake conversation."""

    model_config = SettingsConfigDict(env_prefix="INTAKE_")

    # Conversation limits
    min_turns: int = 5
    max_turns: int = 8       # force-close if we hit this
    force_close_turn: int = 8  # append force-close after this many Q&A pairs

    # Retry settings for vector parsing
    max_parse_retries: int = 2

    # Default values for dimensions we couldn't parse
    default_dimension_value: float = 0.5
