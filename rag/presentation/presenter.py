"""
Echoes Phase 3 -- Story Presenter (Component 4)

Sends the final ranked stories through Gemini Flash to produce
a human, reverent presentation. Supports streaming.
"""

from __future__ import annotations

import time
from typing import AsyncIterator, List, Optional

from config.logging_config import get_logger
from rag.presentation.models import PresentationResult
from rag.presentation.prompts import build_presentation_prompt
from rag.query.models import QueryAnalysis
from rag.ranking.models import ScoredStory

logger = get_logger(__name__)


class StoryPresenter:
    """Presents ranked stories through the LLM.

    Formats stories with the presentation prompt and sends them
    to Gemini Flash for a human, reverent presentation.

    Args:
        llm_client: A BaseLLMClient implementation.
    """

    def __init__(self, llm_client) -> None:
        self.llm_client = llm_client

    async def present(
        self,
        user_text: str,
        query_analysis: QueryAnalysis,
        stories: List[ScoredStory],
        stream: bool = False,
    ) -> PresentationResult:
        """Present stories to the user.

        Args:
            user_text: The user's original decision description.
            query_analysis: Structured analysis of the query.
            stories: Ranked stories to present.
            stream: Whether to stream the response.

        Returns:
            PresentationResult with the formatted output.
        """
        if not stories:
            return PresentationResult(
                text="I don't have enough relevant stories to share right now. "
                     "As more experiences are added to Echoes, I'll be better able to help.",
                stories_presented=0,
            )

        start = time.time()

        prompt = build_presentation_prompt(
            user_text=user_text,
            decision_type=query_analysis.decision_type,
            decision_subcategory=query_analysis.decision_subcategory,
            core_tension=query_analysis.core_tension,
            stakes=query_analysis.stakes,
            stories=stories,
        )

        try:
            result_text = await self.llm_client.present_stories(
                prompt=prompt,
                stream=stream,
            )

            latency_ms = int((time.time() - start) * 1000)

            return PresentationResult(
                text=result_text,
                story_ids=[s.point_id for s in stories],
                stories_presented=len(stories),
                latency_ms=latency_ms,
            )

        except Exception as e:
            logger.error("Presentation failed: %s", e)
            # Fallback: present stories raw
            return self._fallback_present(stories, time.time() - start)

    def _fallback_present(
        self, stories: List[ScoredStory], elapsed: float
    ) -> PresentationResult:
        """Raw story presentation when LLM fails."""
        parts = ["Here are stories from people who stood where you're standing.\n"]

        for story in stories:
            elapsed_months = story.time_elapsed_months
            if elapsed_months >= 12:
                time_str = f"Written {elapsed_months // 12} year{'s' if elapsed_months // 12 != 1 else ''} later"
            elif elapsed_months > 0:
                time_str = f"Written {elapsed_months} month{'s' if elapsed_months != 1 else ''} later"
            else:
                time_str = ""

            parts.append(f"{story.text}\n\n— *{time_str}*\n")

        parts.append("\nThese are their stories. Yours is still being written.")

        return PresentationResult(
            text="\n---\n\n".join(parts),
            story_ids=[s.point_id for s in stories],
            stories_presented=len(stories),
            latency_ms=int(elapsed * 1000),
        )
