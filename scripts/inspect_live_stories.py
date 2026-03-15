"""
Echoes Phase 4 -- Live Stories Inspector

Browse live-fetched stories and their validation results.
Useful for debugging the agent's search and validation pipeline.

Usage:
    python scripts/inspect_live_stories.py --source reddit
    python scripts/inspect_live_stories.py --source web --query "career change"
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


async def inspect_reddit(query: str, max_results: int) -> None:
    """Search Reddit and show raw + validated results."""
    from agent.config.agent_config import AgentSettings, RedditLiveSettings
    from agent.tools.reddit_search import RedditSearchTool
    from agent.tools.story_validator import StoryValidator
    from classifiers.heuristic_filter import HeuristicFilter
    from config.settings import get_settings
    from llm.gemini_client import GeminiClient

    settings = get_settings()
    llm_client = GeminiClient(settings.gemini)
    heuristic = HeuristicFilter()
    agent_settings = AgentSettings()

    reddit = RedditSearchTool(agent_settings, RedditLiveSettings())
    validator = StoryValidator(heuristic, llm_client, agent_settings)

    console.print(f"\n[bold]Searching Reddit for:[/bold] {query}\n")

    raw_results = await reddit.search(query, max_results=max_results)
    console.print(f"[cyan]Raw results: {len(raw_results)}[/cyan]\n")

    # Show raw results summary
    raw_table = Table(title="Raw Reddit Results")
    raw_table.add_column("#", style="dim")
    raw_table.add_column("Subreddit")
    raw_table.add_column("Score", justify="right")
    raw_table.add_column("Length", justify="right")
    raw_table.add_column("Preview")

    for i, r in enumerate(raw_results, 1):
        raw_table.add_row(
            str(i),
            r.get("subreddit", ""),
            str(r.get("score", 0)),
            str(len(r.get("text", ""))),
            r.get("text", "")[:80] + "...",
        )

    console.print(raw_table)

    # Validate
    console.print("\n[yellow]Validating stories...[/yellow]\n")
    validated = await validator.validate_batch(raw_results)

    console.print(f"[green]Validated: {len(validated)}[/green]")
    console.print(f"[red]Rejected: {len(raw_results) - len(validated)}[/red]\n")

    for i, story in enumerate(validated, 1):
        console.print(
            Panel(
                f"{story.text[:300]}...\n\n"
                f"[dim]Type: {story.decision_type} | "
                f"Sentiment: {story.outcome_sentiment} | "
                f"Richness: {story.emotional_richness} | "
                f"Elapsed: {story.time_elapsed_months}mo\n"
                f"Themes: {', '.join(story.key_themes)}\n"
                f"Insight: {story.hindsight_insight}[/dim]",
                title=f"[{i}] {story.source}",
                border_style="green",
            )
        )


async def inspect_web(query: str, max_results: int) -> None:
    """Search web sources and show raw + validated results."""
    from agent.config.agent_config import AgentSettings
    from agent.tools.story_validator import StoryValidator
    from agent.tools.web_search import WebSearchTool
    from classifiers.heuristic_filter import HeuristicFilter
    from config.settings import get_settings
    from llm.gemini_client import GeminiClient

    settings = get_settings()
    llm_client = GeminiClient(settings.gemini)
    heuristic = HeuristicFilter()
    agent_settings = AgentSettings()

    web = WebSearchTool(agent_settings)
    validator = StoryValidator(heuristic, llm_client, agent_settings)

    console.print(f"\n[bold]Searching web for:[/bold] {query}\n")

    raw_results = await web.search(query, max_results=max_results)
    console.print(f"[cyan]Raw results: {len(raw_results)}[/cyan]\n")

    for i, r in enumerate(raw_results, 1):
        console.print(
            f"  [{i}] {r.get('source', '?')} — {r.get('source_url', 'N/A')}\n"
            f"      Length: {len(r.get('text', ''))} chars\n"
            f"      Preview: {r.get('text', '')[:100]}...\n"
        )

    if raw_results:
        console.print("[yellow]Validating stories...[/yellow]\n")
        validated = await validator.validate_batch(raw_results)

        console.print(f"[green]Validated: {len(validated)}[/green]")
        console.print(f"[red]Rejected: {len(raw_results) - len(validated)}[/red]\n")

        for i, story in enumerate(validated, 1):
            console.print(
                Panel(
                    f"{story.text[:300]}...\n\n"
                    f"[dim]Type: {story.decision_type} | "
                    f"Richness: {story.emotional_richness}[/dim]",
                    title=f"[{i}] {story.source}",
                    border_style="green",
                )
            )


def main():
    parser = argparse.ArgumentParser(description="Inspect live-fetched stories")
    parser.add_argument(
        "--source", "-s",
        choices=["reddit", "web", "both"],
        default="reddit",
        help="Source to inspect",
    )
    parser.add_argument(
        "--query", "-q",
        type=str,
        default="career change looking back years later",
        help="Search query",
    )
    parser.add_argument(
        "--max", "-m",
        type=int,
        default=10,
        help="Max results",
    )
    args = parser.parse_args()

    async def run():
        if args.source in ("reddit", "both"):
            await inspect_reddit(args.query, args.max)
        if args.source in ("web", "both"):
            await inspect_web(args.query, args.max)

    asyncio.run(run())


if __name__ == "__main__":
    main()
