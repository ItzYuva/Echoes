"""
Echoes Data Pipeline — Text Chunker

Splits long narratives into overlapping chunks for embedding.
Most Reddit posts/comments are naturally story-sized (200-800 words)
and won't be chunked. Only narratives exceeding the threshold are split.

Chunking strategy:
  - Split at paragraph boundaries
  - Target chunk size: 300-600 words
  - Overlap: 1 sentence from the end of each chunk carried to the next
  - Each chunk inherits the full metadata from the parent story
"""

from __future__ import annotations

import re
import json
from datetime import datetime
from typing import Optional

from config.logging_config import get_logger
from config.settings import PipelineSettings
from storage.models import StoryChunk, StoryMetadata

logger = get_logger(__name__)


class TextChunker:
    """Splits long texts into manageable chunks for embedding.

    Only texts exceeding the word threshold are chunked. Short texts
    pass through as a single chunk.

    Args:
        settings: Pipeline settings with chunking parameters.
    """

    def __init__(self, settings: PipelineSettings) -> None:
        self.max_words = settings.max_chunk_words
        self.min_words = settings.min_chunk_words
        self.overlap_sentences = settings.chunk_overlap_sentences
        self.threshold_words = settings.chunk_threshold_words

    def chunk_story(
        self,
        item: dict,
        metadata: Optional[StoryMetadata] = None,
    ) -> list[StoryChunk]:
        """Split a story item into one or more chunks.

        Short stories become a single chunk. Long stories are split
        at paragraph boundaries with sentence overlap.

        Args:
            item: Item dict from SQLite (must have 'id', 'text', etc.).
            metadata: Optional extracted metadata to attach to each chunk.

        Returns:
            List of StoryChunk instances.
        """
        text = item["text"]
        word_count = len(text.split())

        # Parse metadata fields from the item dict
        key_themes = item.get("key_themes", "[]")
        if isinstance(key_themes, str):
            try:
                key_themes = json.loads(key_themes)
            except (json.JSONDecodeError, TypeError):
                key_themes = []

        # Common fields for all chunks
        base_fields = {
            "parent_id": item["id"],
            "source": item.get("source", "reddit"),
            "subreddit": item.get("subreddit", ""),
            "author_hash": item.get("author_hash", ""),
            "scraped_at": (
                datetime.fromisoformat(item["scraped_at"])
                if item.get("scraped_at")
                else None
            ),
            "original_score": item.get("score", 0),
            "decision_type": item.get("decision_type", "other") or "other",
            "decision_subcategory": item.get("decision_subcategory", "") or "",
            "outcome_sentiment": item.get("outcome_sentiment", "neutral") or "neutral",
            "time_elapsed_months": item.get("time_elapsed_months", -1) or -1,
            "emotional_richness": item.get("emotional_richness", 5) or 5,
            "outcome_clarity": bool(item.get("outcome_clarity", False)),
            "key_themes": key_themes,
            "hindsight_insight": item.get("hindsight_insight", "") or "",
            "classification_confidence": item.get("classification", "RETROSPECTIVE") or "RETROSPECTIVE",
        }

        # Override with metadata if provided
        if metadata:
            base_fields.update({
                "decision_type": metadata.decision_type.value,
                "decision_subcategory": metadata.decision_subcategory,
                "outcome_sentiment": metadata.outcome_sentiment.value,
                "time_elapsed_months": metadata.time_elapsed_months,
                "emotional_richness": metadata.emotional_richness,
                "outcome_clarity": metadata.outcome_clarity,
                "key_themes": metadata.key_themes,
                "hindsight_insight": metadata.hindsight_insight,
            })

        # Short text → single chunk
        if word_count <= self.threshold_words:
            return [
                StoryChunk(
                    text=text,
                    chunk_index=0,
                    total_chunks=1,
                    **base_fields,
                )
            ]

        # Long text → split at paragraph boundaries
        paragraphs = self._split_paragraphs(text)
        chunk_texts = self._merge_paragraphs(paragraphs)

        chunks = []
        total = len(chunk_texts)
        for i, chunk_text in enumerate(chunk_texts):
            chunks.append(
                StoryChunk(
                    text=chunk_text,
                    chunk_index=i,
                    total_chunks=total,
                    **base_fields,
                )
            )

        logger.debug(
            "Chunked story %s into %d chunks (%d words total)",
            item["id"], total, word_count,
        )
        return chunks

    def _split_paragraphs(self, text: str) -> list[str]:
        """Split text into paragraphs.

        Handles multiple newline patterns and filters empty paragraphs.

        Args:
            text: Raw text.

        Returns:
            List of non-empty paragraph strings.
        """
        # Split on double newlines or more
        paragraphs = re.split(r"\n\s*\n", text)
        return [p.strip() for p in paragraphs if p.strip()]

    def _merge_paragraphs(self, paragraphs: list[str]) -> list[str]:
        """Merge paragraphs into chunks within the word-count range.

        Greedily adds paragraphs to the current chunk until the max
        word limit is reached, then starts a new chunk with sentence
        overlap from the previous one.

        Args:
            paragraphs: List of paragraph strings.

        Returns:
            List of chunk text strings.
        """
        if not paragraphs:
            return []

        chunks: list[str] = []
        current_parts: list[str] = []
        current_words = 0

        for para in paragraphs:
            para_words = len(para.split())

            if current_words + para_words > self.max_words and current_parts:
                # Finalize current chunk
                chunk_text = "\n\n".join(current_parts)
                chunks.append(chunk_text)

                # Start new chunk with overlap
                overlap = self._get_last_sentences(chunk_text, self.overlap_sentences)
                current_parts = [overlap] if overlap else []
                current_words = len(overlap.split()) if overlap else 0

            current_parts.append(para)
            current_words += para_words

        # Don't forget the last chunk
        if current_parts:
            chunks.append("\n\n".join(current_parts))

        return chunks

    @staticmethod
    def _get_last_sentences(text: str, n: int) -> str:
        """Extract the last N sentences from a text for overlap.

        Args:
            text: Source text.
            n: Number of sentences to extract.

        Returns:
            The last N sentences joined as a string.
        """
        # Simple sentence splitting
        sentences = re.split(r"(?<=[.!?])\s+", text)
        if len(sentences) <= n:
            return ""
        return " ".join(sentences[-n:])
