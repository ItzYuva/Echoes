#!/usr/bin/env python
"""
Echoes Phase 3 -- Query Log Inspector

Browse logged queries and confidence scores. Useful for diagnosing
retrieval quality and identifying data gaps.

Usage:
    # Show recent queries
    python scripts/inspect_queries.py

    # Filter by confidence level
    python scripts/inspect_queries.py --level low

    # Show gap analysis summary
    python scripts/inspect_queries.py --gaps

    # Show last N queries
    python scripts/inspect_queries.py --limit 50
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Ensure project root is in path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.logging_config import get_logger, setup_logging
from config.settings import Settings
from rag.storage.query_log_store import QueryLogStore

logger = get_logger(__name__)


LEVEL_EMOJI = {
    "high": "🟢",
    "medium": "🟡",
    "low": "🟠",
    "insufficient": "🔴",
}


async def show_recent(store: QueryLogStore, limit: int, level: str | None) -> None:
    """Display recent query logs."""
    queries = await store.get_recent_queries(limit=limit, confidence_level=level)

    if not queries:
        print("\n  No queries found.\n")
        return

    print(f"\n  Found {len(queries)} query log(s):\n")

    for q in queries:
        emoji = LEVEL_EMOJI.get(q["confidence_level"], "⚪")
        decision_type = q["query_analysis"].get("decision_type", "unknown")
        created = q["created_at"][:19].replace("T", " ")

        print(f"  {emoji} [{q['confidence_level']:>12}] {q['confidence_score']:.2f}  │  {decision_type:<14} │  {created}")
        print(f"     Query: {q['query_text'][:80]}{'...' if len(q['query_text']) > 80 else ''}")
        print(f"     Stories: {q['stories_presented']}/{q['candidates_found']} candidates  │  Latency: {q['total_latency_ms']}ms")

        if q["confidence_reasons"]:
            for reason in q["confidence_reasons"][:2]:
                print(f"     • {reason}")
        print()


async def show_gap_analysis(store: QueryLogStore) -> None:
    """Display data gap analysis from query logs."""
    analysis = await store.get_gap_analysis()

    if not analysis:
        print("\n  No query data available for gap analysis.\n")
        return

    # Confidence distribution
    print("\n╭───────────────────────────────────────────────╮")
    print("│ Confidence Distribution                        │")
    print("├───────────────────────────────────────────────┤")
    for entry in analysis.get("confidence_distribution", []):
        emoji = LEVEL_EMOJI.get(entry["level"], "⚪")
        bar = "█" * min(30, int(entry["count"] * 2))
        print(f"│  {emoji} {entry['level']:>12}: {entry['count']:>4} queries  (avg {entry['avg_score']:.2f})  {bar}")
    print("╰───────────────────────────────────────────────╯")

    # Decision type distribution
    print("\n╭───────────────────────────────────────────────╮")
    print("│ Decision Types Queried                         │")
    print("├───────────────────────────────────────────────┤")
    for entry in analysis.get("decision_type_distribution", []):
        print(f"│  {entry['decision_type']:>14}: {entry['count']:>4} queries  (avg confidence {entry['avg_confidence']:.2f})")
    print("╰───────────────────────────────────────────────╯")

    # Latency stats
    latency = analysis.get("latency", {})
    print("\n╭───────────────────────────────────────────────╮")
    print("│ Average Latency                                │")
    print("├───────────────────────────────────────────────┤")
    print(f"│  Total:        {latency.get('avg_total_ms', 0):>6}ms                      │")
    print(f"│  Embedding:    {latency.get('avg_embed_ms', 0):>6}ms                      │")
    print(f"│  Retrieval:    {latency.get('avg_retrieve_ms', 0):>6}ms                      │")
    print(f"│  Reranking:    {latency.get('avg_rerank_ms', 0):>6}ms                      │")
    print(f"│  Presentation: {latency.get('avg_present_ms', 0):>6}ms                      │")
    print(f"│  Total queries: {latency.get('total_queries', 0):>5}                        │")
    print("╰───────────────────────────────────────────────╯")

    # Data gaps
    gaps = analysis.get("data_gaps", [])
    if gaps:
        print("\n╭───────────────────────────────────────────────╮")
        print("│ Data Gaps (Low/Insufficient Queries)           │")
        print("├───────────────────────────────────────────────┤")
        for gap in gaps[:10]:
            emoji = LEVEL_EMOJI.get(gap["level"], "⚪")
            print(f"│  {emoji} [{gap['decision_type']}] {gap['query']}")
            for reason in gap.get("reasons", [])[:1]:
                print(f"│     • {reason}")
        print("╰───────────────────────────────────────────────╯")


async def run(args) -> None:
    settings = Settings()
    store = QueryLogStore(settings.postgres.dsn)

    try:
        await store.initialize()

        if args.gaps:
            await show_gap_analysis(store)
        else:
            await show_recent(store, limit=args.limit, level=args.level)
    except Exception as e:
        print(f"\n  Error connecting to PostgreSQL: {e}")
        print("  Make sure PostgreSQL is running and the query_logs table exists.\n")
    finally:
        await store.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Echoes Query Log Inspector")
    parser.add_argument(
        "--limit", type=int, default=20, help="Number of recent queries to show"
    )
    parser.add_argument(
        "--level",
        choices=["high", "medium", "low", "insufficient"],
        default=None,
        help="Filter by confidence level",
    )
    parser.add_argument(
        "--gaps", action="store_true", help="Show data gap analysis"
    )
    args = parser.parse_args()

    setup_logging()

    print("╭──────────────────────────────────────────────╮")
    print("│ 🔍 Echoes Phase 3 — Query Log Inspector       │")
    print("│ Browse queries, confidence, and data gaps      │")
    print("╰──────────────────────────────────────────────╯")

    asyncio.run(run(args))


if __name__ == "__main__":
    main()
