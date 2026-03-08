"""
Echoes Data Pipeline — Run Full Pipeline CLI

CLI entry point for executing the complete pipeline:
  Scrape → Classify → Tag → Embed & Store

Each stage can be toggled on/off for targeted re-runs.

Usage:
    python scripts/run_pipeline.py                    # full pipeline
    python scripts/run_pipeline.py --no-scrape        # skip scraping
    python scripts/run_pipeline.py --classify-only    # only re-classify
    python scripts/run_pipeline.py --debug            # verbose logging
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.logging_config import setup_logging, get_logger
from config.settings import get_settings
from pipeline.orchestrator import PipelineOrchestrator

logger = get_logger(__name__)


def main() -> None:
    """Run the full Echoes pipeline with CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Echoes — Full Data Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/run_pipeline.py                  Run full pipeline
  python scripts/run_pipeline.py --no-scrape      Skip scraping (use existing raw data)
  python scripts/run_pipeline.py --classify-only  Only run classification stage
  python scripts/run_pipeline.py --tag-only       Only run tagging stage
  python scripts/run_pipeline.py --embed-only     Only run embedding stage
        """,
    )
    parser.add_argument(
        "--no-scrape",
        action="store_true",
        help="Skip the scraping stage",
    )
    parser.add_argument(
        "--no-classify",
        action="store_true",
        help="Skip the classification stage",
    )
    parser.add_argument(
        "--no-tag",
        action="store_true",
        help="Skip the tagging stage",
    )
    parser.add_argument(
        "--no-embed",
        action="store_true",
        help="Skip the embedding stage",
    )
    parser.add_argument(
        "--classify-only",
        action="store_true",
        help="Only run classification (implies --no-scrape --no-tag --no-embed)",
    )
    parser.add_argument(
        "--tag-only",
        action="store_true",
        help="Only run tagging (implies --no-scrape --no-classify --no-embed)",
    )
    parser.add_argument(
        "--embed-only",
        action="store_true",
        help="Only run embedding (implies --no-scrape --no-classify --no-tag)",
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
        log_file="pipeline.log",
    )
    settings = get_settings()

    # Determine which stages to run
    do_scrape = True
    do_classify = True
    do_tag = True
    do_embed = True

    if args.classify_only:
        do_scrape = do_tag = do_embed = False
    elif args.tag_only:
        do_scrape = do_classify = do_embed = False
    elif args.embed_only:
        do_scrape = do_classify = do_tag = False
    else:
        if args.no_scrape:
            do_scrape = False
        if args.no_classify:
            do_classify = False
        if args.no_tag:
            do_tag = False
        if args.no_embed:
            do_embed = False

    # Run pipeline
    orchestrator = PipelineOrchestrator(settings)

    try:
        stats = asyncio.run(
            orchestrator.run(
                scrape=do_scrape,
                classify=do_classify,
                tag=do_tag,
                embed=do_embed,
            )
        )
        logger.info("Pipeline finished successfully")
    except KeyboardInterrupt:
        logger.info("Pipeline interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error("Pipeline failed: %s", e, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
