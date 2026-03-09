"""
Echoes Phase 3 -- Scoring Functions (Component 3)

Individual scoring functions used by the re-ranker. Each returns a
normalized 0.0-1.0 score for a specific signal dimension.
"""

from __future__ import annotations

from typing import List, Set

from personality.models.values_vector import DIMENSION_NAMES, ValuesVector
from rag.retrieval.personality_weighting import (
    HIGH_THRESHOLD,
    LOW_THRESHOLD,
    build_boost_themes,
)


def score_semantic_relevance(semantic_score: float) -> float:
    """Normalize semantic similarity score.

    The Qdrant cosine similarity is already in [0, 1] for cosine distance.
    """
    return max(0.0, min(1.0, semantic_score))


def score_personality_alignment(
    story_themes: List[str],
    outcome_sentiment: str,
    time_elapsed_months: int,
    values_vector: ValuesVector,
) -> float:
    """Score how well a story aligns with the user's values profile.

    Considers theme overlap, sentiment alignment, and time horizon.
    """
    score = 0.0
    signals = 0

    # Theme alignment
    boost_themes = build_boost_themes(values_vector)
    if boost_themes:
        story_theme_set = set(t.lower() for t in story_themes)
        # Check if any story theme contains or matches a boost theme
        overlap = 0
        for boost in boost_themes:
            for theme in story_theme_set:
                if boost.lower() in theme or theme in boost.lower():
                    overlap += 1
                    break
        theme_score = min(1.0, overlap / max(len(boost_themes), 1) * 3)
        score += theme_score
        signals += 1

    # Loss sensitivity → sentiment alignment
    if values_vector.loss_sensitivity >= HIGH_THRESHOLD:
        # Fear-dominant: stories showing fear is survivable
        if outcome_sentiment in ("positive", "mixed"):
            score += 0.8
            signals += 1
    elif values_vector.loss_sensitivity <= LOW_THRESHOLD:
        # Gain-excited: stories about what was gained
        if outcome_sentiment in ("positive",):
            score += 0.8
            signals += 1

    # Time horizon alignment
    if time_elapsed_months > 0:
        if values_vector.time_horizon >= HIGH_THRESHOLD and time_elapsed_months >= 60:
            score += 1.0
            signals += 1
        elif values_vector.time_horizon <= LOW_THRESHOLD and 6 <= time_elapsed_months <= 36:
            score += 1.0
            signals += 1
        elif 0.35 < values_vector.time_horizon < 0.65:
            # Balanced — any time range is fine
            score += 0.7
            signals += 1

    return score / max(signals, 1)


def score_temporal_depth(time_elapsed_months: int) -> float:
    """Score based on how much hindsight the story has.

    More hindsight = more valuable. Non-linear scaling.
    """
    if time_elapsed_months < 0:
        return 0.2  # Unknown time — still usable
    if time_elapsed_months >= 60:
        return 1.0  # 5+ years
    if time_elapsed_months >= 36:
        return 0.85  # 3-5 years
    if time_elapsed_months >= 12:
        return 0.6  # 1-3 years
    if time_elapsed_months >= 6:
        return 0.3  # 6-12 months
    return 0.1  # <6 months


def score_emotional_richness(richness: int) -> float:
    """Normalize emotional richness (1-10 scale) to 0.0-1.0."""
    return max(0.0, min(1.0, richness / 10.0))


def score_outcome_clarity(
    outcome_clarity: bool, ambiguity_tolerance: float
) -> float:
    """Score outcome clarity, adjusted by user's ambiguity tolerance.

    If the user is high ambiguity tolerance, don't penalize unclear outcomes.
    """
    if outcome_clarity:
        return 1.0
    if ambiguity_tolerance >= HIGH_THRESHOLD:
        return 0.7  # High ambiguity tolerance: unclear is fine
    return 0.0
