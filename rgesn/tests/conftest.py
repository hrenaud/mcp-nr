"""Fixtures partagées des tests RGESN."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "files"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "core"))

import pytest


@pytest.fixture(autouse=True)
def _pin_mcp_instance():
    """Réépingle routes._mcp_instance sur l'instance RGESN réelle (cf. conftest GreenIT)."""
    from mcp_ref_core import routes
    import rgesn_mcp
    routes._mcp_instance = rgesn_mcp.mcp
    routes._get_tool_definitions = routes._tool_definitions_from_mcp
    yield
