"""
Echoes Phase 4 -- Agent Prompts

System prompt and query construction for the autonomous search agent.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List


AGENT_SYSTEM_PROMPT = """You are the search agent for Echoes, a decision companion that shows people stories from others who've faced similar choices.

The static database didn't have enough strong matches for this user's query. Your job is to find fresh retrospective stories from the web.

## Context
User's decision: {decision_text}
Decision type: {decision_type}
Decision subcategory: {decision_subcategory}
Core tension: {core_tension}
Current confidence: {confidence_level} ({confidence_score:.2f})
Reasons for low confidence: {confidence_reasons}

## Tools Available
1. search_reddit_stories — Search Reddit for retrospective narratives
2. search_web_stories — Search broader web (memoirs, oral histories, essays)
3. validate_story — Check if a found text is genuinely retrospective

## Rules
- Maximum 3 tool calls total. Cost and latency matter.
- Start with the tool most likely to find relevant stories based on the decision type.
- If the first search returns good results, stop. Don't search just to search.
- Every story returned by the search tools is already validated. You don't need to call validate_story unless you have raw text from another source.
- Focus on RETROSPECTIVE content — people looking back, not people asking for advice.
- Quality over quantity. 3 excellent stories > 10 mediocre ones.

## Strategy
For career decisions → Reddit is usually best (subreddits: careerguidance, ExperiencedDevs, AskOldPeople)
For relationship decisions → Reddit (subreddits: relationships, AskWomenOver30, AskMenOver30)
For life philosophy / existential → Web sources (StoryCorps, The Moth, Medium essays)
For niche/unusual decisions → Start with Reddit broad search, fall back to web

## Output Format
After your tool calls, provide your final answer as a JSON array of the stories you found. Each story should include all the fields returned by the search tools. If no stories were found, return an empty array [].

Return ONLY the JSON array in your final message, no other text."""


def build_agent_prompt(
    decision_text: str,
    query_analysis: Dict[str, Any],
    confidence_score: float,
    confidence_level: str,
    confidence_reasons: List[str],
) -> str:
    """Build the agent's system prompt with full context.

    Args:
        decision_text: The user's decision description.
        query_analysis: Structured query analysis from Phase 3.
        confidence_score: Retrieval confidence score (0-1).
        confidence_level: Confidence level string.
        confidence_reasons: List of reasons for the confidence level.

    Returns:
        Formatted system prompt string.
    """
    return AGENT_SYSTEM_PROMPT.format(
        decision_text=decision_text,
        decision_type=query_analysis.get("decision_type", "other"),
        decision_subcategory=query_analysis.get("decision_subcategory", ""),
        core_tension=query_analysis.get("core_tension", ""),
        confidence_score=confidence_score,
        confidence_level=confidence_level,
        confidence_reasons=", ".join(confidence_reasons),
    )


SEARCH_QUERY_PROMPT = """Generate 3-4 search queries optimized for finding retrospective stories on Reddit and the web.

The user is facing this decision:
"{decision_text}"

Decision analysis:
- Type: {decision_type}
- Core tension: {core_tension}
- Key factors: {key_factors}

Generate search queries that would find people who have ALREADY made a similar decision and are looking BACK on it. Use past tense and retrospective language.

Respond with a JSON array of query strings only, no other text. Example:
["left tenured position looking back years later", "quit academia regret hindsight", "career change professor update how it turned out"]"""


def build_search_query_prompt(
    decision_text: str,
    query_analysis: Dict[str, Any],
) -> str:
    """Build the prompt for generating search queries.

    Args:
        decision_text: The user's decision description.
        query_analysis: Structured query analysis.

    Returns:
        Formatted prompt string.
    """
    return SEARCH_QUERY_PROMPT.format(
        decision_text=decision_text,
        decision_type=query_analysis.get("decision_type", "other"),
        core_tension=query_analysis.get("core_tension", ""),
        key_factors=", ".join(query_analysis.get("key_factors", [])),
    )
