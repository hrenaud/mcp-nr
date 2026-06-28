import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "files"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "core"))

import pytest
from fastmcp.exceptions import ToolError

import rgaa_mcp

_HTML_OK = "<html lang='fr'><head><title>t</title><meta charset='utf-8'></head><body></body></html>"


def test_rate_limit_bloque_apres_seuil(monkeypatch):
    monkeypatch.setattr(rgaa_mcp, "fetcher_html", lambda url: _HTML_OK)
    rgaa_mcp._reset_rate_limit()
    for _ in range(rgaa_mcp._RATE_LIMIT_MAX):
        rgaa_mcp.rgaa_analyser("https://example.com")
    with pytest.raises(ToolError, match="Trop de requêtes"):
        rgaa_mcp.rgaa_analyser("https://example.com")


def test_rate_limit_reset_debloque(monkeypatch):
    monkeypatch.setattr(rgaa_mcp, "fetcher_html", lambda url: _HTML_OK)
    rgaa_mcp._reset_rate_limit()
    for _ in range(rgaa_mcp._RATE_LIMIT_MAX):
        rgaa_mcp.rgaa_analyser("https://example.com")
    rgaa_mcp._reset_rate_limit()
    # après reset, une nouvelle requête repasse
    rgaa_mcp.rgaa_analyser("https://example.com")


def test_fetcher_html_timeout_par_defaut_reduit():
    import inspect
    from analyseur import fetcher_html
    sig = inspect.signature(fetcher_html)
    assert sig.parameters["timeout"].default == 10.0
