"""
Echoes Phase 4 -- MCP Server

A Model Context Protocol server that exposes the agent's tools.
This is the v2 upgrade path: same tools, exposed via MCP protocol
for interoperability with any MCP-compatible agent framework.

For v1, the agent calls tools directly via Python. This server
exists for future MCP client integration and standalone testing.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

from config.logging_config import get_logger

logger = get_logger(__name__)


def create_mcp_server(
    reddit_search_tool,
    web_search_tool,
    story_validator,
):
    """Create and configure the MCP server with registered tools.

    Args:
        reddit_search_tool: RedditSearchTool instance.
        web_search_tool: WebSearchTool instance.
        story_validator: StoryValidator instance.

    Returns:
        Configured MCP Server instance.
    """
    try:
        from mcp.server import Server
        from mcp.types import TextContent, Tool
    except ImportError:
        logger.warning(
            "MCP SDK not installed — MCP server unavailable. "
            "Install with: pip install mcp"
        )
        return None

    server = Server("echoes-mcp")

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            Tool(
                name="search_reddit_stories",
                description=(
                    "Search Reddit for retrospective stories matching a decision query."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"},
                        "subreddits": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Optional subreddit list",
                        },
                        "time_filter": {
                            "type": "string",
                            "enum": ["all", "year", "month", "week"],
                        },
                        "max_results": {"type": "integer"},
                    },
                    "required": ["query"],
                },
            ),
            Tool(
                name="search_web_stories",
                description=(
                    "Search the broader web for retrospective narratives."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"},
                        "source_types": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "max_results": {"type": "integer"},
                    },
                    "required": ["query"],
                },
            ),
            Tool(
                name="validate_story",
                description=(
                    "Validate whether text is a genuine retrospective reflection."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "description": "Story text"},
                        "source_url": {"type": "string"},
                    },
                    "required": ["text"],
                },
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:
        try:
            if name == "search_reddit_stories":
                results = await reddit_search_tool.search(
                    query=arguments["query"],
                    subreddits=arguments.get("subreddits"),
                    time_filter=arguments.get("time_filter", "all"),
                    max_results=arguments.get("max_results", 10),
                )
                # Validate results through the validator
                validated = await story_validator.validate_batch(results)
                return [TextContent(
                    type="text",
                    text=json.dumps([s.model_dump() for s in validated], default=str),
                )]

            elif name == "search_web_stories":
                results = await web_search_tool.search(
                    query=arguments["query"],
                    source_types=arguments.get("source_types"),
                    max_results=arguments.get("max_results", 10),
                )
                validated = await story_validator.validate_batch(results)
                return [TextContent(
                    type="text",
                    text=json.dumps([s.model_dump() for s in validated], default=str),
                )]

            elif name == "validate_story":
                result = await story_validator.validate(
                    text=arguments["text"],
                    source_url=arguments.get("source_url"),
                )
                return [TextContent(
                    type="text",
                    text=json.dumps(result.model_dump(), default=str),
                )]

            else:
                return [TextContent(type="text", text=f"Unknown tool: {name}")]

        except Exception as e:
            logger.error("MCP tool call failed for %s: %s", name, e)
            return [TextContent(type="text", text=f"Error: {e}")]

    return server


async def run_mcp_server_stdio(server) -> None:
    """Run the MCP server on stdio transport.

    Args:
        server: Configured MCP Server instance.
    """
    try:
        from mcp.server.stdio import stdio_server
    except ImportError:
        logger.error("MCP SDK required for stdio server")
        return

    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream)
