"""
Echoes Phase 3 -- Query Embedder

Embeds user decision text and the LLM's focused query for Qdrant search.
Uses the same gemini-embedding-001 model as Phase 1.
"""

from __future__ import annotations

from typing import List, Optional

import google.generativeai as genai

from config.logging_config import get_logger
from processors.embedder import EmbeddingGenerator

logger = get_logger(__name__)


class QueryEmbedder:
    """Embeds user queries for vector search.

    Generates two embeddings per query:
    1. Primary — the user's raw text
    2. Focused — the LLM's 'what_would_help' interpretation

    Args:
        embedder: The Phase 1 EmbeddingGenerator instance.
    """

    def __init__(self, embedder: EmbeddingGenerator) -> None:
        self.embedder = embedder

    def embed_query(self, text: str) -> Optional[List[float]]:
        """Embed a single query text using RETRIEVAL_QUERY task type.

        Args:
            text: The text to embed.

        Returns:
            Embedding vector, or None on failure.
        """
        if not text or not text.strip():
            return None

        try:
            result = genai.embed_content(
                model="models/gemini-embedding-001",
                content=text,
                task_type="RETRIEVAL_QUERY",
            )
            embedding = result["embedding"]
            if isinstance(embedding[0], list):
                return embedding[0]
            return embedding
        except Exception as e:
            logger.error("Query embedding failed: %s", e)
            return None

    def embed_dual(
        self, user_text: str, focused_text: str
    ) -> tuple[Optional[List[float]], Optional[List[float]]]:
        """Generate both primary and focused embeddings.

        Args:
            user_text: The user's raw decision description.
            focused_text: The LLM's 'what_would_help' text.

        Returns:
            Tuple of (primary_embedding, focused_embedding).
        """
        primary = self.embed_query(user_text)
        focused = self.embed_query(focused_text) if focused_text else None
        return primary, focused
