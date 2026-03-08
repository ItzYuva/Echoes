"""
Echoes Data Pipeline — Seed Labels Helper

Creates an initial hand-labeled dataset for classifier validation.
Provides example retrospective and non-retrospective texts that can
be used to test the heuristic filter and LLM classifier accuracy.

Usage:
    python scripts/seed_labels.py               # create labeled samples
    python scripts/seed_labels.py --validate     # run classifier on samples and report accuracy
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rich.console import Console
from rich.table import Table

from config.logging_config import setup_logging
from config.settings import get_settings, LABELED_SAMPLES_DIR

console = Console()

# ──────────────────────────────────────────────
# Hand-labeled examples
# ──────────────────────────────────────────────

LABELED_EXAMPLES = [
    # RETROSPECTIVE (positive examples)
    {
        "text": "Three years after leaving that corporate job, I can honestly say it was the best decision I ever made. At the time I was terrified — I had a mortgage, two kids, and everyone told me I was insane. But looking back, the fear of leaving was so much worse than anything that actually happened after. I started freelancing, made less money the first year, but I was present for my kids in a way I never was before. Now I make more than I did before and I actually enjoy what I do. The lesson? Fear is a terrible advisor.",
        "label": "RETROSPECTIVE",
        "notes": "Clear temporal distance, outcome revealed, hindsight wisdom"
    },
    {
        "text": "Looking back on my divorce, I realize the signs were there for years. I just wasn't ready to see them. We had this pattern where every argument ended with 'let's just move on' without actually resolving anything. Five years later, I'm in a healthy relationship where we actually communicate, and I can see how much I've grown. I don't regret the marriage because it taught me what I actually need from a partner.",
        "label": "RETROSPECTIVE",
        "notes": "Reflection with temporal distance, personal growth, lesson learned"
    },
    {
        "text": "Update: It's been 8 months since I ended things with my partner of 6 years. For anyone who read my original post and wondered how it turned out — I'm doing so much better than I expected. The first two months were brutal, not gonna lie. But I've reconnected with friends I'd lost touch with, started therapy, and honestly? I feel like myself again for the first time in years.",
        "label": "RETROSPECTIVE",
        "notes": "Update format, temporal distance, outcome clarity"
    },
    {
        "text": "I moved across the country 5 years ago for a job that paid 40% more. Everyone — my family, my friends, my then-girlfriend — said I was making a huge mistake. Here's what actually happened: the job was great for 2 years, then the company went under. But by then I'd built a new network, found a better job, met my now-wife, and discovered I actually love living in a big city. The decision to move wasn't about the job. It was about giving myself permission to start over.",
        "label": "RETROSPECTIVE",
        "notes": "5-year temporal distance, narrative arc, unexpected outcome"
    },
    {
        "text": "I wish I had taken that gap year when I was 18 instead of rushing into college. I graduated, got a job, but spent my 20s feeling like I was on a treadmill I couldn't get off. At 32, I finally took a 'gap year' of sorts — quit my job, traveled for 6 months, came back with clarity I never had. The lesson I learned too late: you can always resume the grind. You can't always recover the time you spent grinding without purpose.",
        "label": "RETROSPECTIVE",
        "notes": "Regret, temporal distance, wisdom earned from experience"
    },
    {
        "text": "Ten years ago I chose to stay in my hometown instead of moving to NYC for my dream job. At the time, I told myself it was the responsible choice — aging parents, affordable rent, childhood friends nearby. Now at 35, I sometimes wonder what could have been, but honestly? I've built something beautiful here. My parents got to know their grandkids, I run a small business that actually matters to my community. Not every good life follows the script we imagine at 22.",
        "label": "RETROSPECTIVE",
        "notes": "Ten-year reflection, nuanced outcome (mixed but ultimately positive)"
    },

    # NOT RETROSPECTIVE (negative examples)
    {
        "text": "I'm thinking about quitting my job. I've been at this company for 3 years and I'm completely burned out. My manager is toxic, the pay hasn't kept up with inflation, and I dread Mondays. Should I just put in my two weeks or try to find something first? Any advice would be appreciated.",
        "label": "NOT_RETROSPECTIVE",
        "notes": "In-the-moment, seeking advice, no hindsight"
    },
    {
        "text": "Just got dumped after 4 years together. She said she doesn't see a future with me. I'm sitting in my apartment right now feeling like the floor dropped out from under me. How do you even start to move on from something like this? I don't know who I am without her.",
        "label": "NOT_RETROSPECTIVE",
        "notes": "In-the-moment emotional reaction, no temporal distance"
    },
    {
        "text": "What should I do about my toxic boss? She undermines me in meetings, takes credit for my work, and recently started assigning me to projects below my level. I've been documenting everything but I'm not sure if I should go to HR or just start looking for a new job. Has anyone dealt with something like this?",
        "label": "NOT_RETROSPECTIVE",
        "notes": "Present tense, seeking advice, no reflection on outcome"
    },
    {
        "text": "I'm so excited to start my new job next week! After months of interviewing, I finally got an offer from my dream company. This is going to be the fresh start I needed. Wish me luck!",
        "label": "NOT_RETROSPECTIVE",
        "notes": "In-the-moment optimism, forward-looking, no hindsight"
    },
    {
        "text": "Just bought my first house!! I know the market is crazy right now but we found a place we love and the interest rate is locked in. So nervous but also thrilled. Any first-time homeowner tips?",
        "label": "NOT_RETROSPECTIVE",
        "notes": "In-the-moment excitement, seeking tips, no retrospective element"
    },
    {
        "text": "Does anyone else feel like their 20s are just a series of failures? I graduated 2 years ago and I still haven't figured out what I want to do. All my friends seem to have their lives together. Is this normal?",
        "label": "NOT_RETROSPECTIVE",
        "notes": "Present distress, seeking validation, no hindsight on specific decision"
    },

    # AMBIGUOUS
    {
        "text": "I've been thinking a lot about the decision I made to drop out of medical school. It's been a year now. Part of me thinks I made the right call because I was miserable, but another part of me wonders if I gave up too easily. I'm working in tech now and it's... fine? I guess? I don't know if I'll ever know if I made the right choice.",
        "label": "AMBIGUOUS",
        "notes": "Some temporal distance but outcome is unresolved, still processing"
    },
    {
        "text": "My therapist says I need to stop ruminating about moving in with my ex. It's been 6 months since we broke up and I keep going back to whether I should have kept my own place. I think the lesson is that you should always keep your own space, but honestly I'm not sure I've fully processed it yet.",
        "label": "AMBIGUOUS",
        "notes": "Some reflection but still in active processing, not settled"
    },
]


def create_labeled_samples() -> None:
    """Write labeled samples to the data/labeled_samples directory."""
    LABELED_SAMPLES_DIR.mkdir(parents=True, exist_ok=True)

    output_path = LABELED_SAMPLES_DIR / "labeled_examples.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(LABELED_EXAMPLES, f, indent=2, ensure_ascii=False)

    console.print(
        f"[green]Created {len(LABELED_EXAMPLES)} labeled samples at {output_path}[/]"
    )

    # Summary
    from collections import Counter
    label_counts = Counter(ex["label"] for ex in LABELED_EXAMPLES)
    table = Table(title="Label Distribution")
    table.add_column("Label", style="cyan")
    table.add_column("Count", justify="right", style="green")
    for label, count in label_counts.items():
        table.add_row(label, str(count))
    console.print(table)


def validate_classifier() -> None:
    """Run the heuristic filter on labeled samples and report accuracy."""
    from classifiers.heuristic_filter import HeuristicFilter

    samples_path = LABELED_SAMPLES_DIR / "labeled_examples.json"
    if not samples_path.exists():
        console.print("[red]No labeled samples found. Run without --validate first.[/]")
        return

    with open(samples_path, "r", encoding="utf-8") as f:
        samples = json.load(f)

    heuristic = HeuristicFilter(threshold=0.3)

    table = Table(title="Heuristic Filter Validation")
    table.add_column("Expected", style="cyan")
    table.add_column("Passed?", style="yellow")
    table.add_column("Score", justify="right")
    table.add_column("Signals", style="dim")
    table.add_column("Correct?", style="bold")

    correct = 0
    total = 0

    for sample in samples:
        result = heuristic.evaluate(sample["text"])
        expected = sample["label"]

        # For Stage 1 (high recall): RETROSPECTIVE and AMBIGUOUS should pass
        should_pass = expected in ("RETROSPECTIVE", "AMBIGUOUS")
        is_correct = result.passed == should_pass

        if is_correct:
            correct += 1
        total += 1

        table.add_row(
            expected,
            "[green]PASS[/]" if result.passed else "[red]REJECT[/]",
            f"{result.score:.2f}",
            ", ".join(result.signals[:3]) + ("..." if len(result.signals) > 3 else ""),
            "[green]YES[/]" if is_correct else "[red]NO[/]",
        )

    console.print(table)
    accuracy = correct / total * 100 if total > 0 else 0
    console.print(
        f"\n[bold]Accuracy: {correct}/{total} ({accuracy:.0f}%)[/]"
    )
    console.print(
        "[dim]Note: For Stage 1, RETROSPECTIVE and AMBIGUOUS should pass; "
        "NOT_RETROSPECTIVE should be rejected.[/]"
    )


def main() -> None:
    """Run the seed labels helper."""
    parser = argparse.ArgumentParser(description="Echoes — Seed Labels Helper")
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate the heuristic classifier on labeled samples",
    )
    args = parser.parse_args()

    setup_logging()

    if args.validate:
        validate_classifier()
    else:
        create_labeled_samples()


if __name__ == "__main__":
    main()
