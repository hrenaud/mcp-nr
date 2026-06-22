"""
Tests for HTTP routes (/guide endpoint with Accept header negotiation).

Verifies:
- JSON response when Accept: application/json is sent
- HTML response by default (Accept: text/html)
- Schema validation for tool definitions
- Type hints on _get_tool_definitions()
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "files"))

import pytest
import json
from unittest.mock import AsyncMock, MagicMock
from mcp_ref_core import routes


class TestGetToolDefinitions:
    """Test _get_tool_definitions() function."""

    def test_returns_list_of_dicts(self):
        """_get_tool_definitions() returns a list of dictionaries."""
        # After migration, we test the tools registered on the mcp instance
        import rgaa_mcp
        tools = [t.model_dump() for t in rgaa_mcp.mcp.tools.values()]
        assert isinstance(tools, list)
        assert len(tools) > 0
        assert all(isinstance(tool, dict) for tool in tools)

    def test_has_return_type_hint(self):
        """_get_tool_definitions() has return type hint."""
        import inspect
        sig = inspect.signature(routes._get_tool_definitions)
        assert sig.return_annotation != inspect.Signature.empty, (
            "_get_tool_definitions() missing return type hint"
        )
        # Should be list[dict] or list[dict[str, Any]]
        hint_str = str(sig.return_annotation)
        assert "list" in hint_str.lower(), f"Expected list in return type, got {hint_str}"

    def test_all_tools_have_required_fields(self):
        """Each tool definition has name, description, and inputSchema."""
        tools = routes._get_tool_definitions()
        for tool in tools:
            assert "name" in tool, f"Tool missing 'name': {tool}"
            assert "description" in tool, f"Tool missing 'description': {tool}"
            assert "inputSchema" in tool, f"Tool missing 'inputSchema': {tool}"
            assert isinstance(tool["name"], str)
            assert isinstance(tool["description"], str)
            assert isinstance(tool["inputSchema"], dict)

    def test_tools_have_valid_schemas(self):
        """Each tool's inputSchema is a valid JSON Schema object."""
        tools = routes._get_tool_definitions()
        for tool in tools:
            schema = tool["inputSchema"]
            assert "type" in schema, f"inputSchema missing 'type' for tool {tool['name']}"
            assert schema["type"] == "object"
            assert "properties" in schema

    def test_all_tools_have_unique_names(self):
        """All tool names are unique."""
        tools = routes._get_tool_definitions()
        names = [tool["name"] for tool in tools]
        assert len(names) == len(set(names)), f"Duplicate tool names found: {names}"

    def test_expected_tool_count_and_names(self):
        """Verify expected RGAA tools are present."""
        import rgaa_mcp
        tools = [t.model_dump() for t in rgaa_mcp.mcp.tools.values()]
        tool_names = {tool["name"] for tool in tools}
        expected_names = {
            "rgaa_lister_criteres",
            "rgaa_obtenir_critere",
            "rgaa_chercher",
            "rgaa_glossaire",
            "rgaa_statistiques",
            "rgaa_analyser",
            "rgaa_checklist",
            "rgaa_taux_conformite",
            "rgaa_types_audit",
            "rgaa_criteres_audit",
        }
        assert tool_names == expected_names, f"Tool names mismatch. Got {tool_names}"


