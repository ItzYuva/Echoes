"""
Echoes Phase 3 -- Query Analyzer (Component 1)

Understands a user's decision query: what kind of decision it is,
what's at stake, what emotions are involved, and what kind of stories
would actually help.
"""

from __future__ import annotations

import json
import re
from typing import Optional

from config.logging_config import get_logger
from rag.query.models import QueryAnalysis

logger = get_logger(__name__)

QUERY_ANALYSIS_PROMPT = """Analyze this decision description and extract structured information. Respond in JSON only, no other text.

{{
  "decision_type": one of ["career", "relationship", "relocation", "education", "health", "financial", "family", "lifestyle", "other"],
  "decision_subcategory": specific label (e.g., "leaving stable job for freelance", "long-distance relationship decision"),
  "core_tension": one sentence describing the fundamental tradeoff (e.g., "security vs. autonomy", "love vs. career"),
  "emotional_state": array of 2-4 emotions the person seems to be feeling (e.g., ["fear", "excitement", "guilt"]),
  "stakes": one of ["low", "moderate", "high", "life-altering"],
  "key_factors": array of 3-5 specific factors mentioned (e.g., ["mortgage", "two kids", "desire for autonomy"]),
  "what_would_help": one sentence describing what kind of retrospective stories would be most valuable for this person
}}

Decision description:
\"\"\"
{user_text}
\"\"\"
"""


class QueryAnalyzer:
    """Analyzes user decision queries using Gemini Flash.

    Extracts structured information about the decision type, emotional state,
    stakes, and what kind of retrospective stories would help.

    Args:
        llm_client: A BaseLLMClient implementation (GeminiClient).
    """

    def __init__(self, llm_client) -> None:
        self.llm_client = llm_client

    async def analyze(self, user_text: str) -> QueryAnalysis:
        """Analyze a decision query and return structured analysis.

        Args:
            user_text: The user's description of their decision.

        Returns:
            QueryAnalysis with extracted structure.
        """
        if not user_text or len(user_text.strip()) < 10:
            logger.warning("Query too short: '%s'", user_text[:50])
            return QueryAnalysis(
                decision_type="other",
                what_would_help="Stories from people who faced a similar crossroads.",
            )

        try:
            raw = await self.llm_client.analyze_query(user_text)
            return self._parse_analysis(raw)
        except Exception as e:
            logger.error("Query analysis failed: %s", e)
            return self._fallback_analysis(user_text)

    def _parse_analysis(self, raw: dict) -> QueryAnalysis:
        """Parse raw LLM output into QueryAnalysis."""
        try:
            return QueryAnalysis(
                decision_type=raw.get("decision_type", "other"),
                decision_subcategory=raw.get("decision_subcategory", ""),
                core_tension=raw.get("core_tension", ""),
                emotional_state=raw.get("emotional_state", []),
                stakes=raw.get("stakes", "moderate"),
                key_factors=raw.get("key_factors", []),
                what_would_help=raw.get("what_would_help", ""),
            )
        except Exception as e:
            logger.error("Failed to parse analysis: %s", e)
            return QueryAnalysis()

    def _fallback_analysis(self, user_text: str) -> QueryAnalysis:
        """Simple keyword-based fallback when LLM fails."""
        text_lower = user_text.lower()

        # Detect decision type from keywords
        type_keywords = {
            "career": ["job", "career", "work", "salary", "boss", "company", "resign", "quit", "promotion", "freelance"],
            "relationship": ["partner", "marriage", "divorce", "boyfriend", "girlfriend", "spouse", "dating", "love"],
            "relocation": ["move", "relocate", "city", "country", "abroad", "hometown"],
            "education": ["school", "college", "degree", "university", "study", "student", "phd"],
            "health": ["health", "mental", "therapy", "diagnosis", "treatment", "doctor"],
            "financial": ["money", "invest", "debt", "savings", "buy", "afford", "loan"],
        }

        decision_type = "other"
        for dtype, keywords in type_keywords.items():
            if any(kw in text_lower for kw in keywords):
                decision_type = dtype
                break

        return QueryAnalysis(
            decision_type=decision_type,
            what_would_help=f"Stories from people who faced a similar {decision_type} decision.",
        )
