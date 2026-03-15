"""
Echoes Phase 4 -- MCP Tool Definitions

Shared tool schemas used by both the direct-call agent (v1)
and the MCP server (v2 upgrade path). Defines the interface
contract for all agent tools.
"""

from __future__ import annotations

from typing import Any, Dict, List


def get_tool_definitions() -> List[Dict[str, Any]]:
    """Return MCP-compatible tool definitions for the agent.

    These schemas define the tools available to the LLM agent.
    Used by:
    - v1: Direct Python calls (agent reads these to know what tools exist)
    - v2: MCP server (registered as MCP tools with the same schema)

    Returns:
        List of tool definition dicts.
    """
    return [
        {
            "name": "search_reddit_stories",
            "description": (
                "Search Reddit for retrospective stories matching a decision query. "
                "Returns stories that have been found on Reddit, ready for validation. "
                "Best for: career decisions, relationship decisions, financial decisions, "
                "and any decision where people commonly share experiences on Reddit."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": (
                            "Search query targeting retrospective narratives. "
                            "Use past tense and retrospective language for best results."
                        ),
                    },
                    "subreddits": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "Optional list of subreddits to search. "
                            "Defaults to relevant subreddits based on decision type."
                        ),
                    },
                    "time_filter": {
                        "type": "string",
                        "enum": ["all", "year", "month", "week"],
                        "description": "Reddit time filter. Default: 'all'.",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum stories to return. Default 10, max 20.",
                    },
                },
                "required": ["query"],
            },
        },
        {
            "name": "search_web_stories",
            "description": (
                "Search the broader web for retrospective narratives from memoirs, "
                "oral histories, personal essays, and interview transcripts. "
                "Best for: existential/philosophical decisions, unusual life choices, "
                "and queries where Reddit is unlikely to have good coverage."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query targeting retrospective narratives.",
                    },
                    "source_types": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": ["memoir", "oral_history", "personal_essay", "interview"],
                        },
                        "description": "Optional filter by source type.",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum stories to return. Default 10, max 15.",
                    },
                },
                "required": ["query"],
            },
        },
        {
            "name": "validate_story",
            "description": (
                "Validate whether a piece of text is a genuine retrospective reflection. "
                "Returns classification, confidence, and metadata if it passes. "
                "Use this to verify individual stories before including them."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "The story text to validate.",
                    },
                    "source_url": {
                        "type": "string",
                        "description": "Optional source URL for provenance tracking.",
                    },
                },
                "required": ["text"],
            },
        },
    ]


def get_tool_definitions_for_gemini() -> List[Dict[str, Any]]:
    """Convert tool definitions to Gemini function calling format.

    Gemini uses a slightly different schema format for function declarations.

    Returns:
        List of Gemini-compatible function declarations.
    """
    tools = get_tool_definitions()
    gemini_tools = []

    for tool in tools:
        gemini_tool = {
            "name": tool["name"],
            "description": tool["description"],
            "parameters": _convert_to_gemini_schema(tool["parameters"]),
        }
        gemini_tools.append(gemini_tool)

    return gemini_tools


def _convert_to_gemini_schema(params: dict) -> dict:
    """Convert JSON Schema to Gemini's expected format.

    Gemini function calling uses a subset of OpenAPI schema.
    """
    result = {"type": "OBJECT", "properties": {}}
    required = params.get("required", [])

    for name, prop in params.get("properties", {}).items():
        gemini_prop = {"description": prop.get("description", "")}

        prop_type = prop.get("type", "string").upper()
        if prop_type == "ARRAY":
            gemini_prop["type"] = "ARRAY"
            items = prop.get("items", {})
            gemini_prop["items"] = {"type": items.get("type", "string").upper()}
        elif prop_type == "INTEGER":
            gemini_prop["type"] = "INTEGER"
        else:
            gemini_prop["type"] = "STRING"

        if "enum" in prop:
            gemini_prop["enum"] = prop["enum"]

        result["properties"][name] = gemini_prop

    if required:
        result["required"] = required

    return result
