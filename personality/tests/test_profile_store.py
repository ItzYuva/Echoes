"""
Tests for PostgreSQL profile store operations.

These tests require a running PostgreSQL instance.
Skip if PostgreSQL is not available (CI-friendly).
"""

import json
import os
import uuid

import pytest

# Skip all tests in this module if PostgreSQL is not available
pytestmark = pytest.mark.skipif(
    os.getenv("POSTGRES_HOST") is None and os.getenv("SKIP_PG_TESTS", "1") == "1",
    reason="PostgreSQL not available (set POSTGRES_HOST or SKIP_PG_TESTS=0)",
)


@pytest.fixture
async def store():
    """Create a clean store instance for each test."""
    from personality.storage.postgres_store import PostgresProfileStore

    dsn = (
        f"postgresql://{os.getenv('POSTGRES_USER', 'echoes')}:"
        f"{os.getenv('POSTGRES_PASSWORD', 'echoes_dev')}@"
        f"{os.getenv('POSTGRES_HOST', 'localhost')}:"
        f"{os.getenv('POSTGRES_PORT', '5432')}/"
        f"{os.getenv('POSTGRES_DB', 'echoes')}"
    )

    store = PostgresProfileStore(dsn)
    await store.initialize()
    yield store
    await store.close()


SAMPLE_VALUES = {
    "risk_tolerance": 0.7,
    "change_orientation": 0.8,
    "security_vs_growth": 0.6,
    "action_bias": 0.5,
    "social_weight": 0.4,
    "time_horizon": 0.6,
    "loss_sensitivity": 0.7,
    "ambiguity_tolerance": 0.5,
    "confidence_notes": {"risk_tolerance": "Test note"},
}

SAMPLE_TRANSCRIPT = [
    {"role": "assistant", "content": "Hello, how are you?"},
    {"role": "user", "content": "Good, thanks!"},
]


class TestPostgresStore:
    """Test PostgreSQL profile operations."""

    @pytest.mark.asyncio
    async def test_create_and_retrieve(self, store):
        user_id = await store.create_profile(
            values_vector=SAMPLE_VALUES,
            intake_transcript=SAMPLE_TRANSCRIPT,
            intake_turns=1,
        )

        profile = await store.get_profile(user_id)
        assert profile is not None
        assert profile["values_vector"]["risk_tolerance"] == 0.7

    @pytest.mark.asyncio
    async def test_update_preserves_version(self, store):
        user_id = await store.create_profile(
            values_vector=SAMPLE_VALUES,
            intake_transcript=SAMPLE_TRANSCRIPT,
            intake_turns=1,
        )

        new_values = SAMPLE_VALUES.copy()
        new_values["risk_tolerance"] = 0.9
        await store.update_profile(user_id, new_values, source="test")

        profile = await store.get_profile(user_id)
        assert profile["values_vector"]["risk_tolerance"] == 0.9
        assert profile["profile_version"] == 2

    @pytest.mark.asyncio
    async def test_profile_history(self, store):
        user_id = await store.create_profile(
            values_vector=SAMPLE_VALUES,
            intake_transcript=SAMPLE_TRANSCRIPT,
            intake_turns=1,
        )

        new_values = SAMPLE_VALUES.copy()
        new_values["risk_tolerance"] = 0.3
        await store.update_profile(user_id, new_values, source="follow_up")

        history = await store.get_profile_history(user_id)
        assert len(history) >= 2

    @pytest.mark.asyncio
    async def test_get_nonexistent(self, store):
        profile = await store.get_profile(str(uuid.uuid4()))
        assert profile is None

    @pytest.mark.asyncio
    async def test_profile_count(self, store):
        initial = await store.get_profile_count()
        await store.create_profile(
            values_vector=SAMPLE_VALUES,
            intake_transcript=SAMPLE_TRANSCRIPT,
            intake_turns=1,
        )
        assert await store.get_profile_count() == initial + 1