class TestHttpGuideJsonResponse:
    """Test /guide endpoint with JSON content negotiation."""

    @pytest.mark.asyncio
    async def test_returns_json_with_application_json_header(self):
        """_http_guide returns JSON when Accept: application/json."""
        # Mock the request with Accept header
        request = MagicMock()
        request.headers.get.return_value = "application/json"

        # Call the route handler
        response = await routes._http_guide(request)

        # Verify it's a JSONResponse
        from starlette.responses import JSONResponse
        assert isinstance(response, JSONResponse)

        # Verify the body is valid JSON
        body = json.loads(response.body.decode())
        assert "tools" in body
        assert isinstance(body["tools"], list)

    @pytest.mark.asyncio
    async def test_json_response_has_valid_tools(self):
        """JSON response contains valid tool definitions."""
        request = MagicMock()
        request.headers.get.return_value = "application/json"

        response = await routes._http_guide(request)
        body = json.loads(response.body.decode())
        tools = body["tools"]

        # Verify each tool has required fields
        for tool in tools:
            assert "name" in tool
            assert "description" in tool
            assert "inputSchema" in tool

    @pytest.mark.asyncio
    async def test_returns_html_with_text_html_header(self):
        """_http_guide returns HTML when Accept: text/html."""
        request = MagicMock()
        request.headers.get.return_value = "text/html"

        response = await routes._http_guide(request)

        from starlette.responses import HTMLResponse
        assert isinstance(response, HTMLResponse)

        body = response.body.decode()
        assert "<!DOCTYPE html>" in body
        assert "RGAA" in body

    @pytest.mark.asyncio
    async def test_returns_html_by_default_without_header(self):
        """_http_guide returns HTML by default when Accept header not set."""
        request = MagicMock()
        # Simulate no Accept header (defaults to text/html)
        request.headers.get.return_value = "text/html"

        response = await routes._http_guide(request)

        from starlette.responses import HTMLResponse
        assert isinstance(response, HTMLResponse)

    @pytest.mark.asyncio
    async def test_html_response_includes_tool_table(self):
        """HTML response includes a table with tool names and descriptions."""
        request = MagicMock()
        request.headers.get.return_value = "text/html"

        response = await routes._http_guide(request)
        body = response.body.decode()

        # Verify tools are rendered in the table
        assert "<table>" in body
        assert "rgaa_lister_criteres" in body
        assert "rgaa_obtenir_critere" in body

    @pytest.mark.asyncio
    async def test_json_response_content_type(self):
        """JSON response has correct Content-Type header."""
        request = MagicMock()
        request.headers.get.return_value = "application/json"

        response = await routes._http_guide(request)

        # JSONResponse should have application/json content type
        assert "application/json" in response.headers.get("content-type", "")

    @pytest.mark.asyncio
    async def test_accept_header_with_multiple_types(self):
        """Accept header with multiple types (e.g., 'text/html, application/json')."""
        request = MagicMock()
        request.headers.get.return_value = "text/html, application/json;q=0.9"

        # Since application/json is in the accept header, JSON should be returned
        response = await routes._http_guide(request)

        from starlette.responses import JSONResponse
        assert isinstance(response, JSONResponse)


class TestToolDefinitionsConsistency:
    """Test consistency of tool definitions across requests."""

    def test_tool_definitions_consistent_across_calls(self):
        """_get_tool_definitions() returns consistent results."""
        call1 = routes._get_tool_definitions()
        call2 = routes._get_tool_definitions()

        # Convert to comparable format
        names1 = {t["name"] for t in call1}
        names2 = {t["name"] for t in call2}

        assert names1 == names2

    def test_no_missing_required_schema_fields(self):
        """Every tool schema has required properties field."""
        tools = routes._get_tool_definitions()
        for tool in tools:
            schema = tool["inputSchema"]
            assert "properties" in schema, (
                f"Tool {tool['name']} missing 'properties' in inputSchema"
            )


class TestGetBaseUrl:
    """Test _get_base_url() function."""

    def test_returns_mcp_base_url_when_set(self, monkeypatch):
        """_get_base_url() returns MCP_BASE_URL when set."""
        monkeypatch.setenv("MCP_BASE_URL", "https://example.com")
        result = routes._get_base_url()
        assert result == "https://example.com"

    def test_strips_trailing_slash_from_base_url(self, monkeypatch):
        """_get_base_url() removes trailing slash."""
        monkeypatch.setenv("MCP_BASE_URL", "https://example.com/")
        result = routes._get_base_url()
        assert result == "https://example.com"

    def test_constructs_url_from_host_port(self, monkeypatch):
        """_get_base_url() constructs URL from MCP_HOST and MCP_PORT."""
        monkeypatch.delenv("MCP_BASE_URL", raising=False)
        monkeypatch.setenv("MCP_HOST", "0.0.0.0")
        monkeypatch.setenv("MCP_PORT", "8000")
        result = routes._get_base_url()
        assert result == "http://localhost:8000"

    def test_uses_custom_host(self, monkeypatch):
        """_get_base_url() uses custom host when not 0.0.0.0."""
        monkeypatch.delenv("MCP_BASE_URL", raising=False)
        monkeypatch.setenv("MCP_HOST", "192.168.1.1")
        monkeypatch.setenv("MCP_PORT", "8080")
        result = routes._get_base_url()
        assert result == "http://192.168.1.1:8080"

    def test_defaults_to_localhost_when_empty_host(self, monkeypatch):
        """_get_base_url() uses localhost when host is empty string."""
        monkeypatch.delenv("MCP_BASE_URL", raising=False)
        monkeypatch.setenv("MCP_HOST", "")
        monkeypatch.setenv("MCP_PORT", "8000")
        result = routes._get_base_url()
        assert result == "http://localhost:8000"


class TestGetTokenRequestUrl:
    """Test _get_token_request_url() function."""

    def test_returns_token_request_url_when_set(self, monkeypatch):
        """_get_token_request_url() returns MCP_TOKEN_REQUEST_URL when set."""
        monkeypatch.setenv("MCP_TOKEN_REQUEST_URL", "https://example.com/token-request")
        result = routes._get_token_request_url()
        assert result == "https://example.com/token-request"

    def test_returns_empty_string_when_not_set(self, monkeypatch):
        """_get_token_request_url() returns empty string when env var not set."""
        monkeypatch.delenv("MCP_TOKEN_REQUEST_URL", raising=False)
        result = routes._get_token_request_url()
        assert result == ""


