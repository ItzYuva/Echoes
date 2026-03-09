"""
Echoes Phase 3 -- RAG Pipeline Orchestrator

The full RAG flow: query → understand → retrieve → rerank → confidence → present → log.
This is the main entry point that Phase 5's frontend will call.
"""

from __future__ import annotations

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


class RAGPipeline:
    """Orchestrates the full Echoes RAG flow.

    Connects query understanding → retrieval → re-ranking →
    confidence check → presentation → logging.

    Args:
        settings: Application settings.
        llm_client: Gemini client for query analysis and presentation.
        qdrant: Qdrant store for story retrieval.
        embedder: Embedding generator for query embedding.
    """

    def __init__(
        self,
        settings: Settings,
        llm_client,
        qdrant: QdrantStore,
        embedder: EmbeddingGenerator,
        query_log_store: Optional[QueryLogStore] = None,
    ) -> None:
        self.settings = settings
        self.analyzer = QueryAnalyzer(llm_client)
        self.query_embedder = QueryEmbedder(embedder)
        self.retriever = HybridRetriever(qdrant)
        self.reranker = Reranker()
        self.confidence_scorer = ConfidenceScorer()
        self.presenter = StoryPresenter(llm_client)
        self.query_log_store = query_log_store

    async def query(
        self,
        user_text: str,
        values_vector: ValuesVector,
        user_id: Optional[str] = None,
        max_stories: int = 10,
    ) -> EchoesResponse:
        """Execute the full RAG pipeline.

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
            "RAG complete in %dms (embed=%d, retrieve=%d, rerank=%d, present=%d)",
            total_latency,
            embedding_latency,
            retrieval_latency,
            reranking_latency,
            presentation_latency,
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
        )

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
