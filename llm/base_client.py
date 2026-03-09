"""
Echoes Data Pipeline -- Abstract LLM Client

Defines the interface that all LLM implementations must follow.
Pipeline code calls these methods -- never the SDK directly.
This is the ONE abstraction worth having in v1: it lets us
swap Gemini for Claude/GPT/local models without touching pipeline logic.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, List, Optional

from storage.models import ClassificationResult, StoryMetadata


class BaseLLMClient(ABC):
    """Abstract base class for LLM interactions.

    All LLM-dependent pipeline operations go through this interface.
    Implementations handle the API-specific details (auth, formatting,
    rate limiting, retries).
    """

    # -- Phase 1: Classification & Metadata -----------------------------------

    @abstractmethod
    async def classify(self, text: str) -> tuple[ClassificationResult, str]:
        """Classify a text as retrospective, not retrospective, or ambiguous.

        Args:
            text: The text to classify.

        Returns:
            Tuple of (classification_result, raw_response_string).
        """
        ...

    @abstractmethod
    async def classify_batch(
        self, texts: list[str]
    ) -> list[tuple[ClassificationResult, str]]:
        """Classify multiple texts concurrently.

        Implementations should use async concurrency with a semaphore
        to respect API rate limits.

        Args:
            texts: List of texts to classify.

        Returns:
            List of (classification_result, raw_response_string) tuples,
            in the same order as the input texts.
        """
        ...

    @abstractmethod
    async def extract_metadata(self, text: str) -> Optional[StoryMetadata]:
        """Extract structured metadata from a retrospective story.

        Args:
            text: The story text to analyze.

        Returns:
            StoryMetadata if extraction succeeds, None if it fails.
        """
        ...

    @abstractmethod
    async def extract_metadata_batch(
        self, texts: list[str]
    ) -> list[Optional[StoryMetadata]]:
        """Extract metadata from multiple stories concurrently.

        Args:
            texts: List of story texts.

        Returns:
            List of StoryMetadata (or None for failures), same order as input.
        """
        ...

    # -- Phase 2: Intake Conversation -----------------------------------------

    @abstractmethod
    async def intake_turn(
        self,
        system_prompt: str,
        conversation_history: List[Dict[str, str]],
    ) -> str:
        """Send a single turn of the intake conversation.

        Args:
            system_prompt: The system prompt defining the intake persona.
            conversation_history: List of {"role": ..., "content": ...} dicts.

        Returns:
            The LLM's next message (question or closing + values vector).
        """
        ...

    # -- Phase 3: RAG Core ---------------------------------------------------

    @abstractmethod
    async def analyze_query(self, user_text: str) -> dict:
        """Analyze a decision query and return structured information.

        Args:
            user_text: The user's decision description.

        Returns:
            Dict with decision_type, core_tension, emotional_state, etc.
        """
        ...

    @abstractmethod
    async def present_stories(self, prompt: str, stream: bool = False) -> str:
        """Present stories using the presentation prompt.

        Args:
            prompt: The full presentation prompt with stories.
            stream: Whether to stream the response.

        Returns:
            The formatted presentation text.
        """
        ...

    @abstractmethod
    async def generate_synthetic_story(
        self,
        decision_type: str,
        scenario: str,
        time_elapsed: str,
        outcome_tone: str,
    ) -> str:
        """Generate a realistic retrospective story for test data seeding.

        Args:
            decision_type: Type of decision (career, relationship, etc.).
            scenario: Specific scenario description.
            time_elapsed: How long since the decision.
            outcome_tone: positive / negative / mixed.

        Returns:
            The generated story text.
        """
        ...
