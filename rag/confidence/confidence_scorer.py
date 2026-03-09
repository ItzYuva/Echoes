"""
Echoes Phase 3 -- Confidence Scorer (Component 5)

Assesses retrieval quality to decide whether to present results,
add disclaimers, or acknowledge insufficient coverage.
"""

from __future__ import annotations

from typing import List

from config.logging_config import get_logger
from rag.confidence.models import RetrievalConfidence
from rag.query.models import QueryAnalysis
from rag.ranking.models import ScoredStory

logger = get_logger(__name__)

# Thresholds
HIGH_SEMANTIC_THRESHOLD = 0.65
MEDIUM_SEMANTIC_THRESHOLD = 0.50
MIN_STORIES_THRESHOLD = 4
INSUFFICIENT_SEMANTIC_THRESHOLD = 0.40


class ConfidenceScorer:
    """Assesses retrieval quality for a query.

    Determines whether results are good enough to present,
    need disclaimers, or should be flagged as insufficient.
    """

    def score(
        self,
        stories: List[ScoredStory],
        query_analysis: QueryAnalysis,
    ) -> RetrievalConfidence:
        """Compute retrieval confidence.

        Args:
            stories: The final ranked stories.
            query_analysis: The query analysis for context.

        Returns:
            RetrievalConfidence with score, level, and reasons.
        """
        if not stories:
            return RetrievalConfidence(
                score=0.0,
                level="insufficient",
                reasons=["No stories found for this query"],
            )

        reasons = []

        # Factor 1: Top story semantic score
        top_semantic = stories[0].semantic_relevance if stories else 0.0
        if top_semantic < INSUFFICIENT_SEMANTIC_THRESHOLD:
            reasons.append(f"Best story match is weak (score: {top_semantic:.2f})")

        # Factor 2: Mean semantic score of top 5
        top_5_semantics = [s.semantic_relevance for s in stories[:5]]
        mean_semantic = sum(top_5_semantics) / len(top_5_semantics)

        # Factor 3: Story count
        story_count = len(stories)
        if story_count < MIN_STORIES_THRESHOLD:
            reasons.append(f"Only {story_count} stories found (prefer {MIN_STORIES_THRESHOLD}+)")

        # Factor 4: Decision type match count
        type_matches = sum(
            1 for s in stories
            if s.decision_type == query_analysis.decision_type
        )
        if type_matches == 0:
            reasons.append("No stories match the exact decision type")

        # Factor 5: Mean emotional richness
        mean_richness = (
            sum(s.emotional_richness for s in stories) / len(stories)
        )

        # Factor 6: Mean temporal depth
        valid_times = [s.time_elapsed_months for s in stories if s.time_elapsed_months > 0]
        mean_temporal = sum(valid_times) / len(valid_times) if valid_times else 0

        # Compute composite confidence
        confidence = self._compute_score(
            top_semantic=top_semantic,
            mean_semantic=mean_semantic,
            story_count=story_count,
            type_matches=type_matches,
            mean_richness=mean_richness,
            mean_temporal=mean_temporal,
        )

        # Determine level
        if confidence >= 0.75:
            level = "high"
            reasons.append("Strong matches across multiple signals")
        elif confidence >= 0.55:
            level = "medium"
            if not reasons:
                reasons.append("Moderate match quality — stories relate but may not be exact parallels")
        elif confidence >= 0.40:
            level = "low"
            if not reasons:
                reasons.append("Limited relevant stories available")
        else:
            level = "insufficient"
            if not reasons:
                reasons.append("Not enough relevant stories for a meaningful response")

        logger.info(
            "Retrieval confidence: %.2f (%s) — %d stories, top=%.2f, mean=%.2f",
            confidence, level, story_count, top_semantic, mean_semantic,
        )

        return RetrievalConfidence(
            score=round(confidence, 3),
            level=level,
            reasons=reasons,
        )

    @staticmethod
    def _compute_score(
        top_semantic: float,
        mean_semantic: float,
        story_count: int,
        type_matches: int,
        mean_richness: float,
        mean_temporal: float,
    ) -> float:
        """Weighted combination of confidence factors."""
        # Normalize each factor to 0-1
        top_norm = min(1.0, top_semantic)
        mean_norm = min(1.0, mean_semantic)
        count_norm = min(1.0, story_count / 8.0)
        type_norm = min(1.0, type_matches / 4.0)
        richness_norm = min(1.0, mean_richness / 8.0)
        temporal_norm = min(1.0, mean_temporal / 60.0) if mean_temporal > 0 else 0.3

        return (
            0.30 * top_norm
            + 0.25 * mean_norm
            + 0.15 * count_norm
            + 0.15 * type_norm
            + 0.10 * richness_norm
            + 0.05 * temporal_norm
        )
