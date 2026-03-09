"""
Echoes Phase 3 -- Retrieval Models

Data models for story candidates and retrieval results.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class StoryCandidate(BaseModel):
    """A story retrieved from Qdrant, before re-ranking."""

    point_id: str
    text: str = ""
    semantic_score: float = 0.0

    # Metadata from Qdrant payload
    source: str = ""
    subreddit: str = ""
    decision_type: str = "other"
    decision_subcategory: str = ""
    outcome_sentiment: str = "neutral"
    time_elapsed_months: int = -1
    emotional_richness: int = 5
    outcome_clarity: bool = False
    key_themes: List[str] = Field(default_factory=list)
    hindsight_insight: str = ""

    # Which search pass found this
    search_pass: str = "primary"  # "primary" or "focused"

    @classmethod
    def from_qdrant_result(cls, result: dict, search_pass: str = "primary") -> "StoryCandidate":
        """Build from a QdrantStore.search() result dict."""
        payload = result.get("payload", {})
        return cls(
            point_id=str(result["id"]),
            text=payload.get("text", ""),
            semantic_score=result.get("score", 0.0),
            source=payload.get("source", ""),
            subreddit=payload.get("subreddit", ""),
            decision_type=payload.get("decision_type", "other"),
            decision_subcategory=payload.get("decision_subcategory", ""),
            outcome_sentiment=payload.get("outcome_sentiment", "neutral"),
            time_elapsed_months=payload.get("time_elapsed_months", -1),
            emotional_richness=payload.get("emotional_richness", 5),
            outcome_clarity=payload.get("outcome_clarity", False),
            key_themes=payload.get("key_themes", []),
            hindsight_insight=payload.get("hindsight_insight", ""),
            search_pass=search_pass,
        )


class RetrievalResult(BaseModel):
    """The output of the retrieval phase."""

    candidates: List[StoryCandidate] = Field(default_factory=list)
    primary_count: int = 0
    focused_count: int = 0
    deduplicated_count: int = 0