class TestHttpHomepage:
    """Test _http_homepage() route handler."""

    @pytest.mark.asyncio
    async def test_returns_html_response(self):
        """_http_homepage() returns an HTMLResponse."""
        from starlette.responses import HTMLResponse
        request = MagicMock()
        response = await routes._http_homepage(request)
        assert isinstance(response, HTMLResponse)

    @pytest.mark.asyncio
    async def test_homepage_contains_title(self):
        """Homepage HTML contains RGAA MCP title."""
        request = MagicMock()
        response = await routes._http_homepage(request)
        body = response.body.decode()
        assert "RGAA MCP" in body
        assert "<!DOCTYPE html>" in body

    @pytest.mark.asyncio
    async def test_homepage_contains_version(self):
        """Homepage displays version information."""
        request = MagicMock()
        response = await routes._http_homepage(request)
        body = response.body.decode()
        assert "RGAA 4.2.1" in body

    @pytest.mark.asyncio
    async def test_homepage_shows_cache_status(self):
        """Homepage displays cache status badge."""
        request = MagicMock()
        response = await routes._http_homepage(request)
        body = response.body.decode()
        # Should have either "chargés" or "vide"
        assert ("chargés" in body or "vide" in body)
        assert "badge" in body

    @pytest.mark.asyncio
    async def test_homepage_escapes_base_url(self):
        """Homepage properly escapes base URL for HTML."""
        import os
        old_url = os.environ.get("MCP_BASE_URL")
        try:
            os.environ["MCP_BASE_URL"] = "http://example.com"
            request = MagicMock()
            response = await routes._http_homepage(request)
            body = response.body.decode()
            assert "example.com" in body
        finally:
            if old_url:
                os.environ["MCP_BASE_URL"] = old_url
            elif "MCP_BASE_URL" in os.environ:
                del os.environ["MCP_BASE_URL"]


class TestHttpGuideErrorPaths:
    """Test error and edge cases in _http_guide() handler."""

    @pytest.mark.asyncio
    async def test_guide_with_invalid_accept_header(self):
        """_http_guide() handles invalid Accept header gracefully."""
        request = MagicMock()
        request.headers.get.return_value = "invalid/type"
        response = await routes._http_guide(request)
        from starlette.responses import HTMLResponse
        assert isinstance(response, HTMLResponse)

    @pytest.mark.asyncio
    async def test_guide_with_empty_accept_header(self):
        """_http_guide() defaults to HTML when Accept header is empty."""
        request = MagicMock()
        request.headers.get.return_value = ""
        response = await routes._http_guide(request)
        from starlette.responses import HTMLResponse
        assert isinstance(response, HTMLResponse)

    @pytest.mark.asyncio
    async def test_guide_with_malformed_accept_header(self):
        """_http_guide() handles malformed Accept header with */*."""
        request = MagicMock()
        request.headers.get.return_value = "*/*"
        response = await routes._http_guide(request)
        from starlette.responses import HTMLResponse
        assert isinstance(response, HTMLResponse)

    @pytest.mark.asyncio
    async def test_guide_html_with_token_request_url(self):
        """_http_guide() includes token request URL in HTML when set."""
        import os
        old_url = os.environ.get("MCP_TOKEN_REQUEST_URL")
        try:
            os.environ["MCP_TOKEN_REQUEST_URL"] = "https://example.com/token"
            request = MagicMock()
            request.headers.get.return_value = "text/html"
            response = await routes._http_guide(request)
            body = response.body.decode()
            assert "example.com/token" in body
        finally:
            if old_url:
                os.environ["MCP_TOKEN_REQUEST_URL"] = old_url
            elif "MCP_TOKEN_REQUEST_URL" in os.environ:
                del os.environ["MCP_TOKEN_REQUEST_URL"]

    @pytest.mark.asyncio
    async def test_guide_html_without_token_request_url(self):
        """_http_guide() omits token request URL when not set."""
        import os
        old_url = os.environ.get("MCP_TOKEN_REQUEST_URL")
        try:
            if "MCP_TOKEN_REQUEST_URL" in os.environ:
                del os.environ["MCP_TOKEN_REQUEST_URL"]
            request = MagicMock()
            request.headers.get.return_value = "text/html"
            response = await routes._http_guide(request)
            body = response.body.decode()
            assert "Contactez l'administrateur" in body
        finally:
            if old_url:
                os.environ["MCP_TOKEN_REQUEST_URL"] = old_url

    @pytest.mark.asyncio
    async def test_guide_html_with_invalid_token_url(self):
        """_http_guide() ignores invalid token URL (not http/https)."""
        import os
        old_url = os.environ.get("MCP_TOKEN_REQUEST_URL")
        try:
            os.environ["MCP_TOKEN_REQUEST_URL"] = "ftp://invalid.com"
            request = MagicMock()
            request.headers.get.return_value = "text/html"
            response = await routes._http_guide(request)
            body = response.body.decode()
            assert "Contactez l'administrateur" in body
            assert "ftp://" not in body
        finally:
            if old_url:
                os.environ["MCP_TOKEN_REQUEST_URL"] = old_url
            elif "MCP_TOKEN_REQUEST_URL" in os.environ:
                del os.environ["MCP_TOKEN_REQUEST_URL"]

    @pytest.mark.asyncio
    async def test_guide_json_content_has_correct_structure(self):
        """JSON response has correct top-level structure."""
        request = MagicMock()
        request.headers.get.return_value = "application/json"
        response = await routes._http_guide(request)
        body = json.loads(response.body.decode())
        assert "tools" in body
        assert isinstance(body["tools"], list)

    @pytest.mark.asyncio
    async def test_guide_html_escapes_special_characters(self):
        """_http_guide() escapes HTML special characters in URLs."""
        import os
        old_url = os.environ.get("MCP_BASE_URL")
        try:
            os.environ["MCP_BASE_URL"] = "http://example.com?a=<b>&c=d"
            request = MagicMock()
            request.headers.get.return_value = "text/html"
            response = await routes._http_guide(request)
            body = response.body.decode()
            # Check that < is escaped
            assert "&lt;" in body
        finally:
            if old_url:
                os.environ["MCP_BASE_URL"] = old_url
            elif "MCP_BASE_URL" in os.environ:
                del os.environ["MCP_BASE_URL"]


