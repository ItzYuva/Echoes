"""
Echoes Phase 1 — Live Demo

Seeds 5 realistic retrospective stories directly into the database,
then runs them through the full pipeline stages:
  Stage 2: Heuristic filter
  Stage 3: LLM classification (Gemini)
  Stage 4: Metadata tagging (Gemini)

No Reddit API needed — demonstrates the pipeline end-to-end.
Run: python scripts/demo.py
"""

from __future__ import annotations

import asyncio
import sys
import uuid
import hashlib
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from config.logging_config import setup_logging
from config.settings import get_settings
from storage.models import ScrapedItem, PipelineStatus, ContentType
from storage.sqlite_store import SQLiteStore
from classifiers.heuristic_filter import HeuristicFilter
from classifiers.llm_classifier import LLMClassifier
from processors.tagger import StoryTagger
from llm.gemini_client import GeminiClient

console = Console()

# ── 5 realistic demo stories ──────────────────────────────────────────────────

DEMO_STORIES = [
    {
        "title": "Left my corporate job 3 years ago — here's what actually happened",
        "text": (
            "Three years after leaving that corporate job, I can honestly say it was the best "
            "decision I ever made. At the time I was terrified — I had a mortgage, two kids, "
            "and everyone told me I was insane. But looking back, the fear of leaving was so "
            "much worse than anything that actually happened after. I started freelancing, made "
            "less money the first year, but I was present for my kids in a way I never was before. "
            "Now I make more than I did before and I actually enjoy what I do. The lesson? "
            "Fear is a terrible advisor."
        ),
        "subreddit": "careerguidance",
    },
    {
        "title": "Update: 8 months after my divorce",
        "text": (
            "Update: It's been 8 months since I ended things with my partner of 6 years. "
            "For anyone who read my original post and wondered how it turned out — I'm doing "
            "so much better than I expected. The first two months were brutal, not gonna lie. "
            "But I've reconnected with friends I'd lost touch with, started therapy, and honestly? "
            "I feel like myself again for the first time in years. I wish someone had told me "
            "that the hardest part isn't the decision — it's the first 60 days after."
        ),
        "subreddit": "relationships",
    },
    {
        "title": "Should I quit my job? Feeling burned out",
        "text": (
            "I'm thinking about quitting my job. I've been at this company for 3 years and "
            "I'm completely burned out. My manager is toxic, the pay hasn't kept up with "
            "inflation, and I dread Mondays. Should I just put in my two weeks or try to "
            "find something first? Any advice would be appreciated."
        ),
        "subreddit": "careerguidance",
    },
    {
        "title": "Moved across the country 5 years ago — was it worth it?",
        "text": (
            "I moved across the country 5 years ago for a job that paid 40% more. Everyone — "
            "my family, my friends, my then-girlfriend — said I was making a huge mistake. "
            "Here's what actually happened: the job was great for 2 years, then the company "
            "went under. But by then I'd built a new network, found a better job, met my "
            "now-wife, and discovered I actually love living in a big city. The decision to "
            "move wasn't about the job. It was about giving myself permission to start over."
        ),
        "subreddit": "AskReddit",
    },
    {
        "title": "In hindsight, dropping out of grad school saved me",
        "text": (
            "Six years ago I dropped out of my PhD program. At the time it felt like failure. "
            "My advisor called it a mistake, my parents were devastated, and I spent a year "
            "feeling lost. Looking back now, it was the best thing that ever happened to me. "
            "Academia was making me miserable. I joined a startup, learned to build products "
            "people actually use, and rediscovered why I liked this field in the first place. "
            "The credential would have been nice, but the life I have now is so much better "
            "than the one I was grinding towards."
        ),
        "subreddit": "DecidingToBeBetter",
    },
]


def _make_item(story: dict) -> ScrapedItem:
    """Create a ScrapedItem from a demo story dict."""
    text = story["text"]
    content_hash = hashlib.sha256(text.strip().lower().encode()).hexdigest()
    return ScrapedItem(
        id=str(uuid.uuid4()),
        source="demo",
        subreddit=story["subreddit"],
        content_type=ContentType.POST,
        reddit_id=f"demo_{content_hash[:8]}",
        author_hash=hashlib.sha256(b"demo_author").hexdigest(),
        title=story["title"],
        text=text,
        content_hash=content_hash,
        score=100,
        url=f"https://reddit.com/r/{story['subreddit']}/demo",
        created_utc=datetime.now(timezone.utc),
        scraped_at=datetime.now(timezone.utc),
        status=PipelineStatus.RAW,
    )


