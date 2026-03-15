"""
Echoes Phase 4 -- Agent Configuration

All agent-related settings: tool call limits, timeouts, source configs,
rate limiting, and feature flags.
"""

from __future__ import annotations

import os
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AgentSettings(BaseSettings):
    """Phase 4 agent configuration."""

    model_config = SettingsConfigDict(env_prefix="AGENT_")

    enabled: bool = True
    max_tool_calls: int = 3
    search_timeout_seconds: int = 30
    validation_timeout_seconds: int = 15

    # Rate limiting for Reddit JSON endpoints (unauthenticated)
    reddit_json_requests_per_minute: int = 10
    reddit_json_min_interval_seconds: float = 6.0

    # Web scraping
    web_request_timeout_seconds: int = 10
    max_stories_per_web_source: int = 3
    source_failure_threshold: int = 3  # disable source after N consecutive failures

    # Quality floors
    min_story_length: int = 150
    min_emotional_richness: int = 3

    # Background enrichment
    background_enrichment_enabled: bool = True


class RedditLiveSettings(BaseSettings):
    """Reddit API credentials for live search (optional)."""

    model_config = SettingsConfigDict(env_prefix="REDDIT_")

    client_id: str = ""
    client_secret: str = ""
    username: str = ""
    password: str = ""

    @property
    def has_api_credentials(self) -> bool:
        """Check if full PRAW credentials are available."""
        return bool(self.client_id and self.client_secret)


# Target subreddits prioritized for live search
LIVE_SEARCH_SUBREDDITS = [
    "AskReddit",
    "careerguidance",
    "relationships",
    "LifeAdvice",
    "DecidingToBeBetter",
    "offmychest",
    "ExperiencedDevs",
    "personalfinance",
    "AskOldPeople",
    "AskWomenOver30",
    "AskMenOver30",
]

# Subreddit routing by decision type
SUBREDDIT_ROUTING = {
    "career": ["careerguidance", "ExperiencedDevs", "AskOldPeople", "AskReddit"],
    "relationship": ["relationships", "AskWomenOver30", "AskMenOver30", "AskReddit"],
    "financial": ["personalfinance", "AskOldPeople", "AskReddit"],
    "relocation": ["AskReddit", "AskOldPeople", "LifeAdvice"],
    "education": ["AskReddit", "AskOldPeople", "DecidingToBeBetter"],
    "health": ["AskReddit", "LifeAdvice", "offmychest"],
    "family": ["relationships", "AskWomenOver30", "AskMenOver30", "offmychest"],
    "lifestyle": ["DecidingToBeBetter", "AskOldPeople", "LifeAdvice", "AskReddit"],
    "other": ["AskReddit", "AskOldPeople", "LifeAdvice", "offmychest"],
}

# Web archive sources
WEB_SOURCES = {
    "storycorps": {
        "base_url": "https://storycorps.org",
        "search_url": "https://storycorps.org/?s={query}",
        "type": "oral_history",
        "story_links_selector": ".story-card a, .post-card a, article a",
        "content_selector": ".story-content, .transcript-text, .entry-content, article .content",
        "min_length": 200,
    },
    "themoth": {
        "base_url": "https://themoth.org",
        "search_url": "https://themoth.org/search?q={query}",
        "type": "personal_essay",
        "story_links_selector": ".story-item a, .search-result a, article a",
        "content_selector": ".story-body, .story-text, .entry-content, article",
        "min_length": 200,
    },
    "medium_personal": {
        "search_url": "https://medium.com/search?q={query} looking back retrospective",
        "type": "personal_essay",
        "story_links_selector": "article a[href*='medium.com']",
        "content_selector": "article section, .meteredContent",
        "min_length": 300,
    },
    "quora_retrospective": {
        "search_url": "https://www.quora.com/search?q={query} looking back years later",
        "type": "personal_essay",
        "story_links_selector": ".q-box a[href*='/answer/']",
        "content_selector": ".q-text, .answer_content",
        "min_length": 200,
    },
}

# Retrospective modifiers for search query construction
RETROSPECTIVE_MODIFIERS = [
    "looking back",
    "years later",
    "hindsight",
    "update how it turned out",
    "regret",
    "best decision",
    "worst decision",
    "lesson learned",
]


def get_agent_settings() -> AgentSettings:
    """Load agent settings from environment."""
    return AgentSettings()


def get_reddit_live_settings() -> RedditLiveSettings:
    """Load Reddit live search settings."""
    return RedditLiveSettings()