class TestHttpInstallScript:
    """Test _http_install_script() route handler."""

    @pytest.mark.asyncio
    async def test_returns_plaintext_response(self):
        """_http_install_script() returns a PlainTextResponse."""
        from starlette.responses import PlainTextResponse
        request = MagicMock()
        response = await routes._http_install_script(request)
        assert isinstance(response, PlainTextResponse)

    @pytest.mark.asyncio
    async def test_install_script_is_bash_script(self):
        """Install script starts with bash shebang."""
        request = MagicMock()
        response = await routes._http_install_script(request)
        body = response.body.decode()
        assert body.startswith("#!/usr/bin/env bash")

    @pytest.mark.asyncio
    async def test_install_script_contains_base_url(self):
        """Install script substitutes BASE_URL placeholder."""
        import os
        old_url = os.environ.get("MCP_BASE_URL")
        try:
            os.environ["MCP_BASE_URL"] = "https://example.com"
            request = MagicMock()
            response = await routes._http_install_script(request)
            body = response.body.decode()
            assert "https://example.com" in body
            # Should not contain placeholder
            assert "__BASE_URL__" not in body
        finally:
            if old_url:
                os.environ["MCP_BASE_URL"] = old_url
            elif "MCP_BASE_URL" in os.environ:
                del os.environ["MCP_BASE_URL"]

    @pytest.mark.asyncio
    async def test_install_script_contains_mcp_url(self):
        """Install script substitutes MCP_URL placeholder."""
        import os
        old_url = os.environ.get("MCP_BASE_URL")
        try:
            os.environ["MCP_BASE_URL"] = "https://example.com"
            request = MagicMock()
            response = await routes._http_install_script(request)
            body = response.body.decode()
            assert "https://example.com/mcp" in body
            assert "__MCP_URL__" not in body
        finally:
            if old_url:
                os.environ["MCP_BASE_URL"] = old_url
            elif "MCP_BASE_URL" in os.environ:
                del os.environ["MCP_BASE_URL"]

    @pytest.mark.asyncio
    async def test_install_script_contains_token_request_url(self):
        """Install script includes token request URL when configured."""
        import os
        old_url = os.environ.get("MCP_TOKEN_REQUEST_URL")
        try:
            os.environ["MCP_TOKEN_REQUEST_URL"] = "https://example.com/token"
            request = MagicMock()
            response = await routes._http_install_script(request)
            body = response.body.decode()
            assert "https://example.com/token" in body
        finally:
            if old_url:
                os.environ["MCP_TOKEN_REQUEST_URL"] = old_url
            elif "MCP_TOKEN_REQUEST_URL" in os.environ:
                del os.environ["MCP_TOKEN_REQUEST_URL"]

    @pytest.mark.asyncio
    async def test_install_script_media_type(self):
        """Install script has correct Content-Type."""
        request = MagicMock()
        response = await routes._http_install_script(request)
        content_type = response.headers.get("content-type", "")
        assert "text/plain" in content_type or "charset=utf-8" in content_type
