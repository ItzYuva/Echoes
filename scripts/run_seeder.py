#!/usr/bin/env python
"""
Echoes Phase 3 -- Seeder Runner

Seeds the Qdrant database with test data:
  1. Synthetic stories via Gemini Flash
  2. Hand-written stories from a CSV

Usage:
    # Seed everything (synthetic + CSV)
    python scripts/run_seeder.py

    # Synthetic only (first 10 stories)
    python scripts/run_seeder.py --mode synthetic --max 10

    # CSV only
    python scripts/run_seeder.py --mode csv

    # Start from index 20 (to resume after a failure)
    python scripts/run_seeder.py --mode synthetic --start 20
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Ensure project root is in path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.logging_config import get_logger, setup_logging
from config.settings import Settings

logger = get_logger(__name__)


async def run_synthetic(settings: Settings, max_stories: int, start: int) -> None:
    """Generate and seed synthetic stories."""
    from seeder.synthetic_generator import SyntheticGenerator

    generator = SyntheticGenerator(settings)
    print(f"\n🌱 Generating synthetic stories (max={max_stories}, start={start})...\n")

    stats = await generator.generate_and_seed(
        max_stories=max_stories if max_stories > 0 else None,
        start_from=start,
    )

    print("\n╭─────────────────────────────────────────────╮")
    print("│ Synthetic Seeder Results                     │")
    print("├─────────────────────────────────────────────┤")
    print(f"│ Total specs:    {stats['total_specs']:>5}                        │")
    print(f"│ Generated:      {stats['generated']:>5}                        │")
    print(f"│ Tagged:         {stats['tag_success']:>5}                        │")
    print(f"│ Embedded:       {stats['embedded']:>5}                        │")
    print(f"│ Stored:         {stats['stored']:>5}                        │")
    print(f"│ Errors:         {stats['errors']:>5}                        │")
    print("╰─────────────────────────────────────────────╯")


async def run_csv(settings: Settings, csv_path: str) -> None:
    """Seed stories from a CSV file."""
    from seeder.csv_seeder import CSVSeeder

    seeder = CSVSeeder(settings)
    print(f"\n📄 Seeding from CSV: {csv_path}...\n")

    stats = await seeder.seed_from_csv(csv_path)

    print("\n╭─────────────────────────────────────────────╮")
    print("│ CSV Seeder Results                           │")
    print("├─────────────────────────────────────────────┤")
    print(f"│ Total rows:     {stats['total_rows']:>5}                        │")
    print(f"│ Tagged:         {stats['tagged']:>5}                        │")
    print(f"│ Embedded:       {stats['embedded']:>5}                        │")
    print(f"│ Stored:         {stats['stored']:>5}                        │")
    print(f"│ Errors:         {stats['errors']:>5}                        │")
    print("╰─────────────────────────────────────────────╯")


def main() -> None:
    parser = argparse.ArgumentParser(description="Echoes Test Data Seeder")
    parser.add_argument(
        "--mode",
        choices=["synthetic", "csv", "all"],
        default="all",
        help="What to seed (default: all)",
    )
    parser.add_argument(
        "--max",
        type=int,
        default=0,
        help="Max synthetic stories to generate (0=all)",
    )
    parser.add_argument(
        "--start",
        type=int,
        default=0,
        help="Starting index in generation matrix",
    )
    parser.add_argument(
        "--csv",
        type=str,
        default=str(Path(__file__).resolve().parent.parent / "seeder" / "seed_stories.csv"),
        help="Path to CSV file",
    )
    args = parser.parse_args()

    setup_logging()

    from config.settings import get_settings
    settings = get_settings()

    print("╭──────────────────────────────────────────────╮")
    print("│ 🌱 Echoes Phase 3 — Test Data Seeder         │")
    print("│ Seeds Qdrant with retrospective stories       │")
    print("╰──────────────────────────────────────────────╯")

    if args.mode in ("csv", "all"):
        asyncio.run(run_csv(settings, args.csv))

    if args.mode in ("synthetic", "all"):
        asyncio.run(run_synthetic(settings, args.max, args.start))

    print("\n✅ Seeding complete!")


if __name__ == "__main__":
    main()
