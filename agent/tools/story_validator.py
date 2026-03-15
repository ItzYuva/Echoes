"""
Echoes Phase 4 -- Story Validator Tool

Quality gate for all live-fetched content. Every story from Reddit Live Search
or Web Archive Search passes through the same three-stage validation pipeline
as Phase 1: heuristic → LLM classification → metadata extraction.

CRITICAL: Reuses Phase 1 classifiers to maintain a single quality standard.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from agent.config.agent_config import AgentSettings
from agent.orchestrator.models import LiveStory, ValidationResult
from config.logging_config import get_logger

logger = get_logger(__name__)


class StoryValidator:
    """Three-stage validation pipeline for live-fetched stories.

    Applies the exact same quality bar as Phase 1's pipeline:
    1. Heuristic filter (instant, free)
    2. LLM retrospective classification (Gemini Flash)
    3. Metadata extraction (Gemini Flash)

    Reuses Phase 1 classifiers — one quality standard across the system.

    Args:
        heuristic_filter: Phase 1 HeuristicFilter instance.
        llm_client: Phase 1 BaseLLMClient instance (GeminiClient).
        agent_settings: Agent configuration.
    """

    def __init__(
        self,
        heuristic_filter,
        llm_client,
        agent_settings: AgentSettings,
    ) -> None:
        self.heuristic = heuristic_filter
        self.llm_client = llm_client
        self.settings = agent_settings

    async def validate(
        self,
        text: str,
        source_url: Optional[str] = None,
    ) -> ValidationResult:
        """Validate a single story through all three stages.

        Args:
            text: The story text to validate.
            source_url: Optional source URL for provenance tracking.

        Returns:
            ValidationResult with classification, confidence, and metadata.
        """
        start = time.time()

        # Stage 1: Heuristic check (instant, free)
        heuristic_result = self.heuristic.evaluate(text)
        if not heuristic_result.passed:
            logger.debug("Validation rejected at heuristic (score=%.2f)", heuristic_result.score)
            return ValidationResult(
                is_retrospective=False,
                confidence=0.0,
                rejection_reason="failed_heuristic",
            )

        # Stage 2: LLM classification
        try:
            from storage.models import ClassificationResult

            classification, raw_response = await self.llm_client.classify(text)

            if classification != ClassificationResult.RETROSPECTIVE:
                logger.debug("Validation rejected at LLM classification: %s", classification)
                return ValidationResult(
                    is_retrospective=False,
                    confidence=0.3,
                    rejection_reason="not_retrospective",
                )
        except Exception as e:
            logger.error("LLM classification failed during validation: %s", e)
            return ValidationResult(
                is_retrospective=False,
                confidence=0.0,
                rejection_reason="classification_error",
            )

        # Stage 3: Metadata extraction
        try:
            metadata = await self.llm_client.extract_metadata(text)

            if metadata is None:
                logger.warning("Metadata extraction returned None")
                return ValidationResult(
                    is_retrospective=False,
                    confidence=0.4,
                    rejection_reason="metadata_extraction_failed",
                )

            # Quality floor: reject low emotional richness
            if metadata.emotional_richness < self.settings.min_emotional_richness:
                logger.debug(
                    "Validation rejected: low emotional richness (%d)",
                    metadata.emotional_richness,
                )
                return ValidationResult(
                    is_retrospective=False,
                    confidence=0.5,
                    rejection_reason="low_quality",
                )

            latency = int((time.time() - start) * 1000)
            logger.info(
                "Story validated in %dms (richness=%d, type=%s)",
                latency, metadata.emotional_richness, metadata.decision_type.value,
            )

            return ValidationResult(
                is_retrospective=True,
                confidence=0.9,
                metadata={
                    "decision_type": metadata.decision_type.value,
                    "decision_subcategory": metadata.decision_subcategory,
                    "outcome_sentiment": metadata.outcome_sentiment.value,
                    "time_elapsed_months": metadata.time_elapsed_months,
                    "emotional_richness": metadata.emotional_richness,
                    "outcome_clarity": metadata.outcome_clarity,
                    "key_themes": metadata.key_themes,
                    "hindsight_insight": metadata.hindsight_insight,
                },
            )

        except Exception as e:
            logger.error("Metadata extraction failed during validation: %s", e)
            return ValidationResult(
                is_retrospective=False,
                confidence=0.3,
                rejection_reason="metadata_extraction_error",
            )

    async def validate_batch(
        self,
        stories: List[Dict[str, Any]],
    ) -> List[LiveStory]:
        """Validate multiple raw story dicts and return only validated LiveStory objects.

        Args:
            stories: List of raw story dicts from search tools.

        Returns:
            List of validated LiveStory objects with full metadata.
        """
        start = time.time()
        validated: List[LiveStory] = []
        rejected = 0

        for raw_story in stories:
            text = raw_story.get("text", "")
            source_url = raw_story.get("source_url", "")

            result = await self.validate(text, source_url)

            if result.is_retrospective and result.metadata:
                live_story = LiveStory(
                    text=text,
                    source=raw_story.get("source", "unknown"),
                    source_url=source_url,
                    decision_type=result.metadata["decision_type"],
                    decision_subcategory=result.metadata["decision_subcategory"],
                    outcome_sentiment=result.metadata["outcome_sentiment"],
                    time_elapsed_months=result.metadata["time_elapsed_months"],
                    emotional_richness=result.metadata["emotional_richness"],
                    outcome_clarity=result.metadata["outcome_clarity"],
                    key_themes=result.metadata["key_themes"],
                    hindsight_insight=result.metadata["hindsight_insight"],
                    validation_confidence=result.confidence,
                )
                validated.append(live_story)
            else:
                rejected += 1

        latency = int((time.time() - start) * 1000)
        logger.info(
            "Batch validation: %d validated, %d rejected in %dms",
            len(validated), rejected, latency,
        )

        return validated
