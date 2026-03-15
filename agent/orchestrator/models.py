"""
Echoes Phase 4 -- Agent Data Models

Pydantic models for live stories, agent results, and tool responses.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class LiveStory(BaseModel):
    """A story fetched via live search, validated and tagged."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    text: str
    source: str = "reddit_live"  # reddit_live, web_storycorps, web_themoth, etc.
    source_url: str = ""

    # Metadata (same schema as Qdrant payload)
    decision_type: str = "other"
    decision_subcategory: str = ""
    outcome_sentiment: str = "neutral"
    time_elapsed_months: int = -1
    emotional_richness: int = 5
    outcome_clarity: bool = False
    key_themes: List[str] = Field(default_factory=list)
    hindsight_insight: str = ""

    # Live search metadata
    retrieval_method: str = "mcp_live_search"
    validated: bool = True
    validation_confidence: float = 0.0
    relevance_note: str = ""

    fetched_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    def to_qdrant_payload(self) -> Dict[str, Any]:
        """Convert to a payload dict matching the Qdrant schema."""
        return {
            "text": self.text,
            "source": self.source,
            "source_url": self.source_url,
            "decision_type": self.decision_type,
            "decision_subcategory": self.decision_subcategory,
            "outcome_sentiment": self.outcome_sentiment,
            "time_elapsed_months": self.time_elapsed_months,
            "emotional_richness": self.emotional_richness,
            "outcome_clarity": self.outcome_clarity,
            "key_themes": self.key_themes,
            "hindsight_insight": self.hindsight_insight,
            "retrieval_method": self.retrieval_method,
            "validated": self.validated,
            "validation_confidence": self.validation_confidence,
        }


class ValidationResult(BaseModel):
    """Result of story validation."""

    is_retrospective: bool = False
    confidence: float = 0.0
    rejection_reason: Optional[str] = None  # failed_heuristic, not_retrospective, low_quality
    metadata: Optional[Dict[str, Any]] = None


class ToolCallRecord(BaseModel):
    """Record of a single tool call made by the agent."""

    tool_name: str
    arguments: Dict[str, Any] = Field(default_factory=dict)
    candidates_found: int = 0
    validated_count: int = 0
    rejected_count: int = 0
    latency_ms: int = 0
    error: Optional[str] = None


class AgentResult(BaseModel):
    """Complete result from an agent search run."""

    stories: List[LiveStory] = Field(default_factory=list)
    tool_calls: List[ToolCallRecord] = Field(default_factory=list)
    tool_calls_made: int = 0
    sources_searched: List[str] = Field(default_factory=list)
    total_candidates_found: int = 0
    validated_count: int = 0
    rejected_count: int = 0

    # Performance
    total_latency_ms: int = 0
    search_latency_ms: int = 0
    validation_latency_ms: int = 0
    tokens_used: int = 0

    # Confidence impact
    confidence_before: float = 0.0
    confidence_after: Optional[float] = None

    @property
    def confidence_improvement(self) -> Optional[float]:
        if self.confidence_after is not None:
            return self.confidence_after - self.confidence_before
        return None

    @property
    def stories_count(self) -> int:
        return len(self.stories)
