"""
Echoes Data Pipeline — Abstract LLM Client

Defines the interface that all LLM implementations must follow.
Pipeline code calls these methods — never the SDK directly.
This is the ONE abstraction worth having in v1: it lets us
swap Gemini for Claude/GPT/local models without touching pipeline logic.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from storage.models import ClassificationResult, StoryMetadata


class BaseLLMClient(ABC):
    """Abstract base class for LLM interactions.

    All LLM-dependent pipeline operations go through this interface.
    Implementations handle the API-specific details (auth, formatting,
    rate limiting, retries).
    """

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
