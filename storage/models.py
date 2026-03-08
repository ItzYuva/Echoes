"""
Echoes Data Pipeline — Data Models

Pydantic models defining the schema for every data structure flowing
through the pipeline. These serve as the single source of truth for
data shapes across scraping, classification, tagging, and storage.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field


# ──────────────────────────────────────────────
# Enums
# ──────────────────────────────────────────────

class ContentType(str, enum.Enum):
    """Whether the scraped item is a post or a comment."""
    POST = "post"
    COMMENT = "comment"


class PipelineStatus(str, enum.Enum):
    """Tracks where an item is in the processing pipeline."""
    RAW = "raw"
    HEURISTIC_PASS = "heuristic_pass"
    REJECTED_HEURISTIC = "rejected_heuristic"
    CLASSIFIED_RETROSPECTIVE = "classified_retrospective"
    REJECTED_LLM = "rejected_llm"
    NEEDS_REVIEW = "needs_review"
    TAGGED = "tagged"
    INDEXED = "indexed"
    FAILED = "failed"


class ClassificationResult(str, enum.Enum):
    """LLM classification output categories."""
    RETROSPECTIVE = "RETROSPECTIVE"
    NOT_RETROSPECTIVE = "NOT_RETROSPECTIVE"
    AMBIGUOUS = "AMBIGUOUS"


class DecisionType(str, enum.Enum):
    """High-level decision categories."""
    CAREER = "career"
    RELATIONSHIP = "relationship"
    RELOCATION = "relocation"
    EDUCATION = "education"
    HEALTH = "health"
    FINANCIAL = "financial"
    FAMILY = "family"
    LIFESTYLE = "lifestyle"
    OTHER = "other"


class OutcomeSentiment(str, enum.Enum):
    """How the author feels about the outcome."""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    MIXED = "mixed"
    NEUTRAL = "neutral"


# ──────────────────────────────────────────────
# Core Data Models
# ──────────────────────────────────────────────

class ScrapedItem(BaseModel):
    """A single piece of content scraped from a source (e.g., Reddit post or comment).

    This is the raw input to the pipeline before any classification or tagging.
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source: str = "reddit"
    subreddit: str
    content_type: ContentType
    reddit_id: str  # original Reddit post/comment ID
    author_hash: str  # SHA-256 of the author name (anonymized)
    title: Optional[str] = None  # posts have titles, comments don't
    text: str
    content_hash: str  # SHA-256 of normalized text for dedup
    score: int = 0
    url: Optional[str] = None
    parent_id: Optional[str] = None  # for comments: the post they belong to
    parent_title: Optional[str] = None  # title of parent post (for context)
    created_utc: datetime
    scraped_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    status: PipelineStatus = PipelineStatus.RAW
    heuristic_score: Optional[float] = None
    classification: Optional[ClassificationResult] = None
    classification_raw: Optional[str] = None  # raw LLM response for debugging


class StoryMetadata(BaseModel):
    """Structured metadata extracted from a classified retrospective story.

    Populated by the tagger (Component 3) using Gemini Flash.
    """
    decision_type: DecisionType = DecisionType.OTHER
    decision_subcategory: str = ""
    outcome_sentiment: OutcomeSentiment = OutcomeSentiment.NEUTRAL
    time_elapsed_months: int = -1  # -1 = unknown
    emotional_richness: int = 5  # 1-10
    outcome_clarity: bool = False
    key_themes: list[str] = Field(default_factory=list)
    hindsight_insight: str = ""


class TaggedStory(BaseModel):
    """A fully processed story: scraped content + classification + metadata.

    This is the complete record stored in SQLite after tagging.
    """
    id: str
    source: str
    subreddit: str
    content_type: ContentType
    reddit_id: str
    author_hash: str
    title: Optional[str] = None
    text: str
    content_hash: str
    score: int
    url: Optional[str] = None
    parent_id: Optional[str] = None
    parent_title: Optional[str] = None
    created_utc: datetime
    scraped_at: datetime
    status: PipelineStatus
    heuristic_score: Optional[float] = None
    classification: ClassificationResult = ClassificationResult.RETROSPECTIVE

    # Metadata fields (from tagger)
    metadata: Optional[StoryMetadata] = None


class StoryChunk(BaseModel):
    """A chunk of a story ready for embedding and vector storage.

    Most stories map 1:1 to a chunk. Longer narratives are split
    into overlapping chunks, each carrying the full metadata.
    """
    chunk_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    parent_id: str  # ID of the original ScrapedItem
    text: str
    chunk_index: int = 0
    total_chunks: int = 1

    # Carried-forward fields for Qdrant payload
    source: str = "reddit"
    subreddit: str = ""
    author_hash: str = ""
    scraped_at: Optional[datetime] = None
    original_score: int = 0
    decision_type: str = "other"
    decision_subcategory: str = ""
    outcome_sentiment: str = "neutral"
    time_elapsed_months: int = -1
    emotional_richness: int = 5
    outcome_clarity: bool = False
    key_themes: list[str] = Field(default_factory=list)
    hindsight_insight: str = ""
    classification_confidence: str = "RETROSPECTIVE"


class PipelineStats(BaseModel):
    """Summary statistics for a pipeline run."""
    total_scraped: int = 0
    duplicates_skipped: int = 0
    heuristic_passed: int = 0
    heuristic_rejected: int = 0
    llm_retrospective: int = 0
    llm_rejected: int = 0
    llm_ambiguous: int = 0
    tagged: int = 0
    tag_failed: int = 0
    indexed: int = 0
    chunks_total: int = 0
    errors: int = 0
