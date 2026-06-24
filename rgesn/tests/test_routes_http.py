"""
Tests des routes HTTP RGESN (/guide, /, /install.sh).

Vérifie la négociation Accept: application/json vs text/html,
la cohérence des définitions d'outils, et les helpers d'URL.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "files"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "core"))

import pytest
import json
from unittest.mock import MagicMock
from mcp_ref_core import routes


class TestGetToolDefinitions:
    def test_returns_list_of_dicts(self):
        import rgesn_mcp
        tools = rgesn_mcp._rgesn_tool_definitions()
        assert isinstance(tools, list)
        assert len(tools) > 0
        assert all(isinstance(t, dict) for t in tools)

    def test_has_return_type_hint(self):
        import inspect
        sig = inspect.signature(routes._get_tool_definitions)
        assert sig.return_annotation != inspect.Signature.empty

    def test_all_tools_have_required_fields(self):
        import rgesn_mcp
        for tool in rgesn_mcp._rgesn_tool_definitions():
            assert "name" in tool
            assert "description" in tool
            assert "inputSchema" in tool

    def test_expected_tool_count(self):
        import rgesn_mcp
        tools = rgesn_mcp._rgesn_tool_definitions()
        assert len(tools) == 7

    def test_all_tools_have_unique_names(self):
        import rgesn_mcp
        names = [t["name"] for t in rgesn_mcp._rgesn_tool_definitions()]
        assert len(names) == len(set(names))


class TestHttpGuideJsonResponse:
    @pytest.mark.asyncio
    async def test_returns_json_with_application_json_header(self):
        from starlette.responses import JSONResponse
        request = MagicMock()
        request.headers.get.return_value = "application/json"
        response = await routes._http_guide(request)
        assert isinstance(response, JSONResponse)
        body = json.loads(response.body.decode())
        assert "tools" in body
        assert isinstance(body["tools"], list)

    @pytest.mark.asyncio
    async def test_returns_html_by_default(self):
        from starlette.responses import HTMLResponse
        request = MagicMock()
        request.headers.get.return_value = "text/html"
        response = await routes._http_guide(request)
        assert isinstance(response, HTMLResponse)

    @pytest.mark.asyncio
    async def test_html_response_includes_rgesn_tools(self):
        request = MagicMock()
        request.headers.get.return_value = "text/html"
        response = await routes._http_guide(request)
        body = response.body.decode()
        assert "rgesn_lister_criteres" in body
        assert "rgesn_obtenir_critere" in body


class TestGetBaseUrl:
    def test_returns_mcp_base_url_when_set(self, monkeypatch):
        monkeypatch.setenv("MCP_BASE_URL", "https://rgesn.example.com")
        assert routes._get_base_url() == "https://rgesn.example.com"

    def test_strips_trailing_slash_from_base_url(self, monkeypatch):
        monkeypatch.setenv("MCP_BASE_URL", "https://rgesn.example.com/")
        assert routes._get_base_url() == "https://rgesn.example.com"

    def test_constructs_url_from_host_port(self, monkeypatch):
        monkeypatch.delenv("MCP_BASE_URL", raising=False)
        monkeypatch.setenv("MCP_HOST", "0.0.0.0")
        monkeypatch.setenv("MCP_PORT", "8002")
        assert routes._get_base_url() == "http://localhost:8002"

    def test_uses_custom_host(self, monkeypatch):
        monkeypatch.delenv("MCP_BASE_URL", raising=False)
        monkeypatch.setenv("MCP_HOST", "192.168.1.1")
        monkeypatch.setenv("MCP_PORT", "9000")
        assert routes._get_base_url() == "http://192.168.1.1:9000"


class TestGetTokenRequestUrl:
    def test_returns_token_request_url_when_set(self, monkeypatch):
        monkeypatch.setenv("MCP_TOKEN_REQUEST_URL", "https://forms.gle/rgesn")
        assert routes._get_token_request_url() == "https://forms.gle/rgesn"

    def test_returns_empty_string_when_not_set(self, monkeypatch):
        monkeypatch.delenv("MCP_TOKEN_REQUEST_URL", raising=False)
        assert routes._get_token_request_url() == ""


class TestHttpHomepage:
    @pytest.mark.asyncio
    async def test_returns_html_response(self):
        from starlette.responses import HTMLResponse
        request = MagicMock()
        response = await routes._http_homepage(request)
        assert isinstance(response, HTMLResponse)

    @pytest.mark.asyncio
    async def test_homepage_contains_title(self):
        request = MagicMock()
        response = await routes._http_homepage(request)
        body = response.body.decode()
        assert "RGESN MCP" in body

    @pytest.mark.asyncio
    async def test_homepage_displays_version(self):
        request = MagicMock()
        original = routes._VERSION
        routes._VERSION = "test-ver"
        try:
            response = await routes._http_homepage(request)
            body = response.body.decode()
            assert "test-ver" in body
        finally:
            routes._VERSION = original

    @pytest.mark.asyncio
    async def test_homepage_shows_cache_status(self):
        request = MagicMock()
        response = await routes._http_homepage(request)
        body = response.body.decode()
        assert "critères" in body or "entrées" in body or "Cache" in body

    @pytest.mark.asyncio
    async def test_homepage_displays_referentiel_version(self):
        request = MagicMock()
        original = routes._REFERENTIEL_VERSION
        routes._REFERENTIEL_VERSION = "2024"
        try:
            response = await routes._http_homepage(request)
            body = response.body.decode()
            assert "2024" in body
        finally:
            routes._REFERENTIEL_VERSION = original


class TestToolDefinitionsConsistency:
    def test_tool_definitions_stable_across_calls(self):
        import rgesn_mcp
        first = rgesn_mcp._rgesn_tool_definitions()
        second = rgesn_mcp._rgesn_tool_definitions()
        assert [t["name"] for t in first] == [t["name"] for t in second]

    def test_schemas_have_type_field(self):
        import rgesn_mcp
        for tool in rgesn_mcp._rgesn_tool_definitions():
            assert "type" in tool["inputSchema"], f"{tool['name']} missing type in inputSchema"
