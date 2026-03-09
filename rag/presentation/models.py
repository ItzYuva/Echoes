"""
Echoes Phase 3 -- Presentation Models

Data models for the final story presentation.
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class PresentationResult(BaseModel):
    """The full output of the presentation phase."""

    text: str = ""
    story_ids: List[str] = Field(default_factory=list)
    stories_presented: int = 0
    tokens_input: int = 0
    tokens_output: int = 0
    latency_ms: int = 0
