"""
Echoes Phase 3 -- Counter-Narrative Detection (Component 3)

Detects whether a story challenges a user's dominant profile traits.
Enforces the 25% counter-narrative quota — the principle that
stories should broaden perspective, not create echo chambers.
"""

from __future__ import annotations

from typing import List, Set

from config.logging_config import get_logger
from personality.models.values_vector import DIMENSION_NAMES, ValuesVector
from rag.ranking.models import ScoredStory
from rag.retrieval.personality_weighting import (
    DIMENSION_THEMES,
    HIGH_THRESHOLD,
    LOW_THRESHOLD,
    get_dominant_dimensions,
)

logger = get_logger(__name__)


def is_counter_narrative(
    story_themes: List[str],
    outcome_sentiment: str,
    values_vector: ValuesVector,
) -> bool:
    """Check if a story challenges the user's dominant profile.

    A counter-narrative is a story whose themes align with the
    'counter' themes for the user's most extreme dimensions.
    """
    dominants = get_dominant_dimensions(values_vector, top_n=3)
    story_theme_set = set(t.lower() for t in story_themes)

    for dim_name, _val, direction in dominants:
        counter_themes = DIMENSION_THEMES.get(dim_name, {}).get(direction, {}).get("counter", [])
        for counter in counter_themes:
            for theme in story_theme_set:
                if counter.lower() in theme or theme in counter.lower():
                    return True

    # Also check sentiment-based counter-narratives
    if values_vector.loss_sensitivity >= HIGH_THRESHOLD:
        # Fear-dominant user — a positive outcome story challenges their fear
        if outcome_sentiment == "positive":
            return True
    elif values_vector.loss_sensitivity <= LOW_THRESHOLD:
        # Gain-excited user — a cautionary story provides balance
        if outcome_sentiment == "negative":
            return True

    return False


def enforce_counter_quota(
    stories: List[ScoredStory],
    values_vector: ValuesVector,
    min_ratio: float = 0.25,
    total_target: int = 8,
) -> List[ScoredStory]:
    """Enforce the counter-narrative quota in the final selection.

    If the top stories don't have enough counter-narratives,
    swap in the best counter-narrative candidates.

    Args:
        stories: Sorted list of scored stories (best first).
        values_vector: The user's values profile.
        min_ratio: Minimum fraction of counter-narratives.
        total_target: How many stories to return.

    Returns:
        Final story list with counter-narrative quota enforced.
    """
    if len(stories) <= 2:
        return stories

    target = min(total_target, len(stories))
    min_counter = max(1, int(target * min_ratio))

    selected = stories[:target]
    remaining = stories[target:]

    # Count existing counter-narratives
    counter_stories = [s for s in selected if s.is_counter_narrative]
    non_counter_stories = [s for s in selected if not s.is_counter_narrative]
    counter_candidates = [s for s in remaining if s.is_counter_narrative]

    needed = min_counter - len(counter_stories)

    if needed > 0 and counter_candidates and non_counter_stories:
        logger.info(
            "Counter-narrative quota: need %d more, have %d candidates",
            needed, len(counter_candidates),
        )
        # Replace the weakest non-counter stories with the best counter candidates
        replacements = min(needed, len(counter_candidates), len(non_counter_stories))
        for i in range(replacements):
            # Remove weakest non-counter (already sorted, so last is weakest)
            non_counter_stories.pop()
            # Add best counter candidate
            selected_counter = counter_candidates.pop(0)
            counter_stories.append(selected_counter)

        selected = counter_stories + non_counter_stories
        # Re-sort by composite score
        selected.sort(key=lambda s: s.composite_score, reverse=True)

    return selected


def interleave_by_sentiment(stories: List[ScoredStory]) -> List[ScoredStory]:
    """Interleave stories so sentiments don't cluster.

    Prevents sequences like [positive, positive, positive, negative, negative].
    Instead aims for [positive, mixed, negative, positive, mixed, ...].
    """
    if len(stories) <= 2:
        return stories

    # Group by sentiment
    positive = [s for s in stories if s.outcome_sentiment == "positive"]
    negative = [s for s in stories if s.outcome_sentiment == "negative"]
    mixed = [s for s in stories if s.outcome_sentiment in ("mixed", "neutral")]

    # Interleave: cycle through available pools
    result: List[ScoredStory] = []
    pools = [p for p in [positive, mixed, negative] if p]
    pool_idx = 0

    while pools:
        pool_idx = pool_idx % len(pools)
        result.append(pools[pool_idx].pop(0))
        if not pools[pool_idx]:
            pools.pop(pool_idx)
        else:
            pool_idx += 1

    return result
