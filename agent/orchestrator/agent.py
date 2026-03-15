"""
Echoes Phase 4 -- Agent Orchestrator

The brain of Phase 4. An LLM agent that receives a low-confidence retrieval
result from Phase 3, decides which tools to invoke, processes the results,
and returns supplemental stories that get merged into the response.

v1 Implementation: Direct tool calls (Approach B).
The LLM decides the strategy; tools are called directly via Python.
Structured for clean upgrade to MCP (Approach A) later.
"""

from __future__ import annotations

import asyncio
import json
import re
import time
from typing import Any, Dict, List, Optional

from agent.config.agent_config import AgentSettings, SUBREDDIT_ROUTING
from agent.mcp_server.tool_definitions import get_tool_definitions_for_gemini
from agent.orchestrator.models import AgentResult, LiveStory, ToolCallRecord
from agent.orchestrator.prompts import build_agent_prompt, build_search_query_prompt
from agent.tools.reddit_search import RedditSearchTool
from agent.tools.search_utils import deduplicate_stories
from agent.tools.story_validator import StoryValidator
from agent.tools.web_search import WebSearchTool
from config.logging_config import get_logger
from rag.confidence.models import RetrievalConfidence

logger = get_logger(__name__)


class AgentOrchestrator:
    """Autonomous agent that searches for stories when the database falls short.

    Uses Gemini Flash as the reasoning backbone. In v1, the agent uses a
    simplified decision loop: analyze the decision type, pick the best
    tool, search, validate, and return results.

    For v2, this will be upgraded to a full LLM agent loop where the LLM
    autonomously decides tool calls via the MCP protocol.

    Args:
        llm_client: Gemini client for LLM reasoning.
        reddit_search: Reddit search tool instance.
        web_search: Web archive search tool instance.
        validator: Story validator instance.
        agent_settings: Agent configuration.
    """

    def __init__(
        self,
        llm_client,
        reddit_search: RedditSearchTool,
        web_search: WebSearchTool,
        validator: StoryValidator,
        agent_settings: AgentSettings,
    ) -> None:
        self.llm_client = llm_client
        self.reddit_search = reddit_search
        self.web_search = web_search
        self.validator = validator
        self.settings = agent_settings

    async def search_for_stories(
        self,
        decision_text: str,
        query_analysis: Dict[str, Any],
        confidence: RetrievalConfidence,
        existing_hashes: Optional[set] = None,
    ) -> AgentResult:
        """Execute the agent's search strategy.

        Analyzes the decision type and confidence gap, then decides
        which tools to call and in what order.

        Args:
            decision_text: The user's decision description.
            query_analysis: Structured query analysis from Phase 3.
            confidence: Current retrieval confidence.
            existing_hashes: Content hashes of stories already in results.

        Returns:
            AgentResult with validated stories and execution metadata.
        """
        start = time.time()
        tool_calls: List[ToolCallRecord] = []
        all_validated: List[LiveStory] = []
        total_candidates = 0
        total_rejected = 0
        sources_searched: List[str] = []

        decision_type = query_analysis.get("decision_type", "other")

        # Generate optimized search queries via LLM
        search_queries = await self._generate_search_queries(
            decision_text, query_analysis
        )

        # Decide tool order based on decision type
        tool_order = self._decide_tool_order(decision_type)

        for tool_name in tool_order:
            if len(tool_calls) >= self.settings.max_tool_calls:
                logger.info("Agent reached max tool calls (%d)", self.settings.max_tool_calls)
                break

            # If we already have good stories, stop searching
            if len(all_validated) >= 5:
                logger.info("Agent found enough stories (%d), stopping", len(all_validated))
                break

            tool_start = time.time()
            query = search_queries[0] if search_queries else decision_text

            try:
                if tool_name == "search_reddit_stories":
                    raw_results = await self._call_reddit_search(
                        query, decision_type, search_queries
                    )
                    sources_searched.append("reddit_live")
                elif tool_name == "search_web_stories":
                    raw_results = await self._call_web_search(query, decision_type)
                    sources_searched.append("web_archive")
                else:
                    continue

                candidates = len(raw_results)
                total_candidates += candidates

                # Validate all results
                validated = await self.validator.validate_batch(raw_results)
                rejected = candidates - len(validated)
                total_rejected += rejected

                # Deduplicate against existing stories and previously found ones
                existing = existing_hashes or set()
                for s in all_validated:
                    from agent.tools.search_utils import content_hash
                    existing.add(content_hash(s.text))

                validated = deduplicate_stories(validated, existing)
                all_validated.extend(validated)

                tool_latency = int((time.time() - tool_start) * 1000)
                tool_calls.append(ToolCallRecord(
                    tool_name=tool_name,
                    arguments={"query": query, "decision_type": decision_type},
                    candidates_found=candidates,
                    validated_count=len(validated),
                    rejected_count=rejected,
                    latency_ms=tool_latency,
                ))

                logger.info(
                    "Tool %s: %d candidates → %d validated in %dms",
                    tool_name, candidates, len(validated), tool_latency,
                )

            except Exception as e:
                tool_latency = int((time.time() - tool_start) * 1000)
                logger.error("Tool %s failed: %s", tool_name, e)
                tool_calls.append(ToolCallRecord(
                    tool_name=tool_name,
                    arguments={"query": query},
                    error=str(e),
                    latency_ms=tool_latency,
                ))

        total_latency = int((time.time() - start) * 1000)

        result = AgentResult(
            stories=all_validated,
            tool_calls=tool_calls,
            tool_calls_made=len(tool_calls),
            sources_searched=sources_searched,
            total_candidates_found=total_candidates,
            validated_count=len(all_validated),
            rejected_count=total_rejected,
            total_latency_ms=total_latency,
            confidence_before=confidence.score,
        )

        logger.info(
            "Agent complete: %d stories from %d tool calls in %dms "
            "(candidates=%d, validated=%d, rejected=%d)",
            len(all_validated), len(tool_calls), total_latency,
            total_candidates, len(all_validated), total_rejected,
        )

        return result

    async def _generate_search_queries(
        self,
        decision_text: str,
        query_analysis: Dict[str, Any],
    ) -> List[str]:
        """Use the LLM to generate optimized search queries.

        Falls back to keyword extraction if LLM call fails.

        Args:
            decision_text: The user's decision description.
            query_analysis: Structured query analysis.

        Returns:
            List of 3-4 search query strings.
        """
        try:
            queries = await self.llm_client.build_search_queries(
                decision_text, query_analysis
            )
            if queries:
                return queries
        except Exception as e:
            logger.warning("LLM search query generation failed: %s", e)

        # Fallback: use basic keyword extraction
        from agent.tools.search_utils import build_reddit_search_queries
        from agent.config.agent_config import RETROSPECTIVE_MODIFIERS

        return build_reddit_search_queries(
            decision_text, RETROSPECTIVE_MODIFIERS, max_queries=3
        )

    def _decide_tool_order(self, decision_type: str) -> List[str]:
        """Decide which tools to call and in what order.

        Based on decision type heuristics:
        - Career/financial/relationship → Reddit first
        - Existential/lifestyle/other → Web first, then Reddit

        Args:
            decision_type: The decision type from query analysis.

        Returns:
            Ordered list of tool names.
        """
        web_first_types = {"lifestyle", "other"}

        if decision_type in web_first_types:
            return ["search_web_stories", "search_reddit_stories"]
        else:
            return ["search_reddit_stories", "search_web_stories"]

    async def _call_reddit_search(
        self,
        query: str,
        decision_type: str,
        search_queries: List[str],
    ) -> List[Dict[str, Any]]:
        """Execute Reddit search with appropriate subreddits.

        Args:
            query: Primary search query.
            decision_type: Decision type for subreddit routing.
            search_queries: All generated search queries.

        Returns:
            List of raw story dicts.
        """
        subreddits = self.reddit_search.get_subreddits_for_decision(decision_type)

        return await self.reddit_search.search(
            query=query,
            subreddits=subreddits,
            max_results=15,
        )

    async def _call_web_search(
        self,
        query: str,
        decision_type: str,
    ) -> List[Dict[str, Any]]:
        """Execute web archive search.

        Args:
            query: Search query.
            decision_type: Decision type for source selection.

        Returns:
            List of raw story dicts.
        """
        # For existential/philosophical, prefer oral histories
        source_types = None
        if decision_type in ("lifestyle", "other"):
            source_types = ["oral_history", "personal_essay"]

        return await self.web_search.search(
            query=query,
            source_types=source_types,
            max_results=10,
        )
