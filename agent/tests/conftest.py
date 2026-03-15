"""pytest configuration for Phase 4 agent tests."""

import pytest


@pytest.fixture
def anyio_backend():
    return "asyncio"
