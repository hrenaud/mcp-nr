"""Fixtures partagées des tests RGAA."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "files"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "core"))

import pytest


@pytest.fixture(autouse=True)
def _reset_rgaa_rate_limit():
    """Isole l'état global du rate limiter de rgaa_analyser entre les tests."""
    try:
        import rgaa_mcp
        rgaa_mcp._reset_rate_limit()
    except Exception:
        pass
    yield
