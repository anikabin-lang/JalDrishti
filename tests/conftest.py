"""Global Pytest Configuration and Test Fixtures."""

import pytest
from backend.app.core.security import _global_limiter


@pytest.fixture(autouse=True)
def reset_global_rate_limiter():
    """Reset the in-memory rate limiter state before every test to ensure test isolation."""
    _global_limiter._history.clear()
    yield
    _global_limiter._history.clear()
