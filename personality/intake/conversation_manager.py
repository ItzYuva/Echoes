"""
Echoes Phase 2 -- Conversation Manager

Orchestrates the multi-turn intake conversation between the user
and the LLM. Manages conversation history, turn counting, force-close
logic, and values vector extraction.
"""

from __future__ import annotations

import time
from typing import Dict, List, Optional, Tuple

from config.logging_config import get_logger
from personality.intake.intake_config import IntakeConfig
from personality.intake.system_prompts import FORCE_CLOSE_PROMPT, INTAKE_SYSTEM_PROMPT
from personality.intake.vector_parser import has_values_vector, parse_values_vector
from personality.models.values_vector import ValuesVector

logger = get_logger(__name__)


class ConversationManager:
    """Manages the intake conversation lifecycle.

    Tracks conversation history, enforces turn limits, and extracts
    the values vector when the LLM signals completion.

    Args:
        llm_client: Any object with an `intake_turn` method.
        config: Intake configuration (turn limits, retry settings).
    """

    def __init__(self, llm_client: object, config: Optional[IntakeConfig] = None):
        self.llm = llm_client
        self.config = config or IntakeConfig()
        self.history: List[Dict[str, str]] = []
        self.system_prompt = INTAKE_SYSTEM_PROMPT
        self._start_time: Optional[float] = None
        self._turn_count = 0
        self._completed = False
        self._values_vector: Optional[ValuesVector] = None
        self._closing_message: Optional[str] = None

    @property
    def is_complete(self) -> bool:
        """Whether the intake conversation has finished."""
        return self._completed

    @property
    def values_vector(self) -> Optional[ValuesVector]:
        """The extracted values vector (None until intake completes)."""
        return self._values_vector

    @property
    def closing_message(self) -> Optional[str]:
        """The LLM's closing message to the user."""
        return self._closing_message

    @property
    def turn_count(self) -> int:
        """Number of Q&A exchanges so far."""
        return self._turn_count

    @property
    def duration_seconds(self) -> int:
        """Duration of the intake in seconds."""
        if self._start_time is None:
            return 0
        return int(time.time() - self._start_time)

    @property
    def transcript(self) -> List[Dict[str, str]]:
        """The full conversation transcript."""
        return self.history.copy()

    async def start(self) -> str:
        """Start the intake conversation.

        Sends the system prompt to the LLM and gets the first question.

        Returns:
            The LLM's opening message (greeting + first question).
        """
        self._start_time = time.time()
        logger.info("Starting intake conversation")

        response = await self.llm.intake_turn(self.system_prompt, [])
        self.history.append({"role": "assistant", "content": response})

        logger.info("Intake started with opening message (%d chars)", len(response))
        return response

    async def respond(self, user_input: str) -> Tuple[str, bool]:
        """Process a user response and get the next LLM message.

        Args:
            user_input: The user's response to the current question.

        Returns:
            Tuple of (llm_response, is_complete).
            is_complete is True when the LLM has output the values vector.
        """
        if self._completed:
            return "The intake is already complete.", True

        # Add user response to history
        self.history.append({"role": "user", "content": user_input})
        self._turn_count += 1

        # Check if we need to force-close
        force_close = self._turn_count >= self.config.force_close_turn

        # Build the message history for the LLM
        history = self.history.copy()
        if force_close:
            logger.info("Force-closing intake at turn %d", self._turn_count)
            history.append({"role": "user", "content": FORCE_CLOSE_PROMPT})

        # Get LLM response
        response = await self.llm.intake_turn(self.system_prompt, history)

        # Check for values vector in the response
        if has_values_vector(response):
            vector, closing = parse_values_vector(response)

            if vector is not None:
                self._values_vector = vector
                self._closing_message = closing or response.split("[VALUES_VECTOR]")[0].strip()
                self._completed = True
                # Only add the closing message to history (not the raw JSON)
                self.history.append({"role": "assistant", "content": self._closing_message})
                logger.info(
                    "Intake completed: %d turns, %ds duration",
                    self._turn_count,
                    self.duration_seconds,
                )
                return self._closing_message, True
            else:
                # Vector parsing failed -- retry
                return await self._retry_parse(response)
        else:
            # Normal conversation turn
            self.history.append({"role": "assistant", "content": response})
            return response, False

    async def _retry_parse(self, failed_response: str) -> Tuple[str, bool]:
        """Retry values vector extraction when parsing fails.

        Sends a nudge to the LLM asking it to output the vector
        in the correct format.

        Returns:
            Tuple of (llm_response, is_complete).
        """
        for attempt in range(self.config.max_parse_retries):
            logger.warning(
                "Values vector parse failed, retry %d/%d",
                attempt + 1,
                self.config.max_parse_retries,
            )

            nudge = (
                "Please provide the values vector in the specified JSON format. "
                "Output [VALUES_VECTOR] followed by the JSON object with all 8 "
                "dimensions (risk_tolerance, change_orientation, security_vs_growth, "
                "action_bias, social_weight, time_horizon, loss_sensitivity, "
                "ambiguity_tolerance) and confidence_notes."
            )

            history = self.history.copy()
            history.append({"role": "assistant", "content": failed_response})
            history.append({"role": "user", "content": nudge})

            response = await self.llm.intake_turn(self.system_prompt, history)

            if has_values_vector(response):
                vector, closing = parse_values_vector(response)
                if vector is not None:
                    self._values_vector = vector
                    self._closing_message = closing or self.history[-1].get("content", "")
                    self._completed = True
                    logger.info("Values vector extracted on retry %d", attempt + 1)
                    return self._closing_message, True

        # All retries failed -- create a default vector
        logger.error("All parse retries failed. Using default values vector.")
        self._values_vector = ValuesVector()  # all 0.5 defaults
        self._closing_message = failed_response.split("[VALUES_VECTOR]")[0].strip() if "[VALUES_VECTOR]" in failed_response else failed_response
        self._completed = True
        self.history.append({"role": "assistant", "content": self._closing_message})
        return self._closing_message, True
