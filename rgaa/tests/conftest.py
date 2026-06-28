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


@pytest.fixture(autouse=True)
def _pin_mcp_instance():
    """Réépingle routes._mcp_instance sur l'instance RGAA réelle (cf. conftest GreenIT)."""
    from mcp_ref_core import routes
    import rgaa_mcp
    routes._mcp_instance = rgaa_mcp.mcp
    routes._get_tool_definitions = routes._tool_definitions_from_mcp
    yield
