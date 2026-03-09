"""
Echoes Phase 3 -- Generation Matrix (Component 0)

Defines the scenario combinations for synthetic story generation.
Strategically covers all decision types with varied outcomes and time horizons.
"""

from __future__ import annotations

from typing import List, NamedTuple


class StorySpec(NamedTuple):
    """Specification for a single synthetic story."""
    decision_type: str
    scenario: str
    outcome_tone: str
    time_elapsed: str


# ~80 strategically chosen combinations
GENERATION_MATRIX: List[StorySpec] = [
    # ── Career (24 stories) ──────────────────────────────────────────
    StorySpec("career", "left a stable corporate job to start a business", "positive", "5 years"),
    StorySpec("career", "left a stable corporate job to start a business", "negative", "3 years"),
    StorySpec("career", "left a stable corporate job to start a business", "mixed", "2 years"),
    StorySpec("career", "turned down a promotion to protect work-life balance", "positive", "2 years"),
    StorySpec("career", "turned down a promotion to protect work-life balance", "negative", "5 years"),
    StorySpec("career", "switched careers entirely in their 30s", "positive", "5 years"),
    StorySpec("career", "switched careers entirely in their 30s", "mixed", "3 years"),
    StorySpec("career", "switched careers entirely in their 40s", "negative", "2 years"),
    StorySpec("career", "stayed at a job they hated for the money", "negative", "10 years"),
    StorySpec("career", "stayed at a job they hated for the money", "mixed", "5 years"),
    StorySpec("career", "took a massive pay cut for meaningful work", "positive", "3 years"),
    StorySpec("career", "took a massive pay cut for meaningful work", "negative", "2 years"),
    StorySpec("career", "moved for a job, leaving their support network", "positive", "5 years"),
    StorySpec("career", "moved for a job, leaving their support network", "mixed", "3 years"),
    StorySpec("career", "quit without a plan", "positive", "2 years"),
    StorySpec("career", "quit without a plan", "negative", "6 months"),
    StorySpec("career", "chose a safe career over a passionate one", "negative", "10 years"),
    StorySpec("career", "chose a safe career over a passionate one", "mixed", "5 years"),
    StorySpec("career", "turned down a dream job because of family obligations", "mixed", "3 years"),
    StorySpec("career", "went back to their old career after trying something new", "positive", "2 years"),
    StorySpec("career", "started freelancing after being laid off", "positive", "3 years"),
    StorySpec("career", "started freelancing after being laid off", "mixed", "1 year"),
    StorySpec("career", "accepted a leadership role they didn't feel ready for", "positive", "5 years"),
    StorySpec("career", "accepted a leadership role they didn't feel ready for", "negative", "2 years"),

    # ── Relationship (18 stories) ────────────────────────────────────
    StorySpec("relationship", "ended a long-term relationship that looked perfect on paper", "positive", "3 years"),
    StorySpec("relationship", "ended a long-term relationship that looked perfect on paper", "mixed", "5 years"),
    StorySpec("relationship", "stayed in a struggling marriage and worked on it", "positive", "8 years"),
    StorySpec("relationship", "stayed in a struggling marriage and worked on it", "negative", "5 years"),
    StorySpec("relationship", "chose career over a relationship", "positive", "5 years"),
    StorySpec("relationship", "chose career over a relationship", "negative", "3 years"),
    StorySpec("relationship", "gave someone a second chance after betrayal", "positive", "3 years"),
    StorySpec("relationship", "gave someone a second chance after betrayal", "negative", "5 years"),
    StorySpec("relationship", "married someone everyone warned them about", "positive", "5 years"),
    StorySpec("relationship", "married someone everyone warned them about", "negative", "3 years"),
    StorySpec("relationship", "left someone they still loved", "positive", "3 years"),
    StorySpec("relationship", "left someone they still loved", "mixed", "1 year"),
    StorySpec("relationship", "chose to be single and focus on themselves", "positive", "3 years"),
    StorySpec("relationship", "chose to be single and focus on themselves", "mixed", "5 years"),
    StorySpec("relationship", "moved in with a partner after only a few months", "positive", "3 years"),
    StorySpec("relationship", "moved in with a partner after only a few months", "negative", "1 year"),
    StorySpec("relationship", "reconciled with an estranged family member", "positive", "5 years"),
    StorySpec("relationship", "reconciled with an estranged family member", "mixed", "3 years"),

    # ── Relocation (10 stories) ──────────────────────────────────────
    StorySpec("relocation", "moved to a new country alone", "positive", "3 years"),
    StorySpec("relocation", "moved to a new country alone", "mixed", "7 years"),
    StorySpec("relocation", "moved back to their hometown after years away", "positive", "3 years"),
    StorySpec("relocation", "moved back to their hometown after years away", "negative", "1 year"),
    StorySpec("relocation", "chose to stay when everyone was leaving", "positive", "5 years"),
    StorySpec("relocation", "chose to stay when everyone was leaving", "mixed", "3 years"),
    StorySpec("relocation", "followed a partner to a new city", "positive", "5 years"),
    StorySpec("relocation", "followed a partner to a new city", "negative", "3 years"),
    StorySpec("relocation", "moved for cheaper cost of living", "positive", "3 years"),
    StorySpec("relocation", "moved for cheaper cost of living", "mixed", "1 year"),

    # ── Education (8 stories) ────────────────────────────────────────
    StorySpec("education", "dropped out of college to pursue something else", "positive", "5 years"),
    StorySpec("education", "dropped out of college to pursue something else", "negative", "3 years"),
    StorySpec("education", "went back to school at 35+", "positive", "5 years"),
    StorySpec("education", "went back to school at 35+", "mixed", "3 years"),
    StorySpec("education", "chose a practical degree over their passion", "negative", "10 years"),
    StorySpec("education", "chose a practical degree over their passion", "mixed", "5 years"),
    StorySpec("education", "took on massive student debt for a dream school", "positive", "10 years"),
    StorySpec("education", "took on massive student debt for a dream school", "negative", "5 years"),

    # ── Health (6 stories) ───────────────────────────────────────────
    StorySpec("health", "finally addressed mental health after years of ignoring it", "positive", "3 years"),
    StorySpec("health", "finally addressed mental health after years of ignoring it", "mixed", "1 year"),
    StorySpec("health", "made a radical lifestyle change after a health scare", "positive", "5 years"),
    StorySpec("health", "made a radical lifestyle change after a health scare", "mixed", "3 years"),
    StorySpec("health", "chose an unconventional treatment path", "positive", "3 years"),
    StorySpec("health", "chose an unconventional treatment path", "mixed", "5 years"),

    # ── Financial (10 stories) ───────────────────────────────────────
    StorySpec("financial", "invested everything in one bet", "positive", "5 years"),
    StorySpec("financial", "invested everything in one bet", "negative", "2 years"),
    StorySpec("financial", "chose financial security over a dream", "negative", "10 years"),
    StorySpec("financial", "chose financial security over a dream", "mixed", "5 years"),
    StorySpec("financial", "walked away from an inheritance with strings attached", "positive", "5 years"),
    StorySpec("financial", "walked away from an inheritance with strings attached", "mixed", "3 years"),
    StorySpec("financial", "took on major debt for an opportunity", "positive", "5 years"),
    StorySpec("financial", "took on major debt for an opportunity", "negative", "2 years"),
    StorySpec("financial", "downsized everything to eliminate debt", "positive", "3 years"),
    StorySpec("financial", "downsized everything to eliminate debt", "mixed", "5 years"),
]
