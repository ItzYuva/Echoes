"""
Echoes Phase 3 -- Ranking Models

Data models for scored and ranked stories.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class ScoredStory(BaseModel):
    """A story candidate with a composite score from the re-ranker."""

    point_id: str
    text: str = ""
    composite_score: float = 0.0

    # Individual signal scores
    semantic_relevance: float = 0.0
    personality_alignment: float = 0.0
    temporal_depth: float = 0.0
    emotional_richness_score: float = 0.0
    outcome_clarity_score: float = 0.0
    counter_narrative_bonus: float = 0.0

    # Metadata
    decision_type: str = "other"
    decision_subcategory: str = ""
    outcome_sentiment: str = "neutral"
    time_elapsed_months: int = -1
    emotional_richness: int = 5
    outcome_clarity: bool = False
    key_themes: List[str] = Field(default_factory=list)
    hindsight_insight: str = ""
    source: str = ""
    subreddit: str = ""

    # Flags
    is_counter_narrative: bool = False
    relevance_note: str = ""  # For the presenter: why this story was chosen


class RankingResult(BaseModel):
    """Output of the re-ranking phase."""

    stories: List[ScoredStory] = Field(default_factory=list)
    total_candidates: int = 0
    counter_narrative_count: int = 0
    counter_narrative_ratio: float = 0.0
