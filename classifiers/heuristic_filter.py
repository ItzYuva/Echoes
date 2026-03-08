"""
Echoes Data Pipeline — Heuristic Filter (Classifier Stage 1)

Fast, rule-based filter that checks for temporal markers, verb tense
patterns, and outcome language to identify *likely* retrospective content.

Design philosophy: HIGH RECALL, LOW PRECISION.
  - It's okay to let borderline cases through (Stage 2 LLM will catch them)
  - But we want to filter out obvious non-retrospective content to save API costs
  - Expected filter rate: ~60-70% of raw content rejected here for free

Each heuristic contributes a weighted score. If the total exceeds the
configured threshold, the text passes to Stage 2.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from config.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class HeuristicResult:
    """Result of heuristic filtering on a single text.

    Attributes:
        passed: Whether the text passed the heuristic threshold.
        score: Aggregate confidence score (0.0 - 1.0).
        signals: List of human-readable signals that fired.
    """
    passed: bool
    score: float
    signals: list[str] = field(default_factory=list)


# Written-out number alternatives for regex patterns
_WRITTEN_NUMS = r"(?:\d+|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|fifteen|twenty|thirty|several|a\s+few|many|some)"

# ──────────────────────────────────────────────
# Signal definitions
# ──────────────────────────────────────────────

# Temporal markers indicating hindsight
TEMPORAL_MARKERS = [
    (rf"\b{_WRITTEN_NUMS}\s*years?\s*(?:ago|later)\b", 0.15, "temporal: N years ago/later"),
    (rf"\b{_WRITTEN_NUMS}\s*months?\s*(?:ago|later)\b", 0.12, "temporal: N months ago/later"),
    (r"\blooking\s+back\b", 0.18, "temporal: looking back"),
    (r"\bin\s+hindsight\b", 0.20, "temporal: in hindsight"),
    (r"\bin\s+retrospect\b", 0.20, "temporal: in retrospect"),
    (r"\bif\s+i\s+could\s+go\s+back\b", 0.15, "temporal: if I could go back"),
    (r"\bback\s+then\b", 0.10, "temporal: back then"),
    (r"\bat\s+the\s+time\b", 0.08, "temporal: at the time"),
    (r"\bnow\s+(i|that\s+i)\s+(realize|understand|know|see)\b", 0.15, "temporal: now I realize"),
    (r"\bwhen\s+i\s+was\b", 0.07, "temporal: when I was"),
    (rf"\b(?:it['']?s\s+been|it\s+has\s+been)\s+{_WRITTEN_NUMS}\b", 0.12, "temporal: it's been N..."),
]

# Outcome and resolution language
OUTCOME_MARKERS = [
    (r"\bturned\s+out\b", 0.15, "outcome: turned out"),
    (r"\bended\s+up\b", 0.12, "outcome: ended up"),
    (r"\bin\s+the\s+end\b", 0.12, "outcome: in the end"),
    (r"\bultimately\b", 0.10, "outcome: ultimately"),
    (r"\b(best|worst)\s+decision\b", 0.18, "outcome: best/worst decision"),
    (r"\bglad\s+i\s+(did|didn['']?t)\b", 0.15, "outcome: glad I did/didn't"),
    (r"\bi\s+(don['']?t\s+)?regret\b", 0.15, "outcome: regret"),
    (r"\blesson\s+learned\b", 0.15, "outcome: lesson learned"),
    (r"\bi\s+wish\s+i\s+had\b", 0.15, "outcome: I wish I had"),
    (r"\bshould\s+have\b", 0.08, "outcome: should have"),
    (r"\bcould\s+have\b", 0.06, "outcome: could have"),
    (r"\bwas\s+worth\s+it\b", 0.15, "outcome: was worth it"),
    (r"\bchanged\s+my\s+life\b", 0.12, "outcome: changed my life"),
]

# Update/follow-up markers (common in Reddit advice subs)
UPDATE_MARKERS = [
    (r"^update\s*[:\-–—]", 0.25, "update: starts with 'Update:'"),
    (r"\bupdate\s*[:\-–—]", 0.20, "update: contains 'Update:'"),
    (r"\bfollow[\s-]?up\b", 0.15, "update: follow-up"),
    (r"\bfor\s+anyone\s+wondering\b", 0.15, "update: for anyone wondering"),
    (r"\bhere['']?s\s+what\s+(actually\s+)?happened\b", 0.18, "update: here's what happened"),
]

# Reflection/wisdom language
REFLECTION_MARKERS = [
    (r"\bi\s+(finally\s+)?(realize[ds]?|understood|learned)\b", 0.10, "reflection: realized/learned"),
    (r"\bwisdom\b", 0.08, "reflection: wisdom"),
    (r"\bgrowth\b", 0.06, "reflection: growth"),
    (r"\bthe\s+signs\s+were\s+there\b", 0.12, "reflection: signs were there"),
    (r"\bi\s+was\s+(wrong|right|naive|foolish|blind)\b", 0.12, "reflection: self-assessment"),
    (r"\bwhat\s+i['']?ve\s+learned\b", 0.15, "reflection: what I've learned"),
]

# Negative signals (likely NOT retrospective — these REDUCE the score)
NEGATIVE_MARKERS = [
    (r"\bwhat\s+should\s+i\s+do\b", -0.20, "negative: asking for advice"),
    (r"\bshould\s+i\b", -0.15, "negative: should I?"),
    (r"\bhelp\s+me\b", -0.12, "negative: help me"),
    (r"\bany\s+(advice|suggestions|tips)\b", -0.15, "negative: seeking advice"),
    (r"\bjust\s+(got|found|heard|learned)\b", -0.10, "negative: just happened"),
    (r"\bright\s+now\b", -0.08, "negative: right now"),
    (r"\bwhat\s+do\s+(you|i)\s+(think|do)\b", -0.12, "negative: asking opinion"),
    (r"\bi['']?m\s+(thinking|considering|planning)\s+(about|of|to)\b", -0.12, "negative: planning"),
]


class HeuristicFilter:
    """Rule-based fast filter for identifying likely retrospective content.

    Scans text for temporal markers, outcome language, update patterns,
    and reflection signals. Also checks for negative signals (advice-seeking,
    in-the-moment language) that reduce the score.

    This is Stage 1 of the two-stage classifier. Designed for high recall:
    letting borderline content through is acceptable; false negatives are not.

    Args:
        threshold: Minimum aggregate score to pass (default: 0.3).
    """

    def __init__(self, threshold: float = 0.3) -> None:
        self.threshold = threshold
        # Compile all patterns once
        self._all_signals = []
        for patterns in [
            TEMPORAL_MARKERS, OUTCOME_MARKERS, UPDATE_MARKERS,
            REFLECTION_MARKERS, NEGATIVE_MARKERS,
        ]:
            for pattern, weight, description in patterns:
                self._all_signals.append(
                    (re.compile(pattern, re.IGNORECASE | re.MULTILINE), weight, description)
                )

    def evaluate(self, text: str) -> HeuristicResult:
        """Evaluate a text for retrospective signals.

        Runs all heuristic patterns against the text and computes an
        aggregate score. Negative markers reduce the score.

        Args:
            text: The text to evaluate.

        Returns:
            HeuristicResult with pass/fail, score, and fired signals.
        """
        score = 0.0
        signals: list[str] = []

        for pattern, weight, description in self._all_signals:
            if pattern.search(text):
                score += weight
                signals.append(f"{description} ({weight:+.2f})")

        # Clamp score between 0 and 1
        score = max(0.0, min(1.0, score))

        passed = score >= self.threshold

        if passed:
            logger.debug(
                "Heuristic PASS (score=%.2f, signals=%d): %s",
                score, len(signals), text[:80],
            )
        else:
            logger.debug(
                "Heuristic REJECT (score=%.2f, signals=%d): %s",
                score, len(signals), text[:80],
            )

        return HeuristicResult(passed=passed, score=score, signals=signals)

    def batch_evaluate(self, texts: list[str]) -> list[HeuristicResult]:
        """Evaluate multiple texts.

        Args:
            texts: List of texts to evaluate.

        Returns:
            List of HeuristicResult instances.
        """
        return [self.evaluate(text) for text in texts]
