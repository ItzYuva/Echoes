"""
Echoes Phase 5 -- Python FastAPI Bridge

Thin HTTP wrapper around the existing Phase 1-4 Python pipeline.
No business logic here -- just HTTP ↔ Python pipeline translation.
Spring Boot calls these internal endpoints via WebClient.

Usage:
    uvicorn python_api.server:app --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import asyncio
import os
import sys
import uuid
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

# Ensure project root is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.logging_config import get_logger, setup_logging
from config.settings import Settings, get_settings
from llm.gemini_client import GeminiClient
from personality.api.profile_api import ProfileAPI
from personality.intake.conversation_manager import ConversationManager
from personality.models.values_vector import DIMENSION_NAMES, ValuesVector
from personality.storage.postgres_store import PostgresProfileStore
from processors.embedder import EmbeddingGenerator
from rag.pipeline.rag_pipeline import RAGPipeline
from rag.storage.query_log_store import QueryLogStore
from storage.qdrant_store import QdrantStore

logger = get_logger(__name__)

# ── Global state ─────────────────────────────────────────────────
# Initialized at startup, cleaned up at shutdown.

settings: Settings = None
llm_client: GeminiClient = None
profile_store: PostgresProfileStore = None
profile_api: ProfileAPI = None
rag_pipeline: RAGPipeline = None
intake_sessions: Dict[str, ConversationManager] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown lifecycle."""
    global settings, llm_client, profile_store, profile_api, rag_pipeline

    setup_logging()
    settings = get_settings()

    # LLM
    llm_client = GeminiClient(settings.gemini)

    # PostgreSQL
    profile_store = PostgresProfileStore(settings.postgres.dsn)
    await profile_store.initialize()
    profile_api = ProfileAPI(profile_store)

    # RAG pipeline
    embedder = EmbeddingGenerator(settings.gemini)
    qdrant = QdrantStore(settings.qdrant, vector_size=3072)
    qdrant.ensure_collection()

    query_log_store = QueryLogStore(settings.postgres.dsn)
    await query_log_store.initialize()

    # Optional agent
    agent = None
    if settings.agent.enabled:
        try:
            from agent.orchestrator.agent import AgentOrchestrator
            from agent.tools.reddit_search import RedditSearchTool
            from agent.tools.story_validator import StoryValidator
            from agent.tools.web_search import WebSearchTool

            reddit_search = RedditSearchTool(settings.reddit)
            web_search = WebSearchTool()
            validator = StoryValidator(llm_client)
            agent = AgentOrchestrator(
                llm_client=llm_client,
                reddit_search=reddit_search,
                web_search=web_search,
                validator=validator,
                agent_settings=settings.agent,
            )
            logger.info("Phase 4 agent enabled")
        except Exception as e:
            logger.warning("Could not initialize agent: %s", e)

    rag_pipeline = RAGPipeline(
        settings=settings,
        llm_client=llm_client,
        qdrant=qdrant,
        embedder=embedder,
        query_log_store=query_log_store,
        agent_orchestrator=agent,
    )

    logger.info("Python API ready")
    yield

    # Shutdown
    await profile_store.close()
    await query_log_store.close()
    logger.info("Python API shut down")


app = FastAPI(title="Echoes Python API (internal)", lifespan=lifespan)


# ── Request / Response models ────────────────────────────────────


class IntakeStartRequest(BaseModel):
    session_id: str


class IntakeRespondRequest(BaseModel):
    session_id: str
    message: str


class IntakeResponse(BaseModel):
    session_id: str
    message: str
    turn_number: int
    is_complete: bool
    values_vector: Optional[Dict[str, Any]] = None


class QueryRequest(BaseModel):
    user_id: Optional[str] = None
    decision_text: str
    values_vector: Dict[str, float]
    max_stories: int = 10


class ProfileCreateRequest(BaseModel):
    values_vector: Dict[str, Any]
    intake_transcript: List[Dict[str, str]]
    intake_turns: int
    intake_duration_seconds: int = 0


class ProfileUpdateRequest(BaseModel):
    new_values: Dict[str, Any]
    source: str = "manual_update"


# ── Intake endpoints ─────────────────────────────────────────────


@app.post("/internal/intake/start", response_model=IntakeResponse)
async def start_intake(req: IntakeStartRequest):
    """Start a new intake conversation session."""
    session_id = req.session_id
    manager = ConversationManager(llm_client=llm_client)
    opening = await manager.start()
    intake_sessions[session_id] = manager

    return IntakeResponse(
        session_id=session_id,
        message=opening,
        turn_number=0,
        is_complete=False,
    )


