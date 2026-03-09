"""
Echoes Data Pipeline — Embedding Generator (Component 4)

Generates vector embeddings for story chunks using Google's
gemini-embedding-001 model via the Gemini API. Handles batching
for efficiency and retry logic for API reliability.

Uses the same GOOGLE_API_KEY as the classifier — no extra API key needed.
"""

from __future__ import annotations

import time
from typing import Optional

import google.generativeai as genai
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from config.logging_config import get_logger
from config.settings import GeminiSettings

logger = get_logger(__name__)


class EmbeddingGenerator:
    """Generates text embeddings using Google's embedding API.

    Processes texts in configurable batch sizes for cost efficiency.
    Includes retry logic with exponential backoff for API resilience.

    Uses the same Gemini API key as the classifier — no separate
    OpenAI key required.

    Args:
        settings: Gemini API configuration.
        batch_size: Number of texts per batch (default: 100).
    """

    def __init__(
        self,
        settings: GeminiSettings,
        batch_size: int = 100,
    ) -> None:
        self.settings = settings
        genai.configure(api_key=settings.api_key)
        self.model = "models/gemini-embedding-001"
        self.batch_size = batch_size
        self.dimensions = 3072  # gemini-embedding-001 output dimensions

    @retry(
        retry=retry_if_exception_type((Exception,)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        reraise=True,
    )
    def _embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a batch of texts.

        Args:
            texts: List of text strings to embed.

        Returns:
            List of embedding vectors (same order as input).
        """
        result = genai.embed_content(
            model=self.model,
            content=texts,
            task_type="RETRIEVAL_DOCUMENT",
        )
        # embed_content returns a dict with 'embedding' key
        # For multiple texts, it returns a list of embeddings
        embeddings = result["embedding"]
        if isinstance(embeddings[0], float):
            # Single text was passed, wrap in list
            return [embeddings]
        return embeddings

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a list of texts, batching automatically.

        Splits the input into batches and processes each with retry logic.

        Args:
            texts: List of text strings to embed.

        Returns:
            List of embedding vectors (same order as input).
        """
        if not texts:
            return []

        all_embeddings: list[list[float]] = []

        for i in range(0, len(texts), self.batch_size):
            batch = texts[i: i + self.batch_size]
            try:
                embeddings = self._embed_batch(batch)
                all_embeddings.extend(embeddings)
                logger.debug(
                    "Embedded batch %d-%d (%d texts)",
                    i, i + len(batch), len(batch),
                )
            except Exception as e:
                logger.error(
                    "Embedding failed for batch %d-%d: %s", i, i + len(batch), e
                )
                # Return zero vectors for failed items so we don't lose position
                for _ in batch:
                    all_embeddings.append([0.0] * self.dimensions)

            # Small delay between batches to avoid rate limits
            if i + self.batch_size < len(texts):
                time.sleep(0.5)

        return all_embeddings

    def embed_single(self, text: str) -> Optional[list[float]]:
        """Generate an embedding for a single text.

        Args:
            text: Text string to embed.

        Returns:
            Embedding vector or None on failure.
        """
        try:
            result = self._embed_batch([text])
            return result[0] if result else None
        except Exception as e:
            logger.error("Single embedding failed: %s", e)
            return None
