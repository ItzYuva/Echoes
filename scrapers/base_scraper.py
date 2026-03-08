"""
Echoes Data Pipeline — Abstract Base Scraper

Defines the interface for all data source scrapers. Each scraper
implementation handles its own API auth, pagination, and rate limiting.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from storage.models import ScrapedItem


class BaseScraper(ABC):
    """Abstract base class for content scrapers.

    Subclasses implement scraping logic for specific platforms
    (Reddit, StoryCorps, online forums, etc.).
    """

    @abstractmethod
    def scrape(self) -> list[ScrapedItem]:
        """Execute a full scrape run and return all new items.

        Implementations should:
          - Respect rate limits
          - Handle pagination
          - Deduplicate against previously seen content
          - Skip items below minimum length thresholds

        Returns:
            List of new ScrapedItem instances.
        """
        ...

    @abstractmethod
    def get_source_name(self) -> str:
        """Return a human-readable name for this data source.

        Returns:
            Source identifier string (e.g., "reddit", "storycorps").
        """
        ...
