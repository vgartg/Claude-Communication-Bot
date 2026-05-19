import os
from pathlib import Path

import pytest

# Tests must not depend on the developer's local .env — set required settings up front.
os.environ.setdefault("CCB_BOT_TOKEN", "test:dummy")
os.environ.setdefault("CCB_PORT", "3000")


@pytest.fixture(autouse=True)
def _fresh_registry(tmp_path: Path):
    """Initialize a clean UserRegistry for every test (function scope)."""
    from claude_comm_bot.store import init_registry

    init_registry(tmp_path / "users.json")
    yield
