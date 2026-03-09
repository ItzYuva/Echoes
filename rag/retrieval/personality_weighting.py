"""
Echoes Phase 3 -- Personality Weighting (Component 2)

Maps a user's 8-dimensional values vector into retrieval behavior:
theme boosts, time range preferences, outcome filters, and
counter-narrative themes.

DESIGN PRINCIPLE: The personality weighting NEVER creates an echo chamber.
At least 25% of stories challenge the user's dominant profile traits.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Set, Tuple

from config.logging_config import get_logger
from personality.models.values_vector import DIMENSION_NAMES, ValuesVector
from rag.query.models import RetrievalQuery, QueryAnalysis

logger = get_logger(__name__)

# Threshold for "high" and "low" on each dimension
HIGH_THRESHOLD = 0.65
LOW_THRESHOLD = 0.35

# ── Theme mappings per dimension ──────────────────────────────────────────

DIMENSION_THEMES: Dict[str, Dict[str, Dict]] = {
    "risk_tolerance": {
        "high": {
            "boost": ["leap of faith", "risk", "unknown", "bet on myself", "gamble"],
            "counter": ["caution", "patience", "stability", "played it safe"],
        },
        "low": {
            "boost": ["caution", "patience", "stability", "safe choice", "security"],
            "counter": ["risk", "leap of faith", "unknown", "just did it"],
        },
    },
    "change_orientation": {
        "high": {
            "boost": ["change", "new chapter", "reinvention", "pivot", "fresh start"],
            "counter": ["staying", "commitment", "persistence", "stuck with it"],
        },
        "low": {
            "boost": ["staying", "commitment", "persistence", "consistency"],
            "counter": ["change", "new chapter", "pivot", "fresh start"],
        },
    },
    "security_vs_growth": {
        "high": {
            "boost": ["growth", "expansion", "opportunity", "potential"],
            "counter": ["protection", "preservation", "stability", "safety net"],
        },
        "low": {
            "boost": ["protection", "preservation", "stability", "safety net"],
            "counter": ["growth", "expansion", "potential", "stretching"],
        },
    },
    "action_bias": {
        "high": {
            "boost": ["just did it", "leap", "action", "no regrets"],
            "counter": ["patience", "deliberation", "waited", "took time"],
        },
        "low": {
            "boost": ["patience", "deliberation", "waited and glad", "careful"],
            "counter": ["just did it", "leap", "action", "spontaneous"],
        },
    },
    "social_weight": {
        "high": {
            "boost": ["family", "relationship impact", "what others thought", "community"],
            "counter": ["independence", "self-trust", "going against advice"],
        },
        "low": {
            "boost": ["independence", "self-trust", "going against advice", "solo"],
            "counter": ["family", "relationship impact", "community", "support"],
        },
    },
    "time_horizon": {
        "high": {
            "boost": ["long-term", "future", "investment", "years later"],
            "counter": ["present", "immediate", "short-term", "right now"],
        },
        "low": {
            "boost": ["present", "immediate", "right now", "today"],
            "counter": ["long-term", "future", "investment", "years later"],
        },
    },
    "loss_sensitivity": {
        "high": {
            "boost": ["fear", "loss", "what I almost lost", "survived"],
            "counter": ["gain", "growth", "excitement", "opportunity"],
        },
        "low": {
            "boost": ["gain", "growth", "possibility", "excitement"],
            "counter": ["fear", "loss", "risk", "survived the worst"],
        },
    },
    "ambiguity_tolerance": {
        "high": {
            "boost": ["uncertainty", "grey area", "complex", "both sides"],
            "counter": ["clarity", "obvious", "clear answer"],
        },
        "low": {
            "boost": ["clarity", "clear outcome", "definitive", "obvious"],
            "counter": ["uncertainty", "grey area", "complex", "messy"],
        },
    },
}


def get_dominant_dimensions(
    values: ValuesVector, top_n: int = 3
) -> List[Tuple[str, float, str]]:
    """Find the user's most extreme dimensions.

    Returns:
        List of (dimension_name, value, direction) sorted by extremity.
        direction is "high" or "low".
    """
    extremes = []
    for dim_name in DIMENSION_NAMES:
        val = getattr(values, dim_name)
        distance_from_center = abs(val - 0.5)
        direction = "high" if val >= 0.5 else "low"
        extremes.append((dim_name, val, direction, distance_from_center))

    extremes.sort(key=lambda x: x[3], reverse=True)
    return [(name, val, direction) for name, val, direction, _ in extremes[:top_n]]


def build_boost_themes(values: ValuesVector) -> Set[str]:
    """Get all theme keywords that should be boosted for this user."""
    themes: Set[str] = set()
    for dim_name in DIMENSION_NAMES:
        val = getattr(values, dim_name)
        if val >= HIGH_THRESHOLD:
            themes.update(DIMENSION_THEMES[dim_name]["high"]["boost"])
        elif val <= LOW_THRESHOLD:
            themes.update(DIMENSION_THEMES[dim_name]["low"]["boost"])
    return themes


def build_counter_themes(values: ValuesVector) -> Set[str]:
    """Get themes that challenge the user's dominant profile.

    These are the 'opposite' themes for the user's most extreme dimensions.
    """
    themes: Set[str] = set()
    dominants = get_dominant_dimensions(values, top_n=3)
    for dim_name, _val, direction in dominants:
        themes.update(DIMENSION_THEMES[dim_name][direction]["counter"])
    return themes


def get_preferred_time_range(values: ValuesVector) -> Optional[Tuple[int, int]]:
    """Determine preferred story time horizon based on time_horizon dimension."""
    if values.time_horizon >= HIGH_THRESHOLD:
        return (36, 999)  # 3+ years of hindsight
    elif values.time_horizon <= LOW_THRESHOLD:
        return (6, 36)  # 6 months to 3 years
    return None  # no preference


def build_retrieval_query(
    query_analysis: QueryAnalysis,
    values_vector: ValuesVector,
    primary_embedding: List[float],
    focused_embedding: Optional[List[float]] = None,
) -> RetrievalQuery:
    """Construct a full retrieval query from analysis + personality.

    This is the main entry point for personality-weighted retrieval.

    Args:
        query_analysis: LLM analysis of the user's decision.
        values_vector: The user's 8-dimensional values profile.
        primary_embedding: Embedding of the user's raw text.
        focused_embedding: Embedding of 'what_would_help' (optional).

    Returns:
        RetrievalQuery ready to be sent to the hybrid retriever.
    """
    boost_themes = build_boost_themes(values_vector)
    counter_themes = build_counter_themes(values_vector)
    time_range = get_preferred_time_range(values_vector)

    return RetrievalQuery(
        primary_embedding=primary_embedding,
        focused_embedding=focused_embedding or [],
        decision_type=query_analysis.decision_type,
        boost_themes=list(boost_themes),
        penalize_themes=[],  # not actively penalizing — just not boosting
        counter_narrative_themes=list(counter_themes),
        preferred_time_range=time_range,
        prefer_clear_outcomes=values_vector.ambiguity_tolerance < LOW_THRESHOLD,
        include_mixed_outcomes=values_vector.ambiguity_tolerance >= 0.5,
        min_emotional_richness=6 if values_vector.ambiguity_tolerance >= HIGH_THRESHOLD else 0,
        counter_narrative_quota=0.25,
    )
