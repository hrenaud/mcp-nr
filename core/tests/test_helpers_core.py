"""Tests des helpers de validation partagés (core ne connaît aucun MCP)."""

import pytest
from fastmcp.exceptions import ToolError

from mcp_ref_core._helpers import validate_themes


def test_message_erreur_sans_nom_de_mcp():
    with pytest.raises(ToolError) as exc:
        validate_themes([99])
    msg = str(exc.value)
    assert "rgaa_statistiques" not in msg
    assert "entre 1 et 13" in msg


def test_validate_themes_none_retourne_tous():
    assert validate_themes(None) == list(range(1, 14))
