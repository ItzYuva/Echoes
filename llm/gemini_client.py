"""
Echoes Data Pipeline — Gemini Flash LLM Client

Implements the BaseLLMClient interface using Google's Gemini 2.0 Flash model.
Handles classification and metadata extraction with:
  - Async concurrency via asyncio semaphore
  - Exponential backoff retries via tenacity
  - Response parsing and validation
  - Cost-efficient batching
"""

from __future__ import annotations

import asyncio
import json
import re
from typing import Dict, List, Optional

import google.generativeai as genai
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from config.logging_config import get_logger
from config.settings import GeminiSettings
from llm.base_client import BaseLLMClient
from storage.models import (
    ClassificationResult,
    DecisionType,
    OutcomeSentiment,
    StoryMetadata,
)

logger = get_logger(__name__)

# ──────────────────────────────────────────────
# Prompt templates
# ──────────────────────────────────────────────

CLASSIFICATION_PROMPT = """You are classifying text for a database that only stores retrospective human reflections — stories told in hindsight, after the dust has settled.

Classify the following text into exactly one category:

RETROSPECTIVE — The author is reflecting on a past decision, experience, or turning point from a temporal distance. They know how things turned out. There is hindsight wisdom, regret, gratitude, or lessons learned. The emotional processing has happened.

NOT_RETROSPECTIVE — The author is in the middle of something, seeking advice, reacting in real time, or describing something without meaningful reflection on how it played out.

AMBIGUOUS — Contains some retrospective elements but is primarily forward-looking, advice-seeking, or lacks clear temporal distance.

Respond with ONLY the category label, nothing else.

Text to classify:
\"\"\"
{text}
\"\"\"
"""

METADATA_PROMPT = """Analyze this retrospective story and extract the following metadata. Respond in JSON only, no other text.

{{
  "decision_type": one of ["career", "relationship", "relocation", "education", "health", "financial", "family", "lifestyle", "other"],
  "decision_subcategory": a more specific label (e.g., "leaving a job", "ending a marriage", "moving abroad"),
  "outcome_sentiment": one of ["positive", "negative", "mixed", "neutral"],
  "time_elapsed": best estimate in months (integer). Use -1 if unclear,
  "emotional_richness": 1-10 score (10 = deeply personal, vulnerable, specific emotions named; 1 = vague, generic, surface-level),
  "outcome_clarity": true if the story clearly states what happened as a result, false if outcome is vague or unresolved,
  "key_themes": array of 2-5 theme tags (e.g., ["regret", "growth", "fear of unknown", "financial risk", "relationship sacrifice"]),
  "hindsight_insight": one sentence summary of the core lesson or realization (in the author's implicit voice, not prescriptive)
}}

Story:
\"\"\"
{text}
\"\"\"
"""


