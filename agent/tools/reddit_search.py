"""
Echoes Phase 4 -- Reddit Live Search Tool

Searches Reddit in real time for retrospective stories not in the static database.
Two backends: Reddit JSON endpoints (no API key) and PRAW (with API key).
Auto-detects which backend to use based on available credentials.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any, Dict, List, Optional

import httpx

from agent.config.agent_config import (
    LIVE_SEARCH_SUBREDDITS,
    RETROSPECTIVE_MODIFIERS,
    SUBREDDIT_ROUTING,
    AgentSettings,
    RedditLiveSettings,
)
from agent.tools.search_utils import (
    TokenBucketRateLimiter,
    build_reddit_search_queries,
    content_hash,
)
from config.logging_config import get_logger

logger = get_logger(__name__)

# Reddit JSON API headers
_REDDIT_HEADERS = {
    "User-Agent": "Echoes/1.0 (Decision Companion Research Tool)",
    "Accept": "application/json",
}


class RedditSearchTool:
    """Search Reddit for retrospective stories.

    Auto-selects between public JSON endpoints and PRAW based on
    available credentials. JSON endpoints work without authentication
    at ~10 requests/minute.

    Args:
        agent_settings: Agent configuration.
        reddit_settings: Reddit API credentials (optional).
    """

    def __init__(
        self,
        agent_settings: AgentSettings,
        reddit_settings: Optional[RedditLiveSettings] = None,
    ) -> None:
        self.settings = agent_settings
        self.reddit_settings = reddit_settings or RedditLiveSettings()
        self._rate_limiter = TokenBucketRateLimiter(
            rate=1.0 / agent_settings.reddit_json_min_interval_seconds,
            burst=2,
        )
        self._use_praw = self.reddit_settings.has_api_credentials

    async def search(
        self,
        query: str,
        subreddits: Optional[List[str]] = None,
        time_filter: str = "all",
        max_results: int = 10,
    ) -> List[Dict[str, Any]]:
        """Search Reddit for stories matching a decision query.

        Generates multiple retrospective-targeted search queries and
        searches across relevant subreddits.

        Args:
            query: Decision-related search query.
            subreddits: Optional list of subreddits to search.
            time_filter: Reddit time filter — "all", "year", "month", "week".
            max_results: Maximum raw results to return (before validation).

        Returns:
            List of raw story dicts with text, source_url, and Reddit metadata.
        """
        start = time.time()
        target_subs = subreddits or LIVE_SEARCH_SUBREDDITS[:6]

        # Build retrospective-targeted search queries
        search_queries = build_reddit_search_queries(
            query, RETROSPECTIVE_MODIFIERS, max_queries=3
        )

        all_results: List[Dict[str, Any]] = []
        seen_ids: set[str] = set()

        for search_query in search_queries:
            for subreddit in target_subs:
                if len(all_results) >= max_results:
                    break

                try:
                    if self._use_praw:
                        posts = await self._search_praw(
                            search_query, subreddit, time_filter
                        )
                    else:
                        posts = await self._search_json(
                            search_query, subreddit, time_filter
                        )

                    for post in posts:
                        post_id = post.get("reddit_id", "")
                        if post_id and post_id not in seen_ids:
                            seen_ids.add(post_id)
                            all_results.append(post)

                except Exception as e:
                    logger.warning(
                        "Reddit search failed for r/%s query='%s': %s",
                        subreddit, search_query[:50], e,
                    )
                    continue

            if len(all_results) >= max_results:
                break

        latency = int((time.time() - start) * 1000)
        logger.info(
            "Reddit search: %d results in %dms (queries=%d, subs=%d)",
            len(all_results), latency, len(search_queries), len(target_subs),
        )

        return all_results[:max_results]

    async def _search_json(
        self,
        query: str,
        subreddit: str,
        time_filter: str,
        limit: int = 25,
    ) -> List[Dict[str, Any]]:
        """Search Reddit using public JSON endpoints (no auth needed).

        Rate limited to ~10 requests/minute.

        Args:
            query: Search query string.
            subreddit: Subreddit to search.
            time_filter: Time filter (all, year, month, week).
            limit: Max results per request.

        Returns:
            List of parsed post dicts.
        """
        await self._rate_limiter.acquire()

        url = f"https://www.reddit.com/r/{subreddit}/search.json"
        params = {
            "q": query,
            "sort": "relevance",
            "t": time_filter,
            "limit": min(limit, 25),
            "type": "link",
            "restrict_sr": "true",
        }

        async with httpx.AsyncClient(timeout=self.settings.search_timeout_seconds) as client:
            response = await client.get(url, params=params, headers=_REDDIT_HEADERS)

            if response.status_code == 429:
                logger.warning("Reddit rate limited — backing off")
                await asyncio.sleep(10)
                return []

            if response.status_code != 200:
                logger.warning(
                    "Reddit JSON returned %d for r/%s", response.status_code, subreddit
                )
                return []

            try:
                data = response.json()
            except Exception:
                logger.warning("Reddit returned non-JSON response for r/%s", subreddit)
                return []

        return self._parse_json_results(data, subreddit)

    def _parse_json_results(
        self, data: dict, subreddit: str
    ) -> List[Dict[str, Any]]:
        """Parse Reddit JSON search response into story dicts.

        Handles unexpected response shapes defensively.

        Args:
            data: Raw JSON response from Reddit.
            subreddit: The subreddit that was searched.

        Returns:
            List of story dicts.
        """
        results = []

        try:
            children = data.get("data", {}).get("children", [])
        except (AttributeError, TypeError):
            logger.warning("Unexpected Reddit JSON structure")
            return []

        for child in children:
            try:
                post_data = child.get("data", {})

                # Get text content — selftext for text posts
                text = post_data.get("selftext", "").strip()
                title = post_data.get("title", "").strip()

                # Skip posts without meaningful text content
                if not text or len(text) < self.settings.min_story_length:
                    continue

                # Skip removed/deleted posts
                if text in ("[removed]", "[deleted]"):
                    continue

                # Combine title + body for richer context
                full_text = f"{title}\n\n{text}" if title else text

                permalink = post_data.get("permalink", "")
                source_url = f"https://www.reddit.com{permalink}" if permalink else ""

                results.append({
                    "text": full_text,
                    "source": "reddit_live",
                    "source_url": source_url,
                    "subreddit": f"r/{subreddit}",
                    "reddit_id": post_data.get("id", ""),
                    "score": post_data.get("score", 0),
                    "created_utc": post_data.get("created_utc", 0),
                    "num_comments": post_data.get("num_comments", 0),
                    "content_hash": content_hash(full_text),
                })

            except Exception as e:
                logger.debug("Failed to parse Reddit post: %s", e)
                continue

        return results

    async def _search_praw(
        self,
        query: str,
        subreddit: str,
        time_filter: str,
        limit: int = 25,
    ) -> List[Dict[str, Any]]:
        """Search Reddit using PRAW (requires API credentials).

        Runs PRAW in an executor since it's synchronous.

        Args:
            query: Search query string.
            subreddit: Subreddit to search.
            time_filter: Time filter.
            limit: Max results per request.

        Returns:
            List of parsed post dicts.
        """
        try:
            import praw
        except ImportError:
            logger.warning("PRAW not installed — falling back to JSON endpoints")
            self._use_praw = False
            return await self._search_json(query, subreddit, time_filter, limit)

        def _do_search():
            reddit = praw.Reddit(
                client_id=self.reddit_settings.client_id,
                client_secret=self.reddit_settings.client_secret,
                user_agent="Echoes/1.0 (Decision Companion Research Tool)",
            )
            sub = reddit.subreddit(subreddit)
            results = []

            for submission in sub.search(
                query, sort="relevance", time_filter=time_filter, limit=limit
            ):
                text = (submission.selftext or "").strip()
                if not text or len(text) < self.settings.min_story_length:
                    continue
                if text in ("[removed]", "[deleted]"):
                    continue

                title = submission.title or ""
                full_text = f"{title}\n\n{text}" if title else text

                results.append({
                    "text": full_text,
                    "source": "reddit_live",
                    "source_url": f"https://www.reddit.com{submission.permalink}",
                    "subreddit": f"r/{subreddit}",
                    "reddit_id": submission.id,
                    "score": submission.score,
                    "created_utc": submission.created_utc,
                    "num_comments": submission.num_comments,
                    "content_hash": content_hash(full_text),
                })

            return results

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _do_search)

    def get_subreddits_for_decision(self, decision_type: str) -> List[str]:
        """Get relevant subreddits for a decision type.

        Args:
            decision_type: The decision type from query analysis.

        Returns:
            List of subreddit names in priority order.
        """
        return SUBREDDIT_ROUTING.get(decision_type, SUBREDDIT_ROUTING["other"])
