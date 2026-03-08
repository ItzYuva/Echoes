"""
Echoes Data Pipeline — Run Scraper CLI

CLI entry point for running just the Reddit scraper stage.
Useful for incrementally building up the raw content database
without running the full pipeline.

Usage:
    python scripts/run_scraper.py                    # scrape all subreddits
    python scripts/run_scraper.py --subreddit AskReddit  # single subreddit
    python scripts/run_scraper.py --limit 100        # limit posts per query
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.logging_config import setup_logging, get_logger
from config.settings import get_settings
from scrapers.reddit_scraper import RedditScraper
from storage.sqlite_store import SQLiteStore

logger = get_logger(__name__)


def main() -> None:
    """Run the Reddit scraper with CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Echoes — Reddit Scraper",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--subreddit", "-s",
        type=str,
        help="Scrape a specific subreddit only (e.g., AskReddit)",
    )
    parser.add_argument(
        "--limit", "-l",
        type=int,
        help="Override max posts per query",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging",
    )
    args = parser.parse_args()

    # Setup
    import logging
    setup_logging(
        level=logging.DEBUG if args.debug else logging.INFO,
        log_file="scraper.log",
    )
    settings = get_settings()

    if args.limit:
        settings.reddit.max_posts_per_query = args.limit

    store = SQLiteStore(settings.pipeline.staging_db_path)
    scraper = RedditScraper(settings.reddit, store)

    # Run
    logger.info("Starting scraper...")
    if args.subreddit:
        items = scraper.scrape_subreddit(args.subreddit)
    else:
        items = scraper.scrape()

    # Report
    total = store.get_total_count()
    status_counts = store.count_by_status()
    logger.info("Scraping complete. Total items in DB: %d", total)
    for status, count in sorted(status_counts.items()):
        logger.info("  %s: %d", status, count)


if __name__ == "__main__":
    main()