class GeminiClient(BaseLLMClient):
    """Gemini 2.0 Flash implementation of the LLM client.

    Uses Google's Generative AI SDK for classification and metadata
    extraction. Supports concurrent async requests with semaphore-based
    rate limiting.

    Args:
        settings: Gemini API configuration.
    """

    def __init__(self, settings: GeminiSettings) -> None:
        self.settings = settings
        genai.configure(api_key=settings.api_key)
        self.model = genai.GenerativeModel(settings.classification_model)
        self._semaphore = asyncio.Semaphore(settings.max_concurrency)
        logger.info(
            "Gemini client initialized (model=%s, concurrency=%d)",
            settings.classification_model,
            settings.max_concurrency,
        )

    # ── Classification ──

    @retry(
        retry=retry_if_exception_type(Exception),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        reraise=True,
    )
    async def _call_gemini(self, prompt: str) -> str:
        """Make a single Gemini API call with retry logic.

        Args:
            prompt: The formatted prompt to send.

        Returns:
            The raw text response from the model.
        """
        async with self._semaphore:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.model.generate_content(
                    prompt,
                    generation_config=genai.GenerationConfig(
                        temperature=0.0,
                    ),
                ),
            )
            return response.text.strip()

    async def classify(self, text: str) -> tuple[ClassificationResult, str]:
        """Classify a single text as retrospective or not.

        Args:
            text: The text to classify.

        Returns:
            Tuple of (ClassificationResult, raw_response).
        """
        prompt = CLASSIFICATION_PROMPT.format(text=text[:4000])  # truncate for safety
        try:
            raw = await self._call_gemini(prompt)
            result = self._parse_classification(raw)
            return result, raw
        except Exception as e:
            logger.error("Classification failed: %s", e)
            return ClassificationResult.AMBIGUOUS, f"ERROR: {e}"

    async def classify_batch(
        self, texts: list[str]
    ) -> list[tuple[ClassificationResult, str]]:
        """Classify multiple texts concurrently.

        Uses asyncio.gather with the semaphore limiting concurrency
        to self.settings.max_concurrency simultaneous requests.

        Args:
            texts: List of texts to classify.

        Returns:
            List of (ClassificationResult, raw_response) tuples.
        """
        tasks = [self.classify(text) for text in texts]
        return await asyncio.gather(*tasks)

    @staticmethod
    def _parse_classification(raw: str) -> ClassificationResult:
        """Parse the raw LLM response into a ClassificationResult.

        Args:
            raw: Raw text from the model (should be a single label).

        Returns:
            The parsed ClassificationResult.
        """
        cleaned = raw.strip().upper().replace(" ", "_")

        if "RETROSPECTIVE" in cleaned and "NOT" not in cleaned:
            return ClassificationResult.RETROSPECTIVE
        elif "NOT_RETROSPECTIVE" in cleaned or "NOT RETROSPECTIVE" in cleaned:
            return ClassificationResult.NOT_RETROSPECTIVE
        elif "AMBIGUOUS" in cleaned:
            return ClassificationResult.AMBIGUOUS
        else:
            logger.warning("Unexpected classification response: '%s'", raw)
            return ClassificationResult.AMBIGUOUS

    # ── Metadata Extraction ──

    async def extract_metadata(self, text: str) -> Optional[StoryMetadata]:
        """Extract structured metadata from a retrospective story.

        Args:
            text: The story text.

        Returns:
            StoryMetadata if parsing succeeds, None otherwise.
        """
        prompt = METADATA_PROMPT.format(text=text[:6000])
        try:
            raw = await self._call_gemini(prompt)
            return self._parse_metadata(raw)
        except Exception as e:
            logger.error("Metadata extraction failed: %s", e)
            return None

    async def extract_metadata_batch(
        self, texts: list[str]
    ) -> list[Optional[StoryMetadata]]:
        """Extract metadata from multiple stories concurrently.

        Args:
            texts: List of story texts.

        Returns:
            List of StoryMetadata (or None for failures).
        """
        tasks = [self.extract_metadata(text) for text in texts]
        return await asyncio.gather(*tasks)

    @staticmethod
    def _parse_metadata(raw: str) -> Optional[StoryMetadata]:
        """Parse the raw JSON response into a StoryMetadata object.

        Handles common LLM JSON formatting issues (markdown fences, etc.).

        Args:
            raw: Raw text from the model (should be JSON).

        Returns:
            StoryMetadata or None if parsing fails.
        """
        # Strip markdown code fences if present
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            # Remove ```json and trailing ```
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as e:
            logger.warning("Failed to parse metadata JSON: %s | raw: %s", e, raw[:200])
            return None

        # Map to our enums with safe fallbacks
        try:
            decision_type = DecisionType(data.get("decision_type", "other"))
        except ValueError:
            decision_type = DecisionType.OTHER

        try:
            outcome_sentiment = OutcomeSentiment(
                data.get("outcome_sentiment", "neutral")
            )
        except ValueError:
            outcome_sentiment = OutcomeSentiment.NEUTRAL

        return StoryMetadata(
            decision_type=decision_type,
            decision_subcategory=data.get("decision_subcategory", ""),
            outcome_sentiment=outcome_sentiment,
            time_elapsed_months=int(data.get("time_elapsed", -1)),
            emotional_richness=max(1, min(10, int(data.get("emotional_richness", 5)))),
            outcome_clarity=bool(data.get("outcome_clarity", False)),
            key_themes=data.get("key_themes", [])[:5],
            hindsight_insight=data.get("hindsight_insight", ""),
        )

    # -- Phase 2: Intake Conversation -----------------------------------------

    @retry(
        retry=retry_if_exception_type(Exception),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        reraise=True,
    )
    async def intake_turn(
        self,
        system_prompt: str,
        conversation_history: List[Dict[str, str]],
    ) -> str:
        """Send a single turn of the intake conversation.

        Converts our role-based history to Gemini's content format
        and returns the model's next response.

        Args:
            system_prompt: The system prompt defining the intake persona.
            conversation_history: List of {"role": ..., "content": ...} dicts.

        Returns:
            The LLM's next message text.
        """
        async with self._semaphore:
            # Build a dedicated model with the system instruction baked in
            intake_model = genai.GenerativeModel(
                model_name=self.settings.classification_model,
                system_instruction=system_prompt,
            )

            # Convert conversation history to Gemini content format
            gemini_history = []
            for msg in conversation_history:
                role = "model" if msg["role"] == "assistant" else "user"
                gemini_history.append({"role": role, "parts": [msg["content"]]})

            loop = asyncio.get_event_loop()

            if gemini_history:
                # Multi-turn: start a chat with history and send empty-ish prompt
                # The last message in history should be from the user
                chat_history = gemini_history[:-1] if gemini_history else []
                last_message = gemini_history[-1]["parts"][0] if gemini_history else ""

                def _chat_turn():
                    chat = intake_model.start_chat(history=chat_history)
                    response = chat.send_message(
                        last_message,
                        generation_config=genai.GenerationConfig(
                            temperature=0.7,
                        ),
                    )
                    return response.text.strip()

                result = await loop.run_in_executor(None, _chat_turn)
            else:
                # First turn: no history yet, just ask the model to begin
                def _first_turn():
                    response = intake_model.generate_content(
                        "Begin the intake conversation with a warm greeting and your first question.",
                        generation_config=genai.GenerationConfig(
                            temperature=0.7,
                        ),
                    )
                    return response.text.strip()

                result = await loop.run_in_executor(None, _first_turn)

            logger.debug("Intake turn response: %s...", result[:100])
            return result

    # -- Phase 3: RAG Core ---------------------------------------------------

    QUERY_ANALYSIS_PROMPT = """Analyze this decision description and extract structured information. Respond in JSON only, no other text.

{{
  "decision_type": one of ["career", "relationship", "relocation", "education", "health", "financial", "family", "lifestyle", "other"],
  "decision_subcategory": specific label (e.g., "leaving stable job for freelance"),
  "core_tension": one sentence describing the fundamental tradeoff,
  "emotional_state": array of 2-4 emotions the person seems to be feeling,
  "stakes": one of ["low", "moderate", "high", "life-altering"],
  "key_factors": array of 3-5 specific factors mentioned,
  "what_would_help": one sentence describing what kind of retrospective stories would be most valuable
}}

Decision description:
\"\"\"
{user_text}
\"\"\"
"""

    SYNTHETIC_STORY_PROMPT = """Generate a realistic retrospective reflection written by a real person looking back on a major life decision. The story should read like a Reddit post or personal essay — not polished, not motivational, just honest.

Requirements:
- Decision type: {decision_type}
- Specific scenario: {scenario}
- Time elapsed since decision: {time_elapsed}
- Outcome: {outcome_tone} (but nuanced — even positive outcomes should have costs, and negative outcomes should have silver linings)
- Length: 200-500 words
- Written in first person
- Include: the fear/excitement at the time, specific details that make it feel real, what actually happened, what they know now that they didn't then
- Do NOT include: motivational quotes, generic advice, bullet points, section headers
- Tone: honest, specific, slightly vulnerable — like telling a close friend over coffee

Write ONLY the story text, no preamble or metadata.
"""

    @retry(
        retry=retry_if_exception_type(Exception),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        reraise=True,
    )
    async def analyze_query(self, user_text: str) -> dict:
        """Analyze a decision query and return structured JSON."""
        prompt = self.QUERY_ANALYSIS_PROMPT.format(user_text=user_text)
        raw = await self._call_gemini(prompt)

        # Defensive JSON parsing
        try:
            # Strip markdown fences
            cleaned = raw
            if "```" in cleaned:
                lines = cleaned.split("\n")
                lines = [l for l in lines if not l.strip().startswith("```")]
                cleaned = "\n".join(lines)

            # Fix trailing commas
            import re
            cleaned = re.sub(r",\s*([}\]])", r"\1", cleaned)

            return json.loads(cleaned)
        except json.JSONDecodeError:
            # Try to extract JSON from response
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if match:
                try:
                    extracted = re.sub(r",\s*([}\]])", r"\1", match.group())
                    return json.loads(extracted)
                except json.JSONDecodeError:
                    pass
            logger.warning("Could not parse query analysis: %s", raw[:200])
            return {"decision_type": "other", "what_would_help": ""}

    @retry(
        retry=retry_if_exception_type(Exception),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        reraise=True,
    )
    async def present_stories(self, prompt: str, stream: bool = False) -> str:
        """Present stories using the presentation prompt.

        Uses higher temperature for more natural, varied writing.
        """
        async with self._semaphore:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.model.generate_content(
                    prompt,
                    generation_config=genai.GenerationConfig(
                        temperature=0.7,
                        max_output_tokens=4096,
                    ),
                ),
            )
            return response.text.strip()

    @retry(
        retry=retry_if_exception_type(Exception),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        reraise=True,
    )
    async def generate_synthetic_story(
        self,
        decision_type: str,
        scenario: str,
        time_elapsed: str,
        outcome_tone: str,
    ) -> str:
        """Generate a realistic retrospective story for seeding."""
        prompt = self.SYNTHETIC_STORY_PROMPT.format(
            decision_type=decision_type,
            scenario=scenario,
            time_elapsed=time_elapsed,
            outcome_tone=outcome_tone,
        )
        async with self._semaphore:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.model.generate_content(
                    prompt,
                    generation_config=genai.GenerationConfig(
                        temperature=0.9,  # High creativity for varied stories
                        max_output_tokens=1024,
                    ),
                ),
            )
            return response.text.strip()
