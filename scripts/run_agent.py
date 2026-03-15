"""
Echoes Phase 4 -- Agent Test CLI

Test the agent directly with a decision query. Shows tool calls,
validated stories, and performance metrics.

Usage:
    python scripts/run_agent.py
    python scripts/run_agent.py --query "leaving my tenured position to become a park ranger"
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

console = Console()


async def run_agent_test(query: str) -> None:
    """Run the agent with a decision query and display results."""
    from agent.config.agent_config import AgentSettings, RedditLiveSettings
    from agent.orchestrator.agent import AgentOrchestrator
    from agent.tools.reddit_search import RedditSearchTool
    from agent.tools.story_validator import StoryValidator
    from agent.tools.web_search import WebSearchTool
    from classifiers.heuristic_filter import HeuristicFilter
    from config.settings import get_settings
    from llm.gemini_client import GeminiClient
    from rag.confidence.models import RetrievalConfidence

    settings = get_settings()
    console.print("\n[bold cyan]Echoes Agent — Phase 4 Test CLI[/bold cyan]\n")

    # Initialize components
    console.print("[dim]Initializing components...[/dim]")
    llm_client = GeminiClient(settings.gemini)
    heuristic = HeuristicFilter()
    agent_settings = AgentSettings()
    reddit_settings = RedditLiveSettings()

    reddit_search = RedditSearchTool(agent_settings, reddit_settings)
    web_search = WebSearchTool(agent_settings)
    validator = StoryValidator(heuristic, llm_client, agent_settings)

    agent = AgentOrchestrator(
        llm_client=llm_client,
        reddit_search=reddit_search,
        web_search=web_search,
        validator=validator,
        agent_settings=agent_settings,
    )

    # Analyze the query first
    console.print("[dim]Analyzing query...[/dim]")
    query_analysis = await llm_client.analyze_query(query)

    console.print(
        Panel(
            f"[bold]{query}[/bold]\n\n"
            f"Type: {query_analysis.get('decision_type', 'other')}\n"
            f"Tension: {query_analysis.get('core_tension', 'N/A')}\n"
            f"Stakes: {query_analysis.get('stakes', 'N/A')}",
            title="Decision Query",
            border_style="blue",
        )
    )

    # Simulate low confidence to trigger the agent
    confidence = RetrievalConfidence(
        score=0.35,
        level="low",
        reasons=["Simulated low confidence for agent testing"],
    )

    # Run the agent
    console.print("\n[yellow]Running agent search...[/yellow]\n")
    result = await agent.search_for_stories(
        decision_text=query,
        query_analysis=query_analysis,
        confidence=confidence,
    )

    # Display agent activity
    activity_table = Table(title="Agent Activity", show_header=False)
    activity_table.add_column("Metric", style="cyan")
    activity_table.add_column("Value", style="white")

    activity_table.add_row("Confidence trigger", f"{confidence.level} ({confidence.score:.2f})")
    activity_table.add_row("Tool calls", f"{result.tool_calls_made}/{agent_settings.max_tool_calls}")

    for i, tc in enumerate(result.tool_calls, 1):
        if tc.error:
            activity_table.add_row(
                f"  {i}. {tc.tool_name}", f"[red]ERROR: {tc.error}[/red]"
            )
        else:
            activity_table.add_row(
                f"  {i}. {tc.tool_name}",
                f"{tc.candidates_found} candidates → {tc.validated_count} validated ({tc.latency_ms}ms)",
            )

    activity_table.add_row("Stories returned", str(result.stories_count))
    activity_table.add_row("Total candidates", str(result.total_candidates_found))
    activity_table.add_row("Validated", str(result.validated_count))
    activity_table.add_row("Rejected", str(result.rejected_count))
    activity_table.add_row("Latency", f"{result.total_latency_ms}ms")

    console.print(Panel(activity_table, border_style="green"))

    # Display validated stories
    if result.stories:
        console.print(f"\n[bold green]Validated Stories ({len(result.stories)}):[/bold green]\n")

        for i, story in enumerate(result.stories, 1):
            preview = story.text[:200].replace("\n", " ")
            if len(story.text) > 200:
                preview += "..."

            console.print(
                Panel(
                    f"[italic]{preview}[/italic]\n\n"
                    f"Source: {story.source} | "
                    f"Confidence: {story.validation_confidence:.2f} | "
                    f"Richness: {story.emotional_richness} | "
                    f"Elapsed: {story.time_elapsed_months} months\n"
                    f"Type: {story.decision_type} | "
                    f"Sentiment: {story.outcome_sentiment} | "
                    f"Themes: {', '.join(story.key_themes)}\n"
                    f"Insight: {story.hindsight_insight}",
                    title=f"[{i}] {story.source}",
                    border_style="dim",
                )
            )
    else:
        console.print("\n[red]No stories found.[/red]")

    console.print()


def main():
    parser = argparse.ArgumentParser(description="Echoes Phase 4 Agent Test CLI")
    parser.add_argument(
        "--query", "-q",
        type=str,
        help="Decision query to test (interactive prompt if not provided)",
    )
    args = parser.parse_args()

    if args.query:
        query = args.query
    else:
        console.print("\n[bold cyan]Echoes Agent — Phase 4 Test CLI[/bold cyan]")
        query = console.input("\n[bold]Decision query:[/bold] ")
        if not query.strip():
            console.print("[red]No query provided.[/red]")
            return

    asyncio.run(run_agent_test(query.strip()))


if __name__ == "__main__":
    main()
