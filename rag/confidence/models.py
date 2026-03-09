"""
Echoes Phase 3 -- Confidence Models

Data models for retrieval quality assessment.
"""

from __future__ import annotations

from typing import List

from pydantic import BaseModel, Field


class RetrievalConfidence(BaseModel):
    """Assessment of retrieval quality for a query."""

    score: float = 0.0  # 0.0 - 1.0
    level: str = "insufficient"  # high / medium / low / insufficient
    reasons: List[str] = Field(default_factory=list)

    @property
    def should_present(self) -> bool:
        """Whether to show results at all."""
        return self.level != "insufficient"

    @property
    def needs_disclaimer(self) -> bool:
        """Whether to add a quality disclaimer."""
        return self.level in ("medium", "low", "insufficient")
