"""
Echoes Phase 3+4 -- RAG Pipeline Orchestrator

The full RAG flow: query → understand → retrieve → rerank → confidence →
[agent search if needed] → present → log.

Phase 4 integration: When confidence is low/insufficient, the agent
orchestrator searches for live stories and merges them into the results.
When confidence is medium, background enrichment runs silently.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from typing import Optional

from config.logging_config import get_logger
from config.settings import Settings
from personality.models.values_vector import ValuesVector
from processors.embedder import EmbeddingGenerator
from rag.confidence.confidence_scorer import ConfidenceScorer
from rag.confidence.models import RetrievalConfidence
from rag.presentation.models import PresentationResult
from rag.presentation.presenter import StoryPresenter
from rag.query.models import QueryAnalysis
from rag.query.query_analyzer import QueryAnalyzer
from rag.query.query_embedder import QueryEmbedder
from rag.ranking.models import RankingResult
from rag.ranking.reranker import Reranker
from rag.retrieval.hybrid_retriever import HybridRetriever
from rag.retrieval.personality_weighting import build_retrieval_query
from rag.storage.query_log_store import QueryLogStore
from storage.qdrant_store import QdrantStore

logger = get_logger(__name__)


class EchoesResponse:
    """The complete response from an Echoes query."""

    def __init__(
        self,
        presentation: PresentationResult,
        confidence: RetrievalConfidence,
        query_analysis: QueryAnalysis,
        ranking: RankingResult,
        total_latency_ms: int = 0,
        embedding_latency_ms: int = 0,
        retrieval_latency_ms: int = 0,
        reranking_latency_ms: int = 0,
        presentation_latency_ms: int = 0,
        live_search_used: bool = False,
        live_stories_count: int = 0,
        agent_searching: bool = False,
    ):
        self.presentation = presentation
        self.confidence = confidence
        self.query_analysis = query_analysis
        self.ranking = ranking
        self.total_latency_ms = total_latency_ms
        self.embedding_latency_ms = embedding_latency_ms
        self.retrieval_latency_ms = retrieval_latency_ms
        self.reranking_latency_ms = reranking_latency_ms
        self.presentation_latency_ms = presentation_latency_ms
        self.live_search_used = live_search_used
        self.live_stories_count = live_stories_count
        self.agent_searching = agent_searching


class RAGPipeline:
    """Orchestrates the full Echoes RAG flow.

    Connects query understanding → retrieval → re-ranking →
    confidence check → [Phase 4 agent] → presentation → logging.

    Args:
        settings: Application settings.
        llm_client: Gemini client for query analysis and presentation.
        qdrant: Qdrant store for story retrieval.
        embedder: Embedding generator for query embedding.
        query_log_store: Optional PostgreSQL query log store.
        agent_orchestrator: Optional Phase 4 agent for live search.
    """

    def __init__(
        self,
        settings: Settings,
        llm_client,
        qdrant: QdrantStore,
        embedder: EmbeddingGenerator,
        query_log_store: Optional[QueryLogStore] = None,
        agent_orchestrator=None,
    ) -> None:
        self.settings = settings
        self.llm_client = llm_client
        self.qdrant = qdrant
        self.embedder = embedder
        self.analyzer = QueryAnalyzer(llm_client)
        self.query_embedder = QueryEmbedder(embedder)
        self.retriever = HybridRetriever(qdrant)
        self.reranker = Reranker()
        self.confidence_scorer = ConfidenceScorer()
        self.presenter = StoryPresenter(llm_client)
        self.query_log_store = query_log_store
        self.agent = agent_orchestrator

    async def query(
        self,
        user_text: str,
        values_vector: ValuesVector,
        user_id: Optional[str] = None,
        max_stories: int = 10,
    ) -> EchoesResponse:
        """Execute the full RAG pipeline with Phase 4 integration.

        This is the main entry point. Everything Phase 5 needs to call.

        Args:
            user_text: The user's decision description.
            values_vector: The user's personality profile.
            user_id: Optional user ID for logging.
            max_stories: Maximum stories to present.

        Returns:
            EchoesResponse with presentation, confidence, and metadata.
        """
        pipeline_start = time.time()

        # ── Step 1: Query Understanding ──────────────────────────────────
        logger.info("Step 1: Analyzing query...")
        query_analysis = await self.analyzer.analyze(user_text)
        logger.info(
            "Query: type=%s, tension='%s', stakes=%s",
            query_analysis.decision_type,
            query_analysis.core_tension,
            query_analysis.stakes,
        )

        # ── Step 2: Embed query ─────────────────────────────────────────
        logger.info("Step 2: Embedding query...")
        embed_start = time.time()
        primary_emb, focused_emb = self.query_embedder.embed_dual(
            user_text, query_analysis.what_would_help
        )
        embedding_latency = int((time.time() - embed_start) * 1000)

        if not primary_emb:
            logger.error("Failed to embed query — cannot proceed")
            return self._empty_response(query_analysis, pipeline_start)

        # ── Step 3: Build retrieval query with personality weighting ─────
        logger.info("Step 3: Building personality-weighted retrieval query...")
        retrieval_query = build_retrieval_query(
            query_analysis=query_analysis,
            values_vector=values_vector,
            primary_embedding=primary_emb,
            focused_embedding=focused_emb,
        )

        # ── Step 4: Retrieve candidates ─────────────────────────────────
        logger.info("Step 4: Retrieving candidates from Qdrant...")
        retrieval_start = time.time()
        retrieval_result = self.retriever.retrieve(retrieval_query)
        retrieval_latency = int((time.time() - retrieval_start) * 1000)
        logger.info("Retrieved %d candidates", retrieval_result.deduplicated_count)

        # ── Step 5: Re-rank ─────────────────────────────────────────────
        logger.info("Step 5: Re-ranking candidates...")
        rerank_start = time.time()
        ranking = self.reranker.rerank(
            candidates=retrieval_result.candidates,
            query_analysis=query_analysis,
            values_vector=values_vector,
            max_stories=max_stories,
        )
        reranking_latency = int((time.time() - rerank_start) * 1000)

        # ── Step 6: Confidence check ────────────────────────────────────
        logger.info("Step 6: Assessing retrieval confidence...")
        confidence = self.confidence_scorer.score(ranking.stories, query_analysis)

        # ── Step 6b: Phase 4 — Agent search if needed ───────────────────
        live_search_used = False
        live_stories_count = 0
        agent_metadata = None

        if self.agent and self._agent_enabled():
            if confidence.level in ("low", "insufficient"):
                # BLOCKING: Wait for agent results before presenting
                logger.info(
                    "Step 6b: Confidence is %s (%.2f) — activating agent...",
                    confidence.level, confidence.score,
                )

                agent_result = await self.agent.search_for_stories(
                    decision_text=user_text,
                    query_analysis=query_analysis.model_dump(),
                    confidence=confidence,
                )
                agent_metadata = agent_result

                if agent_result.stories:
                    # Convert live stories to candidates and merge
                    from agent.integration.pipeline_hook import (
                        live_stories_to_candidates,
                        merge_candidates,
                    )

                    live_candidates = live_stories_to_candidates(agent_result.stories)
                    merged = merge_candidates(
                        retrieval_result.candidates, live_candidates
                    )

                    # Re-rank the combined set
                    ranking = self.reranker.rerank(
                        candidates=merged,
                        query_analysis=query_analysis,
                        values_vector=values_vector,
                        max_stories=max_stories,
                    )

                    # Recompute confidence with merged results
                    confidence = self.confidence_scorer.score(
                        ranking.stories, query_analysis
                    )
                    agent_result.confidence_after = confidence.score

                    live_search_used = True
                    live_stories_count = len(agent_result.stories)

                    logger.info(
                        "Agent added %d stories, confidence: %.2f → %.2f",
                        live_stories_count,
                        agent_result.confidence_before,
                        confidence.score,
                    )

            elif confidence.level == "medium":
                # NON-BLOCKING: Present immediately, search in background
                if self._background_enrichment_enabled():
                    logger.info(
                        "Step 6b: Confidence is medium — starting background enrichment"
                    )
                    asyncio.create_task(
                        self._background_enrichment(
                            user_text, query_analysis.model_dump()
                        )
                    )

        # ── Step 7: Present ─────────────────────────────────────────────
        logger.info("Step 7: Presenting stories (confidence=%s)...", confidence.level)
        presentation = await self.presenter.present(
            user_text=user_text,
            query_analysis=query_analysis,
            stories=ranking.stories,
        )
        presentation_latency = presentation.latency_ms

        total_latency = int((time.time() - pipeline_start) * 1000)

        logger.info(
            "RAG complete in %dms (embed=%d, retrieve=%d, rerank=%d, present=%d, live=%s)",
            total_latency,
            embedding_latency,
            retrieval_latency,
            reranking_latency,
            presentation_latency,
            live_search_used,
        )

        # ── Step 8: Log query to PostgreSQL ──────────────────────────────
        await self._log_query(
            user_id=user_id,
            user_text=user_text,
            query_analysis=query_analysis,
            ranking=ranking,
            confidence=confidence,
            presentation=presentation,
            total_latency_ms=total_latency,
            embedding_latency_ms=embedding_latency,
            retrieval_latency_ms=retrieval_latency,
            reranking_latency_ms=reranking_latency,
            presentation_latency_ms=presentation_latency,
        )

        return EchoesResponse(
            presentation=presentation,
            confidence=confidence,
            query_analysis=query_analysis,
            ranking=ranking,
            total_latency_ms=total_latency,
            embedding_latency_ms=embedding_latency,
            retrieval_latency_ms=retrieval_latency,
            reranking_latency_ms=reranking_latency,
            presentation_latency_ms=presentation_latency,
            live_search_used=live_search_used,
            live_stories_count=live_stories_count,
        )

    def _agent_enabled(self) -> bool:
        """Check if the Phase 4 agent is enabled."""
        import os
        return os.environ.get("AGENT_ENABLED", "true").lower() != "false"

    def _background_enrichment_enabled(self) -> bool:
        """Check if background enrichment is enabled."""
        import os
        return os.environ.get("AGENT_BACKGROUND_ENRICHMENT_ENABLED", "true").lower() != "false"

    async def _background_enrichment(
        self,
        decision_text: str,
        query_analysis: dict,
    ) -> None:
        """Run background enrichment asynchronously."""
        try:
            from agent.integration.background_enrichment import background_enrichment

            added = await background_enrichment(
                agent=self.agent,
                decision_text=decision_text,
                query_analysis=query_analysis,
                embedder=self.embedder,
                qdrant_store=self.qdrant,
            )
            logger.info("Background enrichment completed: %d stories added", added)
        except Exception as e:
            logger.error("Background enrichment failed: %s", e)

    async def _log_query(
        self,
        user_id: Optional[str],
        user_text: str,
        query_analysis: QueryAnalysis,
        ranking: RankingResult,
        confidence: RetrievalConfidence,
        presentation: PresentationResult,
        total_latency_ms: int,
        embedding_latency_ms: int,
        retrieval_latency_ms: int,
        reranking_latency_ms: int,
        presentation_latency_ms: int,
    ) -> None:
        """Log the query to PostgreSQL. Non-blocking — failures are logged but don't break the pipeline."""
        if not self.query_log_store:
            return

        try:
            await self.query_log_store.log_query(
                user_id=user_id,
                query_text=user_text,
                query_analysis=query_analysis.model_dump(),
                candidates_found=ranking.total_candidates,
                stories_presented=len(ranking.stories),
                story_ids=[s.point_id for s in ranking.stories],
                confidence_score=confidence.score,
                confidence_level=confidence.level,
                confidence_reasons=confidence.reasons,
                total_latency_ms=total_latency_ms,
                embedding_latency_ms=embedding_latency_ms,
                retrieval_latency_ms=retrieval_latency_ms,
                reranking_latency_ms=reranking_latency_ms,
                presentation_latency_ms=presentation_latency_ms,
                tokens_input=presentation.tokens_input,
                tokens_output=presentation.tokens_output,
            )
        except Exception as e:
            logger.error("Failed to log query to PostgreSQL: %s", e)

    @staticmethod
    def _empty_response(
        query_analysis: QueryAnalysis, start_time: float
    ) -> EchoesResponse:
        """Return an empty response when the pipeline can't proceed."""
        return EchoesResponse(
            presentation=PresentationResult(
                text="I'm having trouble processing your query right now. Please try again.",
            ),
            confidence=RetrievalConfidence(
                score=0.0, level="insufficient",
                reasons=["Pipeline error — could not embed query"],
            ),
            query_analysis=query_analysis,
            ranking=RankingResult(),
            total_latency_ms=int((time.time() - start_time) * 1000),
        )
