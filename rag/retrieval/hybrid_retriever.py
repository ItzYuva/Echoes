"""
Echoes Phase 3 -- Hybrid Retriever (Component 2)

Performs dual-pass Qdrant search:
1. Broad search with primary embedding + decision_type filter
2. Focused search with 'what_would_help' embedding

Merges and deduplicates results into a unified candidate pool.
"""

from __future__ import annotations

from typing import List, Optional

from config.logging_config import get_logger
from rag.query.models import RetrievalQuery
from rag.retrieval.models import RetrievalResult, StoryCandidate
from storage.qdrant_store import QdrantStore

logger = get_logger(__name__)


class HybridRetriever:
    """Dual-pass Qdrant retriever with personality-aware filtering.

    First pass: broad semantic search with decision_type filter.
    Second pass: focused search on 'what_would_help' embedding.
    Merges, deduplicates, and returns candidate pool.

    Args:
        qdrant: The Qdrant store instance.
    """

    def __init__(self, qdrant: QdrantStore) -> None:
        self.qdrant = qdrant

    def retrieve(
        self,
        query: RetrievalQuery,
        broad_limit: int = 50,
        focused_limit: int = 30,
    ) -> RetrievalResult:
        """Execute dual-pass retrieval.

        Args:
            query: The retrieval query with embeddings and filters.
            broad_limit: Max results from broad search.
            focused_limit: Max results from focused search.

        Returns:
            RetrievalResult with deduplicated candidates.
        """
        candidates: dict[str, StoryCandidate] = {}

        # Pass 1: Broad semantic search
        if query.primary_embedding:
            broad_filter = self._build_qdrant_filter(query, strict=False)
            broad_results = self.qdrant.search(
                query_vector=query.primary_embedding,
                limit=broad_limit,
                filters=broad_filter,
            )
            for result in broad_results:
                candidate = StoryCandidate.from_qdrant_result(result, "primary")
                if candidate.point_id not in candidates:
                    candidates[candidate.point_id] = candidate

            primary_count = len(broad_results)
            logger.info("Broad search returned %d results", primary_count)
        else:
            primary_count = 0
            logger.warning("No primary embedding — skipping broad search")

        # Pass 2: Focused search
        focused_count = 0
        if query.focused_embedding:
            focused_filter = self._build_qdrant_filter(query, strict=False)
            focused_results = self.qdrant.search(
                query_vector=query.focused_embedding,
                limit=focused_limit,
                filters=focused_filter,
            )
            for result in focused_results:
                candidate = StoryCandidate.from_qdrant_result(result, "focused")
                if candidate.point_id not in candidates:
                    candidates[candidate.point_id] = candidate
                else:
                    # If already found in broad search, keep the higher score
                    existing = candidates[candidate.point_id]
                    if candidate.semantic_score > existing.semantic_score:
                        candidates[candidate.point_id] = candidate

            focused_count = len(focused_results)
            logger.info("Focused search returned %d results", focused_count)

        all_candidates = list(candidates.values())
        logger.info(
            "Retrieval: %d broad + %d focused → %d unique candidates",
            primary_count,
            focused_count,
            len(all_candidates),
        )

        return RetrievalResult(
            candidates=all_candidates,
            primary_count=primary_count,
            focused_count=focused_count,
            deduplicated_count=len(all_candidates),
        )

    @staticmethod
    def _build_qdrant_filter(
        query: RetrievalQuery, strict: bool = False
    ) -> Optional[dict]:
        """Build Qdrant filter conditions from the retrieval query.

        Uses the qdrant_client filter API format.

        Args:
            query: The retrieval query with filter preferences.
            strict: If True, apply decision_type as must filter.

        Returns:
            Qdrant filter dict, or None if no filters needed.
        """
        from qdrant_client.models import (
            FieldCondition,
            Filter,
            MatchValue,
            Range,
        )

        must_conditions = []
        should_conditions = []

        # Decision type filter
        if query.decision_type and query.decision_type != "other":
            if strict:
                must_conditions.append(
                    FieldCondition(
                        key="decision_type",
                        match=MatchValue(value=query.decision_type),
                    )
                )
            else:
                should_conditions.append(
                    FieldCondition(
                        key="decision_type",
                        match=MatchValue(value=query.decision_type),
                    )
                )

        # Outcome clarity preference
        if query.prefer_clear_outcomes:
            should_conditions.append(
                FieldCondition(
                    key="outcome_clarity",
                    match=MatchValue(value=True),
                )
            )

        # Emotional richness minimum
        if query.min_emotional_richness > 0:
            should_conditions.append(
                FieldCondition(
                    key="emotional_richness",
                    range=Range(gte=query.min_emotional_richness),
                )
            )

        # Time range preference
        if query.preferred_time_range:
            min_months, max_months = query.preferred_time_range
            should_conditions.append(
                FieldCondition(
                    key="time_elapsed_months",
                    range=Range(gte=min_months, lte=max_months),
                )
            )

        if not must_conditions and not should_conditions:
            return None

        filter_kwargs = {}
        if must_conditions:
            filter_kwargs["must"] = must_conditions
        if should_conditions:
            filter_kwargs["should"] = should_conditions

        return Filter(**filter_kwargs)
