"""
Echoes Phase 4 -- Web Archive Search Tool

Searches beyond Reddit for retrospective narratives: memoirs, oral histories,
personal essays, interview transcripts. These are often higher quality and
longer-time-horizon stories than Reddit posts.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus

import httpx

from agent.config.agent_config import WEB_SOURCES, AgentSettings
from agent.tools.search_utils import (
    content_hash,
    extract_links_from_html,
    extract_story_text_from_html,
)
from config.logging_config import get_logger

logger = get_logger(__name__)

# Track consecutive failures per source for auto-disabling
_source_failures: Dict[str, int] = {}


class WebSearchTool:
    """Search the web for retrospective narratives.

    Searches multiple web sources (StoryCorps, The Moth, Medium, Quora)
    for personal essays and oral histories. Handles source failures
    gracefully — individual sources can fail without killing the search.

    Args:
        agent_settings: Agent configuration.
    """

    def __init__(self, agent_settings: AgentSettings) -> None:
        self.settings = agent_settings
        self._client_kwargs = {
            "timeout": agent_settings.web_request_timeout_seconds,
            "follow_redirects": True,
            "headers": {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
            },
        }

    async def search(
        self,
        query: str,
        source_types: Optional[List[str]] = None,
        max_results: int = 10,
    ) -> List[Dict[str, Any]]:
        """Search web sources for retrospective narratives.

        Iterates through enabled sources, fetches search result pages,
        extracts story links, fetches individual stories, and extracts
        text content.

        Args:
            query: Search query targeting retrospective narratives.
            source_types: Optional filter — ["memoir", "oral_history",
                         "personal_essay", "interview"].
            max_results: Maximum stories to return.

        Returns:
            List of story dicts with text, source, and source_url.
        """
        start = time.time()
        stories: List[Dict[str, Any]] = []
        sources = self._filter_sources(source_types)

        for source_name, source_config in sources.items():
            if len(stories) >= max_results:
                break

            if self._is_source_disabled(source_name):
                logger.debug("Skipping disabled source: %s", source_name)
                continue

            try:
                source_stories = await self._search_source(
                    source_name, source_config, query
                )
                stories.extend(source_stories)
                self._mark_source_success(source_name)

            except Exception as e:
                logger.warning("Failed to search %s: %s", source_name, e)
                self._mark_source_failure(source_name)
                continue

        latency = int((time.time() - start) * 1000)
        logger.info(
            "Web search: %d stories from %d sources in %dms",
            len(stories), len(sources), latency,
        )

        return stories[:max_results]

    async def _search_source(
        self,
        source_name: str,
        source_config: dict,
        query: str,
    ) -> List[Dict[str, Any]]:
        """Search a single web source for stories.

        Args:
            source_name: Name of the source (e.g., "storycorps").
            source_config: Source configuration dict.
            query: Search query.

        Returns:
            List of story dicts from this source.
        """
        search_url = source_config["search_url"].format(query=quote_plus(query))
        base_url = source_config.get("base_url", "")

        async with httpx.AsyncClient(**self._client_kwargs) as client:
            # Fetch search results page
            search_response = await client.get(search_url)
            if search_response.status_code != 200:
                logger.debug(
                    "%s returned %d for search", source_name, search_response.status_code
                )
                return []

            search_html = search_response.text

            # Extract story links
            link_selector = source_config.get("story_links_selector", "a")
            story_links = extract_links_from_html(search_html, link_selector, base_url)

            if not story_links:
                logger.debug("No story links found on %s", source_name)
                return []

            # Fetch individual story pages (max per source)
            stories = []
            max_per_source = self.settings.max_stories_per_web_source

            for link in story_links[:max_per_source + 2]:  # fetch a few extra in case some fail
                if len(stories) >= max_per_source:
                    break

                try:
                    story = await self._fetch_story(
                        client, link, source_name, source_config
                    )
                    if story:
                        stories.append(story)
                except Exception as e:
                    logger.debug("Failed to fetch story from %s: %s", link, e)
                    continue

            return stories

    async def _fetch_story(
        self,
        client: httpx.AsyncClient,
        url: str,
        source_name: str,
        source_config: dict,
    ) -> Optional[Dict[str, Any]]:
        """Fetch and extract text from a single story page.

        Args:
            client: HTTP client.
            url: Story page URL.
            source_name: Name of the source.
            source_config: Source configuration.

        Returns:
            Story dict or None if extraction fails.
        """
        response = await client.get(url)
        if response.status_code != 200:
            return None

        content_selector = source_config.get("content_selector", "article, .content")
        min_length = source_config.get("min_length", self.settings.min_story_length)

        text = extract_story_text_from_html(
            response.text, content_selector, min_length
        )

        if not text:
            return None

        # Truncate very long content
        if len(text) > 5000:
            text = text[:5000]

        return {
            "text": text,
            "source": f"web_{source_name}",
            "source_url": url,
            "source_type": source_config.get("type", "personal_essay"),
            "content_hash": content_hash(text),
        }

    def _filter_sources(
        self, source_types: Optional[List[str]] = None
    ) -> Dict[str, dict]:
        """Filter web sources by requested types.

        Args:
            source_types: Optional list of types to include.

        Returns:
            Filtered dict of source configs.
        """
        if not source_types:
            return WEB_SOURCES.copy()

        return {
            name: config
            for name, config in WEB_SOURCES.items()
            if config.get("type") in source_types
        }

    def _is_source_disabled(self, source_name: str) -> bool:
        """Check if a source has been auto-disabled due to consecutive failures."""
        failures = _source_failures.get(source_name, 0)
        return failures >= self.settings.source_failure_threshold

    def _mark_source_failure(self, source_name: str) -> None:
        """Record a failure for a source."""
        _source_failures[source_name] = _source_failures.get(source_name, 0) + 1
        if self._is_source_disabled(source_name):
            logger.warning(
                "Source %s disabled after %d consecutive failures",
                source_name, _source_failures[source_name],
            )

    def _mark_source_success(self, source_name: str) -> None:
        """Reset failure counter for a source on success."""
        if source_name in _source_failures:
            _source_failures[source_name] = 0
