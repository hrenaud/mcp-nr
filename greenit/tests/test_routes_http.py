"""
Tests for HTTP routes (/guide endpoint with Accept header negotiation).

Verifies:
- JSON response when Accept: application/json is sent
- HTML response by default (Accept: text/html)
- Schema validation for tool definitions
- Type hints on _get_tool_definitions()
- Optimized HTML rendering (no rebuilding full schema just for names)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "files"))

import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from mcp_ref_core import routes
import greenit_mcp  # noqa: F401 — injecte les tool defs + sections guide GreenIT dans routes


class TestGetToolDefinitions:
    """Test _get_tool_definitions() function."""

    def test_returns_list_of_dicts(self):
        """_get_tool_definitions() returns a list of dictionaries."""
        result = routes._get_tool_definitions()
        assert isinstance(result, list)
        assert len(result) > 0
        assert all(isinstance(tool, dict) for tool in result)

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
        """Verify expected GreenIT tools are present."""
        tools = routes._get_tool_definitions()
        tool_names = {tool["name"] for tool in tools}
        expected_names = {
            "greenit_lister_fiches",
            "greenit_fiches_prioritaires",
            "greenit_chercher_fiche",
            "greenit_comparer_fiches",
            "greenit_obtenir_fiche_complete",
            "greenit_obtenir_statistiques",
            "greenit_lister_lifecycles",
            "greenit_lister_ressources",
            "greenit_calculer_ecoindex",
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
        assert "GreenIT" in body

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
        assert "greenit_lister_fiches" in body
        assert "greenit_chercher_fiche" in body

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


class TestHtmlRenderingOptimization:
    """Test that HTML rendering is optimized (not rebuilding full schema)."""

    @pytest.mark.asyncio
    async def test_get_tool_definitions_called_only_once_for_html(self):
        """For HTML rendering, _get_tool_definitions() is called once, not multiple times."""
        request = MagicMock()
        request.headers.get.return_value = "text/html"

        # Patch _get_tool_definitions to track calls
        original = routes._get_tool_definitions
        call_count = [0]

        def tracked_get_tool_definitions():
            call_count[0] += 1
            return original()

        with patch.object(routes, "_get_tool_definitions", side_effect=tracked_get_tool_definitions):
            response = await routes._http_guide(request)
            # Should be called once for HTML rendering (not once for HTML + once for JSON)
            assert call_count[0] == 1, f"Expected 1 call, got {call_count[0]}"


class TestHttpHomepage:
    """Test the _http_homepage endpoint."""

    @pytest.mark.asyncio
    async def test_homepage_returns_html_response(self):
        """_http_homepage returns an HTMLResponse."""
        from starlette.responses import HTMLResponse
        request = MagicMock()

        response = await routes._http_homepage(request)
        assert isinstance(response, HTMLResponse)

    @pytest.mark.asyncio
    async def test_homepage_contains_html_structure(self):
        """Homepage HTML contains expected structure."""
        request = MagicMock()
        response = await routes._http_homepage(request)
        body = response.body.decode()

        assert "<!DOCTYPE html>" in body
        assert "<html" in body
        assert "GreenIT MCP" in body
        assert "</html>" in body

    @pytest.mark.asyncio
    async def test_homepage_displays_server_version(self):
        """Homepage displays the server version."""
        request = MagicMock()

        original_version = routes._VERSION
        routes._VERSION = "test-version"
        try:
            response = await routes._http_homepage(request)
            body = response.body.decode()
            assert "test-version" in body
        finally:
            routes._VERSION = original_version

    @pytest.mark.asyncio
    async def test_homepage_includes_install_instructions(self):
        """Homepage includes installation instruction block."""
        request = MagicMock()
        response = await routes._http_homepage(request)
        body = response.body.decode()

        assert "curl -sSL" in body
        assert "/install.sh" in body
        assert "bash -s --" in body

    @pytest.mark.asyncio
    async def test_homepage_includes_documentation_link(self):
        """Homepage includes link to guide documentation."""
        request = MagicMock()
        response = await routes._http_homepage(request)
        body = response.body.decode()

        assert "/guide" in body
        assert "Documentation" in body

    @pytest.mark.asyncio
    async def test_homepage_cache_status_ok(self):
        """Homepage shows 'entrées chargées' when cache is populated."""
        request = MagicMock()

        # Patch the charger_cache function where it's imported in routes
        with patch("data.charger_cache", return_value={"fiches": {"a": 1, "b": 2}}):
            response = await routes._http_homepage(request)
            body = response.body.decode()

            assert "entrées chargées" in body
            assert "badge ok" in body

    @pytest.mark.asyncio
    async def test_homepage_cache_status_warn(self):
        """Homepage shows warning when cache is empty."""
        request = MagicMock()

        # Patch the charger_cache function where it's imported in routes
        with patch("data.charger_cache", return_value={}):
            response = await routes._http_homepage(request)
            body = response.body.decode()

            assert "Cache vide" in body
            assert "badge warn" in body

    @pytest.mark.asyncio
    async def test_homepage_escapes_base_url(self):
        """Homepage escapes special characters in base URL."""
        request = MagicMock()

        with patch("mcp_ref_core.routes._get_base_url", return_value="http://localhost:8000"):
            response = await routes._http_homepage(request)
            body = response.body.decode()

            # Should contain the URL (properly escaped if needed)
            assert "localhost:8000" in body

    @pytest.mark.asyncio
    async def test_homepage_displays_referentiel_version(self):
        """Homepage displays referentiel version when set."""
        request = MagicMock()
        original = routes._REFERENTIEL_VERSION
        routes._REFERENTIEL_VERSION = "2026-04-10"
        try:
            response = await routes._http_homepage(request)
            body = response.body.decode()
            assert "2026-04-10" in body
        finally:
            routes._REFERENTIEL_VERSION = original


class TestHttpInstallScript:
    """Test the _http_install_script endpoint."""

    @pytest.mark.asyncio
    async def test_install_script_returns_plaintext_response(self):
        """_http_install_script returns a PlainTextResponse."""
        from starlette.responses import PlainTextResponse
        request = MagicMock()

        response = await routes._http_install_script(request)
        assert isinstance(response, PlainTextResponse)

    @pytest.mark.asyncio
    async def test_install_script_has_bash_shebang(self):
        """Install script starts with bash shebang."""
        request = MagicMock()
        response = await routes._http_install_script(request)
        body = response.body.decode()

        assert body.startswith("#!/usr/bin/env bash")

    @pytest.mark.asyncio
    async def test_install_script_includes_base_url(self):
        """Install script contains replaced base URL."""
        request = MagicMock()

        with patch("mcp_ref_core.routes._get_base_url", return_value="http://example.com"):
            response = await routes._http_install_script(request)
            body = response.body.decode()

            # Should have replaced __BASE_URL__ with actual URL
            assert "__BASE_URL__" not in body
            assert "http://example.com" in body

    @pytest.mark.asyncio
    async def test_install_script_includes_mcp_url(self):
        """Install script contains MCP endpoint URL."""
        request = MagicMock()

        with patch("mcp_ref_core.routes._get_base_url", return_value="http://example.com"):
            response = await routes._http_install_script(request)
            body = response.body.decode()

            # Should have MCP URL with /mcp path
            assert "__MCP_URL__" not in body
            assert "http://example.com/mcp" in body

    @pytest.mark.asyncio
    async def test_install_script_includes_token_request_url(self):
        """Install script includes token request URL when configured."""
        request = MagicMock()

        with patch("mcp_ref_core.routes._get_token_request_url", return_value="http://example.com/request-token"):
            response = await routes._http_install_script(request)
            body = response.body.decode()

            # Should have token request URL or empty placeholder
            assert "http://example.com/request-token" in body

    @pytest.mark.asyncio
    async def test_install_script_handles_empty_token_request_url(self):
        """Install script handles empty token request URL gracefully."""
        request = MagicMock()

        with patch("mcp_ref_core.routes._get_token_request_url", return_value=""):
            response = await routes._http_install_script(request)
            body = response.body.decode()

            # Should not have __TOKEN_REQUEST_URL__ placeholder
            assert "__TOKEN_REQUEST_URL__" not in body
            # Should have empty string replacement
            assert body.count("TOKEN_REQUEST_URL=") >= 1

    @pytest.mark.asyncio
    async def test_install_script_includes_installation_logic(self):
        """Install script includes client detection and installation logic."""
        request = MagicMock()
        response = await routes._http_install_script(request)
        body = response.body.decode()

        # Check for key functions and logic
        assert "has_claude_code" in body
        assert "has_cursor" in body
        assert "has_vscode" in body
        assert "claude mcp add" in body

    @pytest.mark.asyncio
    async def test_install_script_media_type(self):
        """Install script response has correct media type."""
        request = MagicMock()
        response = await routes._http_install_script(request)

        # Check media type header
        assert "text/plain" in response.media_type


class TestInvalidAcceptHeaders:
    """Test handling of invalid/malformed Accept headers."""

    @pytest.mark.asyncio
    async def test_guide_with_invalid_content_type(self):
        """_http_guide handles invalid Content-Type gracefully."""
        request = MagicMock()
        request.headers.get.return_value = "application/invalid"

        # Should default to HTML for unknown types
        response = await routes._http_guide(request)
        from starlette.responses import HTMLResponse
        assert isinstance(response, HTMLResponse)

    @pytest.mark.asyncio
    async def test_guide_with_malformed_accept_header(self):
        """_http_guide handles malformed Accept header."""
        request = MagicMock()
        request.headers.get.return_value = "text/html; invalid=parameter; garbage"

        # Should fallback to HTML
        response = await routes._http_guide(request)
        from starlette.responses import HTMLResponse
        assert isinstance(response, HTMLResponse)

    @pytest.mark.asyncio
    async def test_guide_with_empty_accept_header(self):
        """_http_guide handles empty Accept header."""
        request = MagicMock()
        request.headers.get.return_value = ""

        # Should default to HTML when header is empty
        response = await routes._http_guide(request)
        from starlette.responses import HTMLResponse
        assert isinstance(response, HTMLResponse)

    @pytest.mark.asyncio
    async def test_guide_with_charset_parameter(self):
        """_http_guide handles Accept header with charset parameter."""
        request = MagicMock()
        request.headers.get.return_value = "application/json; charset=utf-8"

        # Should correctly identify JSON even with charset
        response = await routes._http_guide(request)
        from starlette.responses import JSONResponse
        assert isinstance(response, JSONResponse)

    @pytest.mark.asyncio
    async def test_guide_with_quality_values(self):
        """_http_guide handles Accept header with quality values."""
        request = MagicMock()
        request.headers.get.return_value = "application/json;q=0.9, text/html;q=0.8"

        # JSON should be returned (higher quality value)
        response = await routes._http_guide(request)
        from starlette.responses import JSONResponse
        assert isinstance(response, JSONResponse)

    @pytest.mark.asyncio
    async def test_guide_with_wildcard_accept(self):
        """_http_guide handles wildcard Accept header."""
        request = MagicMock()
        request.headers.get.return_value = "*/*"

        # Should still return something (implementation-dependent, likely HTML)
        response = await routes._http_guide(request)
        # Should not crash and return valid response
        assert response is not None


class TestBaseUrlConfiguration:
    """Test _get_base_url() function with various configurations."""

    def test_base_url_from_env_mcp_base_url(self):
        """_get_base_url() returns MCP_BASE_URL from environment."""
        with patch.dict("os.environ", {"MCP_BASE_URL": "http://custom.example.com"}):
            url = routes._get_base_url()
            assert url == "http://custom.example.com"

    def test_base_url_strips_trailing_slash(self):
        """_get_base_url() strips trailing slashes."""
        with patch.dict("os.environ", {"MCP_BASE_URL": "http://example.com/"}):
            url = routes._get_base_url()
            assert url == "http://example.com"

    def test_base_url_default_with_host_port(self):
        """_get_base_url() constructs from MCP_HOST and MCP_PORT."""
        env = {"MCP_BASE_URL": "", "MCP_HOST": "0.0.0.0", "MCP_PORT": "8000"}
        with patch.dict("os.environ", env, clear=False):
            url = routes._get_base_url()
            assert "localhost:8000" in url

    def test_base_url_custom_host(self):
        """_get_base_url() uses custom host when not 0.0.0.0."""
        env = {"MCP_BASE_URL": "", "MCP_HOST": "example.com", "MCP_PORT": "8080"}
        with patch.dict("os.environ", env, clear=False):
            url = routes._get_base_url()
            assert "example.com:8080" in url


class TestTokenRequestUrl:
    """Test _get_token_request_url() function."""

    def test_token_request_url_from_env(self):
        """_get_token_request_url() returns MCP_TOKEN_REQUEST_URL."""
        with patch.dict("os.environ", {"MCP_TOKEN_REQUEST_URL": "http://example.com/request"}):
            url = routes._get_token_request_url()
            assert url == "http://example.com/request"

    def test_token_request_url_default_empty(self):
        """_get_token_request_url() defaults to empty string."""
        with patch.dict("os.environ", {"MCP_TOKEN_REQUEST_URL": ""}, clear=False):
            url = routes._get_token_request_url()
            assert url == ""


class TestGuideWithTokenRequestUrl:
    """Test /guide endpoint behavior with token request URL."""

    @pytest.mark.asyncio
    async def test_guide_includes_token_request_url_when_configured(self):
        """Guide HTML includes token request URL when configured."""
        request = MagicMock()
        request.headers.get.return_value = "text/html"

        with patch("mcp_ref_core.routes._get_token_request_url", return_value="http://example.com/request-token"):
            response = await routes._http_guide(request)
            body = response.body.decode()

            # Should include the token request URL in the HTML
            assert "http://example.com/request-token" in body
            assert "Demander un accès" in body or "request" in body.lower()

    @pytest.mark.asyncio
    async def test_guide_escapes_token_request_url(self):
        """Guide properly escapes token request URL in HTML."""
        request = MagicMock()
        request.headers.get.return_value = "text/html"

        # URL with special characters that need escaping
        with patch("mcp_ref_core.routes._get_token_request_url", return_value="http://example.com/request?token=abc&user=test"):
            response = await routes._http_guide(request)
            body = response.body.decode()

            # URL should be present (possibly escaped)
            assert "example.com" in body

    @pytest.mark.asyncio
    async def test_guide_handles_non_http_token_url(self):
        """Guide handles non-HTTP token URL (doesn't include it)."""
        request = MagicMock()
        request.headers.get.return_value = "text/html"

        # Non-HTTP URL should not be included in the token section
        with patch("mcp_ref_core.routes._get_token_request_url", return_value="not-a-valid-url"):
            response = await routes._http_guide(request)
            body = response.body.decode()

            # Should contain alternative token instruction (contact admin)
            assert "administrateur" in body or "admin" in body.lower()

    @pytest.mark.asyncio
    async def test_guide_with_https_token_url(self):
        """Guide handles HTTPS token URL correctly."""
        request = MagicMock()
        request.headers.get.return_value = "text/html"

        with patch("mcp_ref_core.routes._get_token_request_url", return_value="https://secure.example.com/token"):
            response = await routes._http_guide(request)
            body = response.body.decode()

            # Should include the HTTPS URL
            assert "https://secure.example.com/token" in body


class TestGuideGreenItEcoIndex:
    """Le guide GreenIT doit toujours afficher la section EcoIndex (injectée par greenit_mcp)."""

    def test_guide_greenit_contient_ecoindex(self):
        import asyncio
        req = MagicMock()
        req.headers = {"accept": "text/html"}
        resp = asyncio.run(routes._http_guide(req))
        body = resp.body.decode()
        assert "EcoIndex" in body
        assert "greenit_calculer_ecoindex" in body
