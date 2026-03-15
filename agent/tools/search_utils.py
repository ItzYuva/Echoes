"""
Echoes Phase 4 -- Search Utilities

Query construction, rate limiting, content extraction, and deduplication
helpers shared across Reddit and web search tools.
"""

from __future__ import annotations

import asyncio
import hashlib
import re
import time
from typing import List, Optional
from urllib.parse import quote_plus

from config.logging_config import get_logger

logger = get_logger(__name__)


# ──────────────────────────────────────────────
# Rate Limiter
# ──────────────────────────────────────────────

class TokenBucketRateLimiter:
    """Simple async token-bucket rate limiter.

    Args:
        rate: Maximum requests per second.
        burst: Maximum burst size (tokens available immediately).
    """

    def __init__(self, rate: float, burst: int = 1) -> None:
        self.rate = rate
        self.burst = burst
        self._tokens = float(burst)
        self._last_refill = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """Wait until a token is available."""
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_refill
            self._tokens = min(self.burst, self._tokens + elapsed * self.rate)
            self._last_refill = now

            if self._tokens < 1.0:
                wait_time = (1.0 - self._tokens) / self.rate
                await asyncio.sleep(wait_time)
                self._tokens = 0.0
                self._last_refill = time.monotonic()
            else:
                self._tokens -= 1.0


# ──────────────────────────────────────────────
# Query Construction
# ──────────────────────────────────────────────

def extract_key_terms(decision_text: str) -> List[str]:
    """Extract meaningful search terms from a decision description.

    Strips common stop words and returns the most important terms
    for building targeted search queries.

    Args:
        decision_text: The user's decision description.

    Returns:
        List of key terms, ordered by likely relevance.
    """
    stop_words = {
        "i", "im", "i'm", "me", "my", "myself", "we", "our", "a", "an",
        "the", "is", "am", "are", "was", "were", "be", "been", "being",
        "have", "has", "had", "do", "does", "did", "will", "would", "could",
        "should", "may", "might", "shall", "can", "to", "of", "in", "for",
        "on", "with", "at", "by", "from", "as", "into", "about", "between",
        "through", "during", "before", "after", "above", "below", "and",
        "but", "or", "nor", "not", "so", "if", "then", "than", "that",
        "this", "these", "those", "it", "its", "what", "which", "who",
        "whom", "how", "when", "where", "why", "all", "each", "every",
        "both", "few", "more", "most", "other", "some", "such", "no",
        "only", "very", "just", "also", "really", "thinking", "considering",
        "whether", "up", "out", "off", "over", "again", "here", "there",
    }

    # Normalize and tokenize
    text = decision_text.lower()
    text = re.sub(r"[^\w\s'-]", " ", text)
    words = text.split()

    # Filter stop words, keep terms with substance
    terms = [w for w in words if w not in stop_words and len(w) > 2]

    # Deduplicate while preserving order
    seen = set()
    unique = []
    for t in terms:
        if t not in seen:
            seen.add(t)
            unique.append(t)

    return unique


def build_reddit_search_queries(
    decision_text: str,
    retrospective_modifiers: List[str],
    max_queries: int = 4,
) -> List[str]:
    """Generate Reddit-optimized search queries targeting retrospective content.

    From a decision description, produces multiple search queries that
    combine key terms with retrospective modifiers.

    Args:
        decision_text: The user's decision description.
        retrospective_modifiers: List of modifier phrases (e.g., "looking back").
        max_queries: Maximum number of queries to generate.

    Returns:
        List of search query strings.
    """
    terms = extract_key_terms(decision_text)
    if not terms:
        return [decision_text]

    # Take the top 3-4 terms for brevity
    core_terms = " ".join(terms[:4])

    queries = []
    for modifier in retrospective_modifiers[:max_queries]:
        queries.append(f"{core_terms} {modifier}")

    # Always include a plain version too
    if core_terms not in queries:
        queries.insert(0, core_terms)

    return queries[:max_queries]


