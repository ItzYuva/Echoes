"""
Tests for the intake conversation manager.

Uses a mock LLM client to simulate the multi-turn intake flow.
"""

import pytest

from personality.intake.conversation_manager import ConversationManager
from personality.intake.intake_config import IntakeConfig


class MockLLMClient:
    """Mock LLM that returns scripted responses for testing."""

    def __init__(self, responses: list[str]):
        self._responses = responses
        self._call_count = 0

    async def intake_turn(self, system_prompt: str, history: list) -> str:
        if self._call_count < len(self._responses):
            response = self._responses[self._call_count]
            self._call_count += 1
            return response
        return "I've run out of scripted responses."


# A clean values vector output from the LLM
CLEAN_VECTOR_OUTPUT = """Thanks for sharing all that. I have a good sense of where you're coming from.

[VALUES_VECTOR]
{
  "risk_tolerance": 0.78,
  "change_orientation": 0.85,
  "security_vs_growth": 0.62,
  "action_bias": 0.50,
  "social_weight": 0.35,
  "time_horizon": 0.60,
  "loss_sensitivity": 0.73,
  "ambiguity_tolerance": 0.52,
  "confidence_notes": {
    "risk_tolerance": "Strong signal - explicitly said uncertainty excites them",
    "social_weight": "Moderate signal - mentioned family once"
  }
}"""


class TestConversationManager:
    """Test the conversation manager flow."""

    @pytest.mark.asyncio
    async def test_happy_path_6_turns(self):
        """Full intake: 6 questions, clean vector output."""
        responses = [
            # Opening (start)
            "Hey there. Let me ask you something...",
            # Questions 1-5
            "That's interesting. When you think about decisions...",
            "I hear you. What about when you're uncertain...",
            "Makes sense. How do you feel about change...",
            "Got it. When you picture the future...",
            "One more question. What weighs more for you...",
            # Final turn with vector
            CLEAN_VECTOR_OUTPUT,
        ]

        mock = MockLLMClient(responses)
        config = IntakeConfig(max_turns=8, force_close_turn=8)
        manager = ConversationManager(llm_client=mock, config=config)

        # Start
        opening = await manager.start()
        assert "ask you" in opening.lower() or len(opening) > 10

        # Simulate 6 user responses
        for i in range(6):
            response, is_complete = await manager.respond(f"User answer {i+1}")
            if is_complete:
                break

        assert manager.is_complete
        assert manager.values_vector is not None
        assert manager.values_vector.risk_tolerance == pytest.approx(0.78)
        assert manager.values_vector.change_orientation == pytest.approx(0.85)
        assert manager.turn_count == 6

    @pytest.mark.asyncio
    async def test_short_intake_5_turns(self):
        """Rich answers lead to 5-turn intake."""
        responses = [
            "Welcome! First question...",
            "Wow, that's very insightful...",
            "I'm getting a clear picture...",
            "That confirms what I thought...",
            "Last one...",
            CLEAN_VECTOR_OUTPUT,
        ]

        mock = MockLLMClient(responses)
        manager = ConversationManager(llm_client=mock)

        await manager.start()
        for i in range(5):
            _, complete = await manager.respond(f"Rich detailed answer {i+1}")
            if complete:
                break

        assert manager.is_complete
        assert manager.values_vector is not None

    @pytest.mark.asyncio
    async def test_already_complete(self):
        """Responding after completion returns early."""
        responses = [
            "Hello!",
            CLEAN_VECTOR_OUTPUT,
        ]

        mock = MockLLMClient(responses)
        manager = ConversationManager(llm_client=mock)

        await manager.start()
        await manager.respond("My answer")

        assert manager.is_complete
        response, complete = await manager.respond("More input")
        assert complete
        assert "already complete" in response.lower()

    @pytest.mark.asyncio
    async def test_transcript_recorded(self):
        """Conversation transcript is properly recorded."""
        responses = [
            "Welcome!",
            CLEAN_VECTOR_OUTPUT,
        ]

        mock = MockLLMClient(responses)
        manager = ConversationManager(llm_client=mock)

        await manager.start()
        assert len(manager.transcript) == 1  # opening message

        await manager.respond("My answer")
        transcript = manager.transcript

        assert any(msg["role"] == "assistant" for msg in transcript)
        assert any(msg["role"] == "user" for msg in transcript)

    @pytest.mark.asyncio
    async def test_duration_tracking(self):
        """Duration is tracked from start."""
        responses = [
            "Hello!",
            CLEAN_VECTOR_OUTPUT,
        ]

        mock = MockLLMClient(responses)
        manager = ConversationManager(llm_client=mock)

        assert manager.duration_seconds == 0
        await manager.start()
        assert manager.duration_seconds >= 0  # at least 0 seconds

    @pytest.mark.asyncio
    async def test_default_vector_on_total_failure(self):
        """If all parse retries fail, use default vector."""
        bad_vector = """Thanks for everything.

[VALUES_VECTOR]
this is not valid json at all"""

        responses = [
            "Hello!",
            bad_vector,  # first attempt
            bad_vector,  # retry 1
            bad_vector,  # retry 2
        ]

        mock = MockLLMClient(responses)
        config = IntakeConfig(max_parse_retries=2)
        manager = ConversationManager(llm_client=mock, config=config)

        await manager.start()
        await manager.respond("My answer")

        # Should still complete with defaults
        assert manager.is_complete
        assert manager.values_vector is not None
        assert manager.values_vector.risk_tolerance == 0.5  # default
