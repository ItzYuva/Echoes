"""
Echoes Data Pipeline — Reddit Scraper (Component 1)

PRAW-based scraper that searches target subreddits for retrospective content.
Pulls both posts and top-level comments, anonymizes authors, deduplicates
via content hashing, and stores raw items in the SQLite staging database.

Features:
  - Configurable search queries targeting retrospective language
  - Rate limiting (respects Reddit's 60 req/min)
  - Incremental: tracks last-scraped timestamp per subreddit+query pair
  - Content deduplication via SHA-256 hash
  - Minimum content length filtering
"""

from __future__ import annotations

import hashlib
import time
from datetime import datetime, timezone
from typing import Optional

import praw

from config.logging_config import get_logger
from config.settings import RedditSettings
from scrapers.base_scraper import BaseScraper
from storage.models import ContentType, PipelineStatus, ScrapedItem
from storage.sqlite_store import SQLiteStore

logger = get_logger(__name__)


def _hash_text(text: str) -> str:
    """Generate a SHA-256 hash of normalized text for deduplication.

    Normalization: lowercase, stripped of leading/trailing whitespace.

    Args:
        text: Raw text content.

    Returns:
        Hex-encoded SHA-256 hash string.
    """
    normalized = text.strip().lower()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _hash_author(author_name: str) -> str:
    """Generate an anonymized hash of a Reddit username.

    Args:
        author_name: Reddit username.

    Returns:
        Hex-encoded SHA-256 hash string.
    """
    return hashlib.sha256(author_name.encode("utf-8")).hexdigest()


