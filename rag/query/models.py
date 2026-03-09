"""
Echoes Phase 3 -- Query Understanding Models

Data models for query analysis and search construction.
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class QueryAnalysis(BaseModel):
    """Structured analysis of a user's decision query.

    Produced by the LLM-based query analyzer.
    """

    decision_type: str = "other"
    decision_subcategory: str = ""
    core_tension: str = ""
    emotional_state: List[str] = Field(default_factory=list)
    stakes: str = "moderate"  # low / moderate / high / life-altering
    key_factors: List[str] = Field(default_factory=list)
    what_would_help: str = ""


class RetrievalQuery(BaseModel):
    """Everything needed to search Qdrant for relevant stories.

    Built from the query analysis + user's values vector.
    """

    # Embeddings
    primary_embedding: List[float] = Field(default_factory=list)
    focused_embedding: List[float] = Field(default_factory=list)

    # Filters
    decision_type: str = "other"
    metadata_filters: dict = Field(default_factory=dict)

    # Personality-based boost rules
    boost_themes: List[str] = Field(default_factory=list)
    penalize_themes: List[str] = Field(default_factory=list)
    preferred_time_range: Optional[tuple] = None  # (min_months, max_months)
    prefer_clear_outcomes: bool = False
    include_mixed_outcomes: bool = True
    min_emotional_richness: int = 0

    # Counter-narrative
    counter_narrative_themes: List[str] = Field(default_factory=list)
    counter_narrative_quota: float = 0.25  # minimum fraction of results