def build_web_search_query(decision_text: str) -> str:
    """Build a URL-safe search query for web sources.

    Args:
        decision_text: The user's decision description.

    Returns:
        URL-encoded search query string.
    """
    terms = extract_key_terms(decision_text)
    query = " ".join(terms[:5])
    return quote_plus(query)


# ──────────────────────────────────────────────
# Content Extraction
# ──────────────────────────────────────────────

def extract_story_text_from_html(
    html: str,
    content_selector: str,
    min_length: int = 150,
) -> Optional[str]:
    """Extract story text from an HTML page using CSS selectors.

    Falls back to paragraph extraction if selectors don't match.

    Args:
        html: Raw HTML content.
        content_selector: CSS selector(s) for content elements.
        min_length: Minimum text length to accept.

    Returns:
        Extracted text or None if too short.
    """
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        logger.error("beautifulsoup4 not installed — cannot extract HTML content")
        return None

    soup = BeautifulSoup(html, "html.parser")

    # Remove script and style elements
    for tag in soup(["script", "style", "nav", "header", "footer", "aside"]):
        tag.decompose()

    # Try each selector
    for selector in content_selector.split(","):
        selector = selector.strip()
        elements = soup.select(selector)
        if elements:
            text = " ".join(el.get_text(separator=" ", strip=True) for el in elements)
            text = _clean_extracted_text(text)
            if len(text) >= min_length:
                return text

    # Fallback: collect all paragraphs
    paragraphs = soup.find_all("p")
    if paragraphs:
        text = " ".join(p.get_text(separator=" ", strip=True) for p in paragraphs)
        text = _clean_extracted_text(text)
        if len(text) >= min_length:
            return text

    return None


def extract_links_from_html(html: str, selector: str, base_url: str = "") -> List[str]:
    """Extract links from HTML using a CSS selector.

    Args:
        html: Raw HTML content.
        selector: CSS selector for link elements.
        base_url: Base URL for resolving relative links.

    Returns:
        List of absolute URLs.
    """
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        logger.error("beautifulsoup4 not installed — cannot extract links")
        return []

    soup = BeautifulSoup(html, "html.parser")
    links = []

    for element in soup.select(selector):
        href = element.get("href", "")
        if not href or href.startswith("#") or href.startswith("javascript:"):
            continue

        # Resolve relative URLs
        if href.startswith("/"):
            href = base_url.rstrip("/") + href
        elif not href.startswith("http"):
            href = base_url.rstrip("/") + "/" + href

        links.append(href)

    # Deduplicate preserving order
    seen = set()
    unique = []
    for link in links:
        if link not in seen:
            seen.add(link)
            unique.append(link)

    return unique


def _clean_extracted_text(text: str) -> str:
    """Clean up extracted text: collapse whitespace, remove artifacts."""
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# ──────────────────────────────────────────────
# Deduplication
# ──────────────────────────────────────────────

def content_hash(text: str) -> str:
    """Generate a hash of normalized text for deduplication.

    Args:
        text: The text to hash.

    Returns:
        SHA-256 hex digest of the normalized text.
    """
    normalized = re.sub(r"\s+", " ", text.lower().strip())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def deduplicate_stories(stories: list, existing_hashes: set[str] | None = None) -> list:
    """Remove duplicate stories by content hash.

    Args:
        stories: List of story dicts or LiveStory objects.
        existing_hashes: Optional set of hashes already in the database.

    Returns:
        Deduplicated list.
    """
    existing = existing_hashes or set()
    seen = set()
    unique = []

    for story in stories:
        text = story.text if hasattr(story, "text") else story.get("text", "")
        h = content_hash(text)
        if h not in seen and h not in existing:
            seen.add(h)
            unique.append(story)

    removed = len(stories) - len(unique)
    if removed:
        logger.info("Deduplication removed %d stories", removed)

    return unique
