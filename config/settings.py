"""
Echoes Data Pipeline — Central Configuration

All configuration values are loaded from environment variables with sensible defaults.
Uses pydantic-settings for validation and type coercion.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# ──────────────────────────────────────────────
# Project paths
# ──────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
LABELED_SAMPLES_DIR = DATA_DIR / "labeled_samples"
STAGING_DB_PATH = DATA_DIR / "staging.db"

# Ensure directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
LABELED_SAMPLES_DIR.mkdir(parents=True, exist_ok=True)


class RedditSettings(BaseSettings):
    """Reddit API credentials and scraping parameters."""

    model_config = SettingsConfigDict(env_prefix="REDDIT_")

    client_id: str = ""
    client_secret: str = ""
    user_agent: str = "Echoes Data Pipeline v1.0"

    # Target subreddits in priority order
    subreddits: list[str] = [
        "AskReddit",
        "LifeAdvice",
        "relationships",
        "careerguidance",
        "DecidingToBeBetter",
        "offmychest",
    ]

    # Search queries targeting retrospective language
    search_queries: list[str] = [
        "looking back",
        "years later",
        "in hindsight",
        "I wish I had",
        "update:",
        "if I could go back",
        "best decision",
        "worst decision",
        "regret",
        "turned out",
        "glad I did",
        "should have",
        "lesson learned",
    ]

    min_content_length: int = 150
    max_posts_per_query: int = 500
    rate_limit_pause: float = 1.0  # seconds between requests
    fetch_comments: bool = True
    max_comment_depth: int = 0  # 0 = top-level only
    min_score: int = 2  # skip heavily-downvoted content


class GeminiSettings(BaseSettings):
    """Google Gemini API configuration."""

    model_config = SettingsConfigDict(env_prefix="GOOGLE_")

    api_key: str = ""
    classification_model: str = "gemini-2.5-flash"
    fallback_model: str = "gemini-2.0-flash-lite"
    max_concurrency: int = 10  # semaphore limit for async calls
    request_timeout: int = 30  # seconds
    max_retries: int = 3



class QdrantSettings(BaseSettings):
    """Qdrant vector database configuration."""

    model_config = SettingsConfigDict(env_prefix="QDRANT_")

    host: str = "localhost"
    port: int = 6333
    grpc_port: int = 6334
    collection_name: str = "echoes_stories"
    distance_metric: str = "Cosine"


class PostgresSettings(BaseSettings):
    """PostgreSQL configuration for Phase 2 user profiles."""

    model_config = SettingsConfigDict(env_prefix="POSTGRES_")

    host: str = "localhost"
    port: int = 5432
    db: str = "echoes"
    user: str = "echoes"
    password: str = "echoes_dev"

    @property
    def dsn(self) -> str:
        """Build the PostgreSQL connection string."""
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.db}"


class PipelineSettings(BaseSettings):
    """Pipeline orchestration settings."""

    model_config = SettingsConfigDict(env_prefix="PIPELINE_")

    # Chunking
    max_chunk_words: int = 600
    min_chunk_words: int = 300
    chunk_overlap_sentences: int = 1
    chunk_threshold_words: int = 1000  # only chunk if text is longer than this

    # Classification
    heuristic_min_score: float = 0.3  # threshold for heuristic filter pass

    # Batching
    llm_batch_size: int = 20  # how many texts to classify in one async batch
    embed_batch_size: int = 100

    # Database
    staging_db_path: str = str(STAGING_DB_PATH)


class AgentSettings(BaseSettings):
    """Phase 4 agent configuration."""

    model_config = SettingsConfigDict(env_prefix="AGENT_")

    enabled: bool = True
    max_tool_calls: int = 3
    search_timeout_seconds: int = 30
    background_enrichment_enabled: bool = True


class Settings(BaseSettings):
    """Root settings object aggregating all sub-configs."""

    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    reddit: RedditSettings = Field(default_factory=RedditSettings)
    gemini: GeminiSettings = Field(default_factory=GeminiSettings)
    qdrant: QdrantSettings = Field(default_factory=QdrantSettings)
    postgres: PostgresSettings = Field(default_factory=PostgresSettings)
    pipeline: PipelineSettings = Field(default_factory=PipelineSettings)
    agent: AgentSettings = Field(default_factory=AgentSettings)


def get_settings() -> Settings:
    """Load and return the application settings.

    Reads from environment variables and .env file. Call this once at
    application startup and pass the settings object where needed.

    Returns:
        Settings: Fully resolved configuration object.
    """
    # Ensure .env is loaded before building sub-models
    from dotenv import load_dotenv

    load_dotenv(PROJECT_ROOT / ".env")

    return Settings(
        reddit=RedditSettings(),
        gemini=GeminiSettings(),
        qdrant=QdrantSettings(),
        postgres=PostgresSettings(),
        pipeline=PipelineSettings(),
        agent=AgentSettings(),
    )
