#!/usr/bin/env python3
"""
Echoes Phase 2 -- Interactive Intake CLI

Run the personality intake conversation in your terminal.
This is how you test and experience the intake flow.

Usage:
    python scripts/run_intake.py
    python scripts/run_intake.py --no-save    # Don't save to DB
"""

from __future__ import annotations

import asyncio
import sys
import os
import time

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.text import Text
from rich.table import Table

from config.logging_config import get_logger, setup_logging
from config.settings import get_settings
from llm.gemini_client import GeminiClient
from personality.intake.conversation_manager import ConversationManager
from personality.intake.intake_config import IntakeConfig
from personality.models.values_vector import DIMENSION_NAMES, ValuesVector

logger = get_logger(__name__)
console = Console()


def render_values_bar(name: str, value: float, width: int = 20) -> str:
    """Render a single dimension as a visual bar."""
    filled = int(value * width)
    empty = width - filled
    bar = "[bold cyan]" + "█" * filled + "[dim]" + "░" * empty + "[/]"
    return f"  {name:<22s} {bar}  {value:.2f}"


def display_values_vector(vector: ValuesVector) -> None:
    """Display the values vector as a visual bar chart."""
    lines = []
    for dim in DIMENSION_NAMES:
        val = getattr(vector, dim)
        lines.append(render_values_bar(dim, val))

    output = "\n".join(lines)
    console.print(
        Panel(
            output,
            title="[bold]Your Values Profile[/bold]",
            border_style="cyan",
            padding=(1, 2),
        )
    )

    # Show dimension summaries
    summary = vector.dimension_summary()
    table = Table(show_header=True, header_style="bold magenta", padding=(0, 1))
    table.add_column("Dimension", style="cyan")
    table.add_column("Reading", style="white")
    table.add_column("Confidence", style="dim")

    for dim in DIMENSION_NAMES:
        confidence = vector.confidence_notes.get(dim, "")
        table.add_row(dim, summary[dim], confidence[:60] if confidence else "-")

    console.print(table)


async def run_intake() -> None:
    """Run the interactive intake conversation."""
    setup_logging()
    settings = get_settings()

    # Print header
    console.print()
    console.print(
        Panel(
            "[bold]Echoes -- Personality Intake[/bold]\n"
            "A short conversation to understand how you approach decisions.\n"
            "Answer honestly -- there are no right or wrong answers.\n"
            "Type [bold cyan]quit[/bold cyan] at any time to exit.",
            border_style="blue",
            padding=(1, 2),
        )
    )
    console.print()

    # Initialize LLM client
    try:
        gemini = GeminiClient(settings.gemini)
    except Exception as e:
        console.print(f"[red]Failed to initialize Gemini client: {e}[/red]")
        console.print("[dim]Check that GOOGLE_API_KEY is set in your .env file[/dim]")
        return

    # Create conversation manager
    config = IntakeConfig()
    manager = ConversationManager(llm_client=gemini, config=config)

    start_time = time.time()

    # Start the conversation
    console.print("[dim]Connecting to Echoes...[/dim]\n")
    try:
        opening = await manager.start()
    except Exception as e:
        console.print(f"[red]Failed to start intake: {e}[/red]")
        return

    console.print(Panel(opening, border_style="green", title="Echoes"))
    console.print()

    # Conversation loop
    while not manager.is_complete:
        try:
            user_input = Prompt.ask("[bold cyan]You[/bold cyan]")
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Intake cancelled.[/dim]")
            return

        if user_input.strip().lower() in ("quit", "exit", "q"):
            console.print("[dim]Intake cancelled.[/dim]")
            return

        if not user_input.strip():
            console.print("[dim]Please share your thoughts -- even a short answer helps.[/dim]")
            continue

        console.print()
        try:
            response, is_complete = await manager.respond(user_input)
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            continue

        if is_complete:
            console.print(Panel(response, border_style="green", title="Echoes"))
        else:
            console.print(Panel(response, border_style="green", title="Echoes"))

        console.print()

    # Show results
    duration = int(time.time() - start_time)
    vector = manager.values_vector

    if vector is None:
        console.print("[red]Intake completed but no values vector was extracted.[/red]")
        return

    console.print()
    console.print(
        Panel(
            "[bold]Intake Complete[/bold]",
            border_style="cyan",
        )
    )

    display_values_vector(vector)

    console.print(f"\n[dim]Intake took {manager.turn_count} turns in {duration} seconds[/dim]")

    # Offer to save
    save_prompt = "--no-save" not in sys.argv
    if save_prompt:
        console.print()
        console.print(
            "[dim]To save this profile to the database, you need PostgreSQL running.[/dim]"
        )
        console.print(
            "[dim]Run: docker compose up -d postgres[/dim]"
        )

        try:
            save = Prompt.ask(
                "Save this profile?",
                choices=["y", "n"],
                default="n",
            )
        except (KeyboardInterrupt, EOFError):
            save = "n"

        if save == "y":
            try:
                from personality.storage.postgres_store import PostgresProfileStore
                from personality.api.profile_api import ProfileAPI

                dsn = (
                    f"postgresql://{os.getenv('POSTGRES_USER', 'echoes')}:"
                    f"{os.getenv('POSTGRES_PASSWORD', 'echoes_dev')}@"
                    f"{os.getenv('POSTGRES_HOST', 'localhost')}:"
                    f"{os.getenv('POSTGRES_PORT', '5432')}/"
                    f"{os.getenv('POSTGRES_DB', 'echoes')}"
                )

                store = PostgresProfileStore(dsn)
                await store.initialize()

                api = ProfileAPI(store)
                user_id = await api.create_profile(
                    values_vector=vector,
                    intake_transcript=manager.transcript,
                    intake_turns=manager.turn_count,
                    intake_duration_seconds=duration,
                )

                console.print(f"\n[green]Profile saved! user_id = {user_id}[/green]")
                await store.close()
            except Exception as e:
                console.print(f"\n[yellow]Could not save to database: {e}[/yellow]")
                console.print("[dim]The profile data was displayed above -- you can save it manually.[/dim]")
    else:
        console.print("\n[dim]--no-save flag set. Profile not saved.[/dim]")


if __name__ == "__main__":
    asyncio.run(run_intake())
