"""
Echoes Phase 4 -- MCP Server Standalone Runner

Starts the MCP server for debugging and testing with MCP-compatible clients.

Usage:
    python scripts/run_mcp_server.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rich.console import Console

console = Console()


async def run_server() -> None:
    """Initialize and run the MCP server on stdio."""
    from agent.config.agent_config import AgentSettings, RedditLiveSettings
    from agent.mcp_server.server import create_mcp_server, run_mcp_server_stdio
    from agent.tools.reddit_search import RedditSearchTool
    from agent.tools.story_validator import StoryValidator
    from agent.tools.web_search import WebSearchTool
    from classifiers.heuristic_filter import HeuristicFilter
    from config.settings import get_settings
    from llm.gemini_client import GeminiClient

    settings = get_settings()

    # Initialize components
    llm_client = GeminiClient(settings.gemini)
    heuristic = HeuristicFilter()
    agent_settings = AgentSettings()
    reddit_settings = RedditLiveSettings()

    reddit_search = RedditSearchTool(agent_settings, reddit_settings)
    web_search = WebSearchTool(agent_settings)
    validator = StoryValidator(heuristic, llm_client, agent_settings)

    # Create MCP server
    server = create_mcp_server(reddit_search, web_search, validator)

    if server is None:
        console.print(
            "[red]MCP SDK not installed. Install with: pip install mcp[/red]"
        )
        return

    console.print("[bold cyan]MCP Server 'echoes-mcp' running on stdio[/bold cyan]")
    console.print("Tools registered: search_reddit_stories, search_web_stories, validate_story")
    console.print("[dim]Waiting for MCP client connection...[/dim]\n")

    await run_mcp_server_stdio(server)


def main():
    asyncio.run(run_server())


if __name__ == "__main__":
    main()
