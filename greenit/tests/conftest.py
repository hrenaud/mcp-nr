"""Fixtures partagées des tests GreenIT."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "files"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "core"))

import pytest


@pytest.fixture(autouse=True)
def _pin_mcp_instance():
    """Réépingle routes._mcp_instance sur l'instance GreenIT réelle.

    Les tests de câblage créent des instances FastMCP sans outils qui polluent
    le global partagé ; on garantit que la dérivation introspective du /guide
    retourne bien les outils GreenIT.
    """
    from mcp_ref_core import routes
    import greenit_mcp
    routes._mcp_instance = greenit_mcp.mcp
    routes._get_tool_definitions = routes._tool_definitions_from_mcp
    yield