async def main() -> None:
    setup_logging()
    settings = get_settings()

    console.print(Panel(
        "[bold cyan]Echoes Phase 1 - Live Demo[/]\n"
        "Seeds 5 stories and runs them through the full pipeline.\n"
        "[dim]Stages: Heuristic -> LLM Classify -> Tag[/]",
        border_style="cyan",
    ))

    # ── Setup ──────────────────────────────────────────────────────────────────
    store = SQLiteStore(settings.pipeline.staging_db_path)
    gemini = GeminiClient(settings.gemini)
    heuristic = HeuristicFilter(threshold=settings.pipeline.heuristic_min_score)
    classifier = LLMClassifier(gemini, store, batch_size=10)
    tagger = StoryTagger(gemini, store, batch_size=10)

    # ── Stage 1: Seed stories ──────────────────────────────────────────────────
    console.print("\n[bold yellow]>>> Seeding demo stories into database...[/]")
    items = [_make_item(s) for s in DEMO_STORIES]
    inserted = 0
    for item in items:
        if store.insert_item(item):
            inserted += 1
    console.print(f"  Inserted [green]{inserted}[/] new stories "
                  f"([dim]{len(items) - inserted} already existed[/])")

    # ── Stage 2a: Heuristic filter ─────────────────────────────────────────────
    console.print("\n[bold yellow]>>> Stage 2a: Heuristic Filter[/]")
    raw_items = store.get_items_by_status(PipelineStatus.RAW)

    heuristic_table = Table(show_header=True, header_style="bold cyan")
    heuristic_table.add_column("Title", max_width=45)
    heuristic_table.add_column("Score", justify="right")
    heuristic_table.add_column("Result")
    heuristic_table.add_column("Top Signal")

    for item in raw_items:
        result = heuristic.evaluate(item["text"])
        store.update_heuristic_result(item["id"], result.passed, result.score)
        title = item.get("title", "")[:42] + "..." if len(item.get("title","")) > 42 else item.get("title","")
        top_signal = result.signals[0] if result.signals else "-"
        heuristic_table.add_row(
            title,
            f"{result.score:.2f}",
            "[green]PASS[/]" if result.passed else "[red]REJECT[/]",
            f"[dim]{top_signal}[/]",
        )

    console.print(heuristic_table)

    # ── Stage 2b: LLM classification ──────────────────────────────────────────
    heuristic_passed = store.get_items_by_status(PipelineStatus.HEURISTIC_PASS)
    if not heuristic_passed:
        console.print("[yellow]No items passed heuristic filter.[/]")
        return

    console.print(f"\n[bold yellow]>>> Stage 2b: LLM Classification "
                  f"([cyan]{len(heuristic_passed)}[/] items → Gemini)[/]")
    classify_stats = await classifier.classify_items(heuristic_passed, show_progress=True)
    console.print(
        f"  Results: [green]{classify_stats['retrospective']} retrospective[/], "
        f"[red]{classify_stats['not_retrospective']} rejected[/], "
        f"[yellow]{classify_stats['ambiguous']} ambiguous[/]"
    )

    # ── Stage 3: Tagging ───────────────────────────────────────────────────────
    classified = store.get_items_by_status(PipelineStatus.CLASSIFIED_RETROSPECTIVE)
    if not classified:
        console.print("\n[yellow]No items passed LLM classification.[/]")
    else:
        console.print(f"\n[bold yellow]>>> Stage 3: Metadata Tagging "
                      f"([cyan]{len(classified)}[/] stories → Gemini)[/]")
        await tagger.tag_items(classified, show_progress=True)

    # ── Final results ──────────────────────────────────────────────────────────
    console.print("\n[bold yellow]>>> Final Results[/]")
    tagged = store.get_items_by_status(PipelineStatus.TAGGED)

    if not tagged:
        console.print("[dim]No stories were tagged. Check your GOOGLE_API_KEY.[/]")
        return

    for item in tagged:
        import json
        themes = item.get("key_themes", "[]")
        if isinstance(themes, str):
            try:
                themes = json.loads(themes)
            except Exception:
                themes = []

        console.print(Panel(
            f"[bold]{item.get('title', 'Untitled')}[/]\n"
            f"[dim]r/{item['subreddit']}[/]\n\n"
            f"[cyan]Decision type:[/]   {item.get('decision_type', '?')}\n"
            f"[cyan]Sentiment:[/]       {item.get('outcome_sentiment', '?')}\n"
            f"[cyan]Time elapsed:[/]    {item.get('time_elapsed_months', '?')} months\n"
            f"[cyan]Emotional depth:[/] {item.get('emotional_richness', '?')}/10\n"
            f"[cyan]Themes:[/]          {', '.join(themes) if themes else '?'}\n"
            f"[cyan]Insight:[/]         {item.get('hindsight_insight', '?')}\n",
            border_style="green",
        ))

    console.print(f"\n[bold green]Demo complete! {len(tagged)} stories fully processed.[/]")
    console.print("[dim]Run `python scripts/inspect_db.py` to explore the database.[/]")


if __name__ == "__main__":
    asyncio.run(main())