@app.post("/internal/intake/respond", response_model=IntakeResponse)
async def intake_respond(req: IntakeRespondRequest):
    """Process a user message in an intake conversation."""
    manager = intake_sessions.get(req.session_id)
    if manager is None:
        raise HTTPException(status_code=404, detail="Session not found")

    response_text, is_complete = await manager.respond(req.message)

    result = IntakeResponse(
        session_id=req.session_id,
        message=response_text,
        turn_number=manager.turn_count,
        is_complete=is_complete,
    )

    if is_complete and manager.values_vector:
        vv = manager.values_vector
        result.values_vector = vv.to_dict()
        result.values_vector["confidence_notes"] = vv.confidence_notes
        # Clean up session
        del intake_sessions[req.session_id]

    return result


# ── Query endpoint ────────────────────────────────────────────────


@app.post("/internal/query")
async def query(req: QueryRequest):
    """Run the full RAG pipeline."""
    vv = ValuesVector(**{k: v for k, v in req.values_vector.items() if k in DIMENSION_NAMES})

    response = await rag_pipeline.query(
        user_text=req.decision_text,
        values_vector=vv,
        user_id=req.user_id,
        max_stories=req.max_stories,
    )

    # Serialize the response
    stories = []
    for s in response.ranking.stories:
        stories.append({
            "id": s.point_id,
            "text": s.text,
            "decision_type": s.decision_type,
            "decision_subcategory": s.decision_subcategory,
            "outcome_sentiment": s.outcome_sentiment,
            "time_elapsed_months": s.time_elapsed_months,
            "emotional_richness": s.emotional_richness,
            "outcome_clarity": s.outcome_clarity,
            "key_themes": s.key_themes,
            "hindsight_insight": s.hindsight_insight,
            "is_counter_narrative": s.is_counter_narrative,
            "composite_score": s.composite_score,
        })

    return {
        "presentation": {
            "text": response.presentation.text,
            "stories_count": response.presentation.stories_presented,
        },
        "confidence": {
            "score": response.confidence.score,
            "level": response.confidence.level,
            "reasons": response.confidence.reasons,
        },
        "query_analysis": {
            "decision_type": response.query_analysis.decision_type,
            "decision_subcategory": response.query_analysis.decision_subcategory,
            "core_tension": response.query_analysis.core_tension,
            "emotional_state": response.query_analysis.emotional_state,
            "stakes": response.query_analysis.stakes,
            "key_factors": response.query_analysis.key_factors,
            "what_would_help": response.query_analysis.what_would_help,
        },
        "stories": stories,
        "metadata": {
            "total_latency_ms": response.total_latency_ms,
            "embedding_latency_ms": response.embedding_latency_ms,
            "retrieval_latency_ms": response.retrieval_latency_ms,
            "reranking_latency_ms": response.reranking_latency_ms,
            "presentation_latency_ms": response.presentation_latency_ms,
            "live_search_used": response.live_search_used,
            "live_stories_count": response.live_stories_count,
            "agent_searching": response.agent_searching,
            "candidates_found": response.ranking.total_candidates,
            "stories_presented": len(stories),
            "counter_narrative_ratio": response.ranking.counter_narrative_ratio,
        },
    }


# ── Profile endpoints ─────────────────────────────────────────────


@app.post("/internal/profile")
async def create_profile(req: ProfileCreateRequest):
    """Create a user profile."""
    user_id = await profile_store.create_profile(
        values_vector=req.values_vector,
        intake_transcript=req.intake_transcript,
        intake_turns=req.intake_turns,
        intake_duration_seconds=req.intake_duration_seconds,
    )
    return {"user_id": user_id}


@app.get("/internal/profile/{user_id}")
async def get_profile(user_id: str):
    """Get a user profile."""
    data = await profile_store.get_profile(user_id)
    if data is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    return data


@app.put("/internal/profile/{user_id}")
async def update_profile(user_id: str, req: ProfileUpdateRequest):
    """Update a user's values vector."""
    success = await profile_store.update_profile(
        user_id=user_id,
        new_values=req.new_values,
        source=req.source,
    )
    if not success:
        raise HTTPException(status_code=404, detail="Profile not found")
    return {"success": True}


@app.get("/internal/profile/{user_id}/history")
async def get_profile_history(user_id: str):
    """Get profile version history."""
    history = await profile_store.get_profile_history(user_id)
    return {"versions": history}


# ── Health ────────────────────────────────────────────────────────


@app.get("/internal/health")
async def health():
    """Health check."""
    return {"status": "ok", "service": "echoes-python-api"}