class RedditScraper(BaseScraper):
    """PRAW-based Reddit scraper for retrospective content.

    Iterates over configured subreddits and search queries,
    fetching posts and their top-level comments. Deduplicates
    against the SQLite store and respects rate limits.

    Args:
        settings: Reddit API configuration.
        store: SQLite staging store for persistence and dedup.
    """

    def __init__(self, settings: RedditSettings, store: SQLiteStore) -> None:
        self.settings = settings
        self.store = store
        self.reddit = praw.Reddit(
            client_id=settings.client_id,
            client_secret=settings.client_secret,
            user_agent=settings.user_agent,
        )
        # Verify credentials
        try:
            _ = self.reddit.user.me()
            logger.info("Reddit API: authenticated as script app")
        except Exception:
            logger.info("Reddit API: running in read-only mode")

    def get_source_name(self) -> str:
        """Return the source identifier."""
        return "reddit"

    def scrape(self) -> list[ScrapedItem]:
        """Execute a full scrape run across all subreddits and queries.

        For each subreddit+query combination:
          1. Search for matching posts
          2. For each post, optionally fetch top-level comments
          3. Deduplicate against existing content
          4. Store new items in SQLite

        Returns:
            List of newly scraped items (already persisted to SQLite).
        """
        all_items: list[ScrapedItem] = []
        total_duplicates = 0

        for subreddit_name in self.settings.subreddits:
            logger.info("Scraping r/%s ...", subreddit_name)
            subreddit = self.reddit.subreddit(subreddit_name)

            for query in self.settings.search_queries:
                items, dupes = self._scrape_query(subreddit, subreddit_name, query)
                all_items.extend(items)
                total_duplicates += dupes

        logger.info(
            "[bold green]Scrape complete:[/] %d new items, %d duplicates skipped",
            len(all_items),
            total_duplicates,
        )
        return all_items

    def scrape_subreddit(
        self, subreddit_name: str, queries: Optional[list[str]] = None
    ) -> list[ScrapedItem]:
        """Scrape a single subreddit with specified or default queries.

        Args:
            subreddit_name: Name of the subreddit (without r/ prefix).
            queries: Optional list of search queries. Uses defaults if None.

        Returns:
            List of newly scraped items.
        """
        subreddit = self.reddit.subreddit(subreddit_name)
        queries = queries or self.settings.search_queries
        all_items: list[ScrapedItem] = []

        for query in queries:
            items, _ = self._scrape_query(subreddit, subreddit_name, query)
            all_items.extend(items)

        return all_items

    def _scrape_query(
        self,
        subreddit: praw.models.Subreddit,
        subreddit_name: str,
        query: str,
    ) -> tuple[list[ScrapedItem], int]:
        """Search a subreddit with a single query and process results.

        Args:
            subreddit: PRAW subreddit object.
            subreddit_name: Name string for logging.
            query: Search query string.

        Returns:
            Tuple of (new_items, duplicate_count).
        """
        new_items: list[ScrapedItem] = []
        duplicates = 0

        logger.info("  Query: '%s' in r/%s", query, subreddit_name)

        try:
            search_results = subreddit.search(
                query,
                sort="relevance",
                time_filter="all",
                limit=self.settings.max_posts_per_query,
            )

            for post in search_results:
                # Rate limiting
                time.sleep(self.settings.rate_limit_pause)

                # Process the post itself
                post_item = self._process_post(post, subreddit_name)
                if post_item:
                    if self.store.content_hash_exists(post_item.content_hash):
                        duplicates += 1
                    else:
                        if self.store.insert_item(post_item):
                            new_items.append(post_item)
                        else:
                            duplicates += 1

                # Process top-level comments
                if self.settings.fetch_comments:
                    comment_items = self._process_comments(
                        post, subreddit_name
                    )
                    for comment_item in comment_items:
                        if self.store.content_hash_exists(comment_item.content_hash):
                            duplicates += 1
                        else:
                            if self.store.insert_item(comment_item):
                                new_items.append(comment_item)
                            else:
                                duplicates += 1

            # Update scrape state for incremental runs
            if new_items:
                latest_utc = max(
                    item.created_utc for item in new_items
                ).isoformat()
                self.store.update_scrape_state(
                    subreddit_name, query, latest_utc, len(new_items)
                )

        except Exception as e:
            logger.error(
                "Error scraping r/%s with query '%s': %s",
                subreddit_name, query, e,
            )

        logger.info(
            "    → %d new items, %d duplicates", len(new_items), duplicates
        )
        return new_items, duplicates

    def _process_post(
        self, post: praw.models.Submission, subreddit_name: str
    ) -> Optional[ScrapedItem]:
        """Convert a PRAW submission into a ScrapedItem.

        Filters out posts below the minimum content length and score.

        Args:
            post: PRAW submission object.
            subreddit_name: Name of the subreddit.

        Returns:
            ScrapedItem or None if the post doesn't qualify.
        """
        # Use selftext for text posts; skip link-only posts
        text = post.selftext or ""
        if len(text) < self.settings.min_content_length:
            return None

        if post.score < self.settings.min_score:
            return None

        author_name = str(post.author) if post.author else "[deleted]"

        return ScrapedItem(
            source="reddit",
            subreddit=subreddit_name,
            content_type=ContentType.POST,
            reddit_id=post.id,
            author_hash=_hash_author(author_name),
            title=post.title,
            text=text,
            content_hash=_hash_text(text),
            score=post.score,
            url=f"https://reddit.com{post.permalink}",
            created_utc=datetime.fromtimestamp(post.created_utc, tz=timezone.utc),
        )

    def _process_comments(
        self,
        post: praw.models.Submission,
        subreddit_name: str,
    ) -> list[ScrapedItem]:
        """Extract qualifying top-level comments from a post.

        Args:
            post: PRAW submission object.
            subreddit_name: Name of the subreddit.

        Returns:
            List of ScrapedItem instances for qualifying comments.
        """
        items: list[ScrapedItem] = []

        try:
            post.comments.replace_more(limit=0)  # don't expand "load more"
            for comment in post.comments:
                if not hasattr(comment, "body"):
                    continue

                text = comment.body or ""
                if len(text) < self.settings.min_content_length:
                    continue

                if comment.score < self.settings.min_score:
                    continue

                author_name = str(comment.author) if comment.author else "[deleted]"

                item = ScrapedItem(
                    source="reddit",
                    subreddit=subreddit_name,
                    content_type=ContentType.COMMENT,
                    reddit_id=comment.id,
                    author_hash=_hash_author(author_name),
                    title=None,
                    text=text,
                    content_hash=_hash_text(text),
                    score=comment.score,
                    url=f"https://reddit.com{comment.permalink}",
                    parent_id=post.id,
                    parent_title=post.title,
                    created_utc=datetime.fromtimestamp(
                        comment.created_utc, tz=timezone.utc
                    ),
                )
                items.append(item)

                # Rate limit between comment processing
                time.sleep(self.settings.rate_limit_pause * 0.5)

        except Exception as e:
            logger.warning(
                "Error processing comments for post %s: %s", post.id, e
            )

        return items
