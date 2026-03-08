#!/usr/bin/env python3
"""
Echoes Phase 2 -- Profile Inspector

Browse and inspect user profiles stored in PostgreSQL.

Usage:
    python scripts/inspect_profiles.py
    python scripts/inspect_profiles.py --user-id <UUID>
"""

from __future__ import annotations

import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from config.logging_config import setup_logging

console = Console()


async def main() -> None:
    """Inspect profiles in the database."""
    setup_logging()

    dsn = (
        f"postgresql://{os.getenv('POSTGRES_USER', 'echoes')}:"
        f"{os.getenv('POSTGRES_PASSWORD', 'echoes_dev')}@"
        f"{os.getenv('POSTGRES_HOST', 'localhost')}:"
        f"{os.getenv('POSTGRES_PORT', '5432')}/"
        f"{os.getenv('POSTGRES_DB', 'echoes')}"
    )

    try:
        from personality.storage.postgres_store import PostgresProfileStore

        store = PostgresProfileStore(dsn)
        await store.initialize()
    except Exception as e:
        console.print(f"[red]Cannot connect to PostgreSQL: {e}[/red]")
        console.print(
            "[dim]Make sure PostgreSQL is running: docker compose up -d postgres[/dim]"
        )
        return

    count = await store.get_profile_count()
    console.print(f"\n[bold]Echoes Profiles:[/bold] {count} total\n")

    if count == 0:
        console.print("[dim]No profiles yet. Run: python scripts/run_intake.py[/dim]")
        await store.close()
        return

    # If a specific user_id is provided
    if len(sys.argv) > 2 and sys.argv[1] == "--user-id":
        user_id = sys.argv[2]
        profile = await store.get_profile(user_id)
        if profile:
            _display_profile(profile)
        else:
            console.print(f"[red]Profile not found: {user_id}[/red]")
    else:
        # List all profiles (basic summary)
        console.print("[dim]Use --user-id <UUID> to see a full profile[/dim]\n")

    await store.close()


def _display_profile(data: dict) -> None:
    """Display a single profile in detail."""
    values = data["values_vector"]

    table = Table(title="Values Vector", show_header=True, header_style="bold cyan")
    table.add_column("Dimension", style="cyan")
    table.add_column("Value", justify="right")
    table.add_column("Bar", style="green")

    for dim, val in values.items():
        bar_len = int(float(val) * 20)
        bar = "█" * bar_len + "░" * (20 - bar_len)
        table.add_row(dim, f"{float(val):.2f}", bar)

    console.print(table)
    console.print(f"\n[dim]Created: {data['created_at']}[/dim]")
    console.print(f"[dim]Turns: {data['intake_turns']} | Version: {data['profile_version']}[/dim]")


if __name__ == "__main__":
    asyncio.run(main())
