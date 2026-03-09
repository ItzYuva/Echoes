"""
Echoes Data Pipeline — Database Inspector

Utility to browse what's in the SQLite staging database and Qdrant.
Useful for debugging and verifying pipeline output.

Usage:
    python scripts/inspect_db.py                     # summary overview
    python scripts/inspect_db.py --status tagged      # show items by status
    python scripts/inspect_db.py --item <uuid>        # show a specific item
    python scripts/inspect_db.py --qdrant             # show Qdrant collection info
    python scripts/inspect_db.py --sample 5           # show N sample stories
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.syntax import Syntax

from config.logging_config import setup_logging
from config.settings import get_settings
from storage.models import PipelineStatus
from storage.sqlite_store import SQLiteStore

console = Console()


def show_summary(store: SQLiteStore) -> None:
    """Print a summary of the database contents."""
    total = store.get_total_count()
    status_counts = store.count_by_status()

    table = Table(
        title=f"Database Summary ({total} total items)",
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("Status", style="cyan")
    table.add_column("Count", justify="right", style="green")
    table.add_column("Percentage", justify="right", style="yellow")

    for status, count in sorted(status_counts.items()):
        pct = f"{count / total * 100:.1f}%" if total > 0 else "0%"
        table.add_row(status, str(count), pct)

    console.print(table)


def show_items_by_status(store: SQLiteStore, status: str, limit: int = 20) -> None:
    """Show items with a specific pipeline status."""
    try:
        pipeline_status = PipelineStatus(status)
    except ValueError:
        console.print(f"[red]Invalid status: {status}[/]")
        console.print(f"Valid values: {[s.value for s in PipelineStatus]}")
        return

    items = store.get_items_by_status(pipeline_status, limit=limit)
    if not items:
        console.print(f"No items with status '{status}'")
        return

    console.print(f"\n[bold]Items with status '{status}' (showing {len(items)}):[/]")

    for item in items:
        text_preview = item["text"][:200].replace("\n", " ")
        panel_content = (
            f"[cyan]ID:[/] {item['id']}\n"
            f"[cyan]Subreddit:[/] r/{item['subreddit']}\n"
            f"[cyan]Type:[/] {item['content_type']}\n"
            f"[cyan]Score:[/] {item['score']}\n"
            f"[cyan]Created:[/] {item['created_utc']}\n"
        )
        if item.get("title"):
            panel_content += f"[cyan]Title:[/] {item['title']}\n"
        if item.get("heuristic_score"):
            panel_content += f"[cyan]Heuristic score:[/] {item['heuristic_score']:.2f}\n"
        if item.get("classification"):
            panel_content += f"[cyan]Classification:[/] {item['classification']}\n"
        if item.get("decision_type"):
            panel_content += f"[cyan]Decision type:[/] {item['decision_type']}\n"
        if item.get("key_themes"):
            panel_content += f"[cyan]Themes:[/] {item['key_themes']}\n"
        if item.get("hindsight_insight"):
            panel_content += f"[cyan]Insight:[/] {item['hindsight_insight']}\n"

        panel_content += f"\n[dim]{text_preview}...[/]"

        console.print(Panel(panel_content, title=f"[Story] {item['id'][:8]}...", border_style="blue"))


def show_item(store: SQLiteStore, item_id: str) -> None:
    """Show full details of a specific item."""
    item = store.get_item_by_id(item_id)
    if not item:
        console.print(f"[red]Item not found: {item_id}[/]")
        return

    console.print(Panel(
        json.dumps(dict(item), indent=2, default=str),
        title=f"Item: {item_id}",
        border_style="green",
    ))


def show_qdrant(settings) -> None:
    """Show Qdrant collection info."""
    try:
        from storage.qdrant_store import QdrantStore
        qdrant = QdrantStore(settings.qdrant, 3072)  # gemini-embedding-001 dimensions
        info = qdrant.get_collection_info()
        console.print(Panel(
            json.dumps(info, indent=2),
            title="Qdrant Collection Info",
            border_style="magenta",
        ))
    except Exception as e:
        console.print(f"[red]Could not connect to Qdrant: {e}[/]")
        console.print("[yellow]Is Qdrant running? Try: docker compose up -d[/]")


def show_samples(store: SQLiteStore, n: int = 5) -> None:
    """Show sample tagged stories with full metadata."""
    items = store.get_items_by_status(PipelineStatus.TAGGED, limit=n)
    if not items:
        items = store.get_items_by_status(PipelineStatus.INDEXED, limit=n)
    if not items:
        console.print("No tagged/indexed stories found")
        return

    console.print(f"\n[bold magenta]Sample Stories ({len(items)}):[/]")

    for item in items:
        text = item["text"]
        if len(text) > 500:
            text = text[:500] + "..."

        themes = item.get("key_themes", "[]")
        if isinstance(themes, str):
            try:
                themes = json.loads(themes)
            except json.JSONDecodeError:
                themes = []

        console.print(Panel(
            f"[bold]{item.get('title', 'Untitled')}[/]\n"
            f"[dim]r/{item['subreddit']} | Score: {item['score']} | {item['content_type']}[/]\n\n"
            f"{text}\n\n"
            f"[cyan]Decision:[/] {item.get('decision_type', '?')} → {item.get('decision_subcategory', '?')}\n"
            f"[cyan]Sentiment:[/] {item.get('outcome_sentiment', '?')}\n"
            f"[cyan]Time elapsed:[/] {item.get('time_elapsed_months', '?')} months\n"
            f"[cyan]Emotional richness:[/] {item.get('emotional_richness', '?')}/10\n"
            f"[cyan]Themes:[/] {', '.join(themes) if themes else '?'}\n"
            f"[cyan]Insight:[/] {item.get('hindsight_insight', '?')}\n",
            title="[Story]",
            border_style="green",
        ))


def main() -> None:
    """Run the database inspector CLI."""
    parser = argparse.ArgumentParser(
        description="Echoes — Database Inspector",
    )
    parser.add_argument(
        "--status",
        type=str,
        help="Show items with this pipeline status",
    )
    parser.add_argument(
        "--item",
        type=str,
        help="Show full details for a specific item UUID",
    )
    parser.add_argument(
        "--qdrant",
        action="store_true",
        help="Show Qdrant collection info",
    )
    parser.add_argument(
        "--sample",
        type=int,
        nargs="?",
        const=5,
        help="Show N sample tagged stories (default: 5)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Max items to show per query (default: 20)",
    )
    args = parser.parse_args()

    setup_logging()
    settings = get_settings()
    store = SQLiteStore(settings.pipeline.staging_db_path)

    if args.item:
        show_item(store, args.item)
    elif args.status:
        show_items_by_status(store, args.status, limit=args.limit)
    elif args.qdrant:
        show_qdrant(settings)
    elif args.sample is not None:
        show_samples(store, n=args.sample)
    else:
        show_summary(store)


if __name__ == "__main__":
    main()
