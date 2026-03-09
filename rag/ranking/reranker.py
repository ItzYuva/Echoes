"""
Echoes Phase 3 -- Re-ranker (Component 3)

Takes ~80 candidate stories from retrieval and ranks them down to
the top 8-12 using a multi-signal composite scoring function.

Scoring weights are configurable — they're the primary tuning knob.
"""

from __future__ import annotations

from typing import List

from config.logging_config import get_logger
from personality.models.values_vector import ValuesVector
from rag.query.models import QueryAnalysis
from rag.ranking.counter_narrative import (
    enforce_counter_quota,
    interleave_by_sentiment,
    is_counter_narrative,
)
from rag.ranking.models import RankingResult, ScoredStory
from rag.ranking.scoring_functions import (
    score_emotional_richness,
    score_outcome_clarity,
    score_personality_alignment,
    score_semantic_relevance,
    score_temporal_depth,
)
from rag.retrieval.models import StoryCandidate

logger = get_logger(__name__)

# Default scoring weights — configurable as tuning knobs
DEFAULT_WEIGHTS = {
    "semantic_relevance": 0.30,
    "personality_alignment": 0.25,
    "temporal_depth": 0.15,
    "emotional_richness": 0.15,
    "outcome_clarity": 0.10,
    "counter_narrative_bonus": 0.05,
}

# Counter-narrative bonus value
COUNTER_NARRATIVE_BONUS_SCORE = 0.3


class Reranker:
    """Multi-signal story re-ranker.

    Scores each candidate story across 6 dimensions and selects
    the top 8-12 with counter-narrative quota enforcement.

    Args:
        weights: Optional custom scoring weights.
    """

    def __init__(self, weights: dict | None = None) -> None:
        self.weights = weights or DEFAULT_WEIGHTS.copy()

    def rerank(
        self,
        candidates: List[StoryCandidate],
        query_analysis: QueryAnalysis,
        values_vector: ValuesVector,
        max_stories: int = 10,
    ) -> RankingResult:
        """Re-rank candidates and select final stories.

        Args:
            candidates: Story candidates from retrieval.
            query_analysis: Structured query analysis.
            values_vector: User's personality profile.
            max_stories: Maximum stories to return (8-12 range).

        Returns:
            RankingResult with scored, ordered, and quota-enforced stories.
        """
        if not candidates:
            logger.warning("No candidates to rerank")
            return RankingResult()

        # Score each candidate
        scored: List[ScoredStory] = []
        for candidate in candidates:
            scored_story = self._score_candidate(
                candidate, query_analysis, values_vector
            )
            scored.append(scored_story)

        # Sort by composite score
        scored.sort(key=lambda s: s.composite_score, reverse=True)

        # Enforce counter-narrative quota
        selected = enforce_counter_quota(
            scored, values_vector,
            min_ratio=0.25,
            total_target=max_stories,
        )

        # Interleave by sentiment
        final = interleave_by_sentiment(selected)

        # Count counter-narratives
        cn_count = sum(1 for s in final if s.is_counter_narrative)

        logger.info(
            "Reranked %d candidates → %d stories (%d counter-narratives, %.0f%%)",
            len(candidates),
            len(final),
            cn_count,
            (cn_count / len(final) * 100) if final else 0,
        )

        return RankingResult(
            stories=final,
            total_candidates=len(candidates),
            counter_narrative_count=cn_count,
            counter_narrative_ratio=cn_count / len(final) if final else 0,
        )

    def _score_candidate(
        self,
        candidate: StoryCandidate,
        query_analysis: QueryAnalysis,
        values_vector: ValuesVector,
    ) -> ScoredStory:
        """Compute composite score for a single candidate."""
        w = self.weights

        # Individual scores
        sem = score_semantic_relevance(candidate.semantic_score)
        pers = score_personality_alignment(
            candidate.key_themes,
            candidate.outcome_sentiment,
            candidate.time_elapsed_months,
            values_vector,
        )
        temp = score_temporal_depth(candidate.time_elapsed_months)
        emo = score_emotional_richness(candidate.emotional_richness)
        clar = score_outcome_clarity(
            candidate.outcome_clarity, values_vector.ambiguity_tolerance
        )

        # Counter-narrative check
        cn = is_counter_narrative(
            candidate.key_themes, candidate.outcome_sentiment, values_vector
        )
        cn_bonus = COUNTER_NARRATIVE_BONUS_SCORE if cn else 0.0

        # Composite score
        composite = (
            w["semantic_relevance"] * sem
            + w["personality_alignment"] * pers
            + w["temporal_depth"] * temp
            + w["emotional_richness"] * emo
            + w["outcome_clarity"] * clar
            + w["counter_narrative_bonus"] * cn_bonus
        )

        # Build relevance note for the presenter
        notes = []
        if candidate.decision_type == query_analysis.decision_type:
            notes.append(f"Same decision type: {candidate.decision_type}")
        if cn:
            notes.append("Counter-narrative: broadens perspective")
        if temp >= 0.85:
            notes.append(f"Deep hindsight: {candidate.time_elapsed_months} months")

        return ScoredStory(
            point_id=candidate.point_id,
            text=candidate.text,
            composite_score=composite,
            semantic_relevance=sem,
            personality_alignment=pers,
            temporal_depth=temp,
            emotional_richness_score=emo,
            outcome_clarity_score=clar,
            counter_narrative_bonus=cn_bonus,
            decision_type=candidate.decision_type,
            decision_subcategory=candidate.decision_subcategory,
            outcome_sentiment=candidate.outcome_sentiment,
            time_elapsed_months=candidate.time_elapsed_months,
            emotional_richness=candidate.emotional_richness,
            outcome_clarity=candidate.outcome_clarity,
            key_themes=candidate.key_themes,
            hindsight_insight=candidate.hindsight_insight,
            source=candidate.source,
            subreddit=candidate.subreddit,
            is_counter_narrative=cn,
            relevance_note="; ".join(notes),
        )
