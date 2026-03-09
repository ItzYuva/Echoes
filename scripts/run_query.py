#!/usr/bin/env python
"""
Echoes Phase 3 -- Query Runner

Interactive script to test the full RAG pipeline.
Type a decision, see what Echoes surfaces.

Usage:
    # Interactive mode
    python scripts/run_query.py

    # Single query
    python scripts/run_query.py --query "Should I leave my corporate job to freelance?"

    # With custom personality
    python scripts/run_query.py --query "..." --risk 0.8 --action 0.7
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Ensure project root is in path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.logging_config import get_logger, setup_logging
from config.settings import Settings
from llm.gemini_client import GeminiClient
from personality.models.values_vector import DIMENSION_NAMES, ValuesVector
from processors.embedder import EmbeddingGenerator
from rag.pipeline.rag_pipeline import RAGPipeline
from storage.qdrant_store import QdrantStore

logger = get_logger(__name__)


def build_values_vector(args) -> ValuesVector:
    """Build a values vector from CLI args or defaults."""
    return ValuesVector(
        risk_tolerance=args.risk,
        change_orientation=args.change,
        security_vs_growth=args.growth,
        action_bias=args.action,
        social_weight=args.social,
        time_horizon=args.time,
        loss_sensitivity=args.loss,
        ambiguity_tolerance=args.ambiguity,
    )


async def run_query(
    pipeline: RAGPipeline,
    query_text: str,
    values: ValuesVector,
) -> None:
    """Execute a single query and display results."""
    print(f"\n🔍 Query: {query_text}")
    print(f"🧬 Personality: risk={values.risk_tolerance:.1f}, action={values.action_bias:.1f}, growth={values.security_vs_growth:.1f}")
    print("─" * 60)

    response = await pipeline.query(
        user_text=query_text,
        values_vector=values,
    )

    # Display analysis
    analysis = response.query_analysis
    print(f"\n📊 Analysis:")
    print(f"   Type: {analysis.decision_type} — {analysis.decision_subcategory}")
    print(f"   Tension: {analysis.core_tension}")
    print(f"   Stakes: {analysis.stakes}")
    print(f"   Emotions: {', '.join(analysis.emotional_state)}")

    # Display confidence
    conf = response.confidence
    level_emoji = {
        "high": "🟢",
        "medium": "🟡",
        "low": "🟠",
        "insufficient": "🔴",
    }
    print(f"\n📈 Confidence: {level_emoji.get(conf.level, '⚪')} {conf.level} ({conf.score:.2f})")
    for reason in conf.reasons:
        print(f"   • {reason}")

    # Display ranking stats
    ranking = response.ranking
    print(f"\n📚 Stories: {len(ranking.stories)} selected from {ranking.total_candidates} candidates")
    print(f"   Counter-narratives: {ranking.counter_narrative_count} ({ranking.counter_narrative_ratio:.0%})")

    # Display the presentation
    print("\n" + "═" * 60)
    print(response.presentation.text)
    print("═" * 60)

    # Display performance
    print(f"\n⏱️ Latency: {response.total_latency_ms}ms total")
    print(f"   Embed: {response.embedding_latency_ms}ms | Retrieve: {response.retrieval_latency_ms}ms | Rerank: {response.reranking_latency_ms}ms | Present: {response.presentation_latency_ms}ms")


async def interactive_mode(pipeline: RAGPipeline, values: ValuesVector) -> None:
    """Run queries interactively."""
    print("\n💬 Interactive mode. Type your decision or 'quit' to exit.\n")

    while True:
        try:
            query_text = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n👋 Goodbye!")
            break

        if not query_text or query_text.lower() in ("quit", "exit", "q"):
            print("👋 Goodbye!")
            break

        await run_query(pipeline, query_text, values)


def main() -> None:
    parser = argparse.ArgumentParser(description="Echoes RAG Query Runner")
    parser.add_argument("--query", type=str, help="Single query to run")

    # Personality sliders (all default to 0.5 = neutral)
    parser.add_argument("--risk", type=float, default=0.5, help="Risk tolerance (0-1)")
    parser.add_argument("--change", type=float, default=0.5, help="Change orientation (0-1)")
    parser.add_argument("--growth", type=float, default=0.5, help="Security vs growth (0-1)")
    parser.add_argument("--action", type=float, default=0.5, help="Action bias (0-1)")
    parser.add_argument("--social", type=float, default=0.5, help="Social weight (0-1)")
    parser.add_argument("--time", type=float, default=0.5, help="Time horizon (0-1)")
    parser.add_argument("--loss", type=float, default=0.5, help="Loss sensitivity (0-1)")
    parser.add_argument("--ambiguity", type=float, default=0.5, help="Ambiguity tolerance (0-1)")

    args = parser.parse_args()

    setup_logging()

    from config.settings import get_settings
    settings = get_settings()
    values = build_values_vector(args)

    # Initialize pipeline components
    llm_client = GeminiClient(settings.gemini)
    embedder = EmbeddingGenerator(settings.gemini)
    qdrant = QdrantStore(settings.qdrant, vector_size=3072)
    qdrant.ensure_collection()

    pipeline = RAGPipeline(
        settings=settings,
        llm_client=llm_client,
        qdrant=qdrant,
        embedder=embedder,
    )

    print("╭──────────────────────────────────────────────╮")
    print("│ 🔮 Echoes Phase 3 — RAG Query Runner          │")
    print("│ Ask about a life decision. See what echoes.    │")
    print("╰──────────────────────────────────────────────╯")

    if args.query:
        asyncio.run(run_query(pipeline, args.query, values))
    else:
        asyncio.run(interactive_mode(pipeline, values))


if __name__ == "__main__":
    main()
