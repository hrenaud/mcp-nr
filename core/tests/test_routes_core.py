"""Tests for shared core route functions."""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastmcp import FastMCP

from mcp_ref_core import routes


class TestRegisterVersionResource:
    """Tests for the centralized register_version_resource function."""

    def setup_method(self):
        self._orig_mcp_id = routes._MCP_ID
        self._orig_items_key = routes._ITEMS_KEY
        self._orig_version = routes._VERSION
        routes._MCP_ID = "test"
        routes._ITEMS_KEY = "items"
        routes._VERSION = "9.9.9"

    def teardown_method(self):
        routes._MCP_ID = self._orig_mcp_id
        routes._ITEMS_KEY = self._orig_items_key
        routes._VERSION = self._orig_version

    def test_function_exists(self):
        assert hasattr(routes, "register_version_resource")
        assert callable(routes.register_version_resource)

    def test_resource_is_registered(self):
        mcp = FastMCP("test")
        fake_cache = {"meta": {"version": "1.0"}, "items": {}}
        routes.register_version_resource(mcp, lambda: fake_cache)

        import asyncio
        resources = asyncio.run(mcp.list_resources())
        uris = [str(r.uri) for r in resources]
        assert any("test://version" in u for u in uris), f"test://version not found in {uris}"

    def test_resource_returns_unified_structure(self):
        mcp = FastMCP("test")
        fake_cache = {
            "meta": {"version": "3.0", "updated_at": "2026-01-01"},
            "items": {"a": 1, "b": 2, "c": 3},
        }
        routes.register_version_resource(mcp, lambda: fake_cache)

        import asyncio
        result = asyncio.run(mcp.read_resource("test://version"))
        data = json.loads(result.contents[0].content)

        assert data["server_version"] == "9.9.9"
        assert data["referentiel_version"] == "3.0"
        assert data["updated_at"] == "2026-01-01"
        assert data["nb_items"] == 3

    def test_resource_handles_missing_meta(self):
        mcp = FastMCP("test")
        fake_cache = {"items": {"x": 1}}
        routes.register_version_resource(mcp, lambda: fake_cache)

        import asyncio
        result = asyncio.run(mcp.read_resource("test://version"))
        data = json.loads(result.contents[0].content)

        assert data["referentiel_version"] == "inconnue"
        assert data["updated_at"] == "inconnue"
        assert data["nb_items"] == 1



class TestNoMcpSpecificsInCore:
    """core/routes.py ne doit contenir aucun code spécifique à un MCP (règle d'or)."""

    def test_default_tool_definitions_is_empty(self):
        assert routes._default_tool_definitions() == []

    def test_default_guide_extra_sections_is_empty(self):
        assert routes._default_guide_extra_sections() == ""

    def test_routes_has_no_greenit_specifics(self):
        import inspect
        src = inspect.getsource(routes)
        assert "_greenit_tool_definitions" not in src
        assert "greenit_calculer_ecoindex" not in src
        assert "EcoIndex" not in src


class TestToolDefinitionsFromMcp:
    """Task 3 — la liste /guide est dérivée des outils FastMCP enregistrés (#14/#21/#46/#51)."""

    def test_returns_empty_when_no_instance(self):
        routes._mcp_instance = None
        assert routes._tool_definitions_from_mcp() == []

    def test_derives_from_registered_tools(self):
        from fastmcp import FastMCP
        m = FastMCP("t")

        @m.tool
        def sample_tool(x: int) -> dict:
            """desc sample"""
            return {}

        routes._mcp_instance = m
        defs = routes._tool_definitions_from_mcp()
        names = {d["name"] for d in defs}
        assert "sample_tool" in names
        d = next(d for d in defs if d["name"] == "sample_tool")
        assert "desc sample" in (d["description"] or "")
        assert isinstance(d["inputSchema"], dict)
        assert "properties" in d["inputSchema"]


class TestBaseUrlSyncScript:
    """Le guide/homepage corrige l'URL affichée via window.location.origin (côté client)."""

    def test_function_exists(self):
        assert hasattr(routes, "_base_url_sync_script")
        assert callable(routes._base_url_sync_script)

    def test_script_uses_window_location_origin(self):
        script = routes._base_url_sync_script("http://localhost:8000")
        assert "window.location.origin" in script
        assert "<script>" in script and "</script>" in script

    def test_script_embeds_server_url_as_js_literal(self):
        script = routes._base_url_sync_script("http://localhost:8000")
        # URL encodée en littéral JS (JSON), pour comparer avec l'origine réelle.
        assert '"http://localhost:8000"' in script

    def test_script_targets_data_base_url_elements(self):
        script = routes._base_url_sync_script("http://localhost:8000")
        assert "data-base-url" in script

    def test_script_noop_when_origin_matches(self):
        script = routes._base_url_sync_script("http://localhost:8000")
        # Garde : si l'origine == valeur serveur, on ne fait rien.
        assert "origin === server" in script

    def test_script_escapes_quotes_in_url(self):
        # Une URL contenant un guillemet ne doit pas casser le littéral JS.
        script = routes._base_url_sync_script('http://x"y')
        assert 'http://x"y' not in script.replace('\\"', "")  # le guillemet brut est échappé


class TestGetBaseUrlFromRequest:
    """Le /guide (et homepage/install) doit refléter le domaine réel de la requête."""

    def _req(self, headers, scheme="http"):
        from unittest.mock import MagicMock
        r = MagicMock()
        r.headers = headers
        r.url.scheme = scheme
        return r

    def test_env_override_wins(self, monkeypatch):
        monkeypatch.setenv("MCP_BASE_URL", "https://configured.example")
        req = self._req({"host": "ignored.example"})
        assert routes._get_base_url(req) == "https://configured.example"

    def test_uses_forwarded_host_and_proto(self, monkeypatch):
        monkeypatch.delenv("MCP_BASE_URL", raising=False)
        req = self._req({"x-forwarded-host": "mcp.example.org", "x-forwarded-proto": "https"})
        assert routes._get_base_url(req) == "https://mcp.example.org"

    def test_uses_host_header_when_no_forwarded(self, monkeypatch):
        monkeypatch.delenv("MCP_BASE_URL", raising=False)
        req = self._req({"host": "mcp.example.org:8002"}, scheme="http")
        assert routes._get_base_url(req) == "http://mcp.example.org:8002"

    def test_forwarded_host_liste_prend_le_premier(self, monkeypatch):
        monkeypatch.delenv("MCP_BASE_URL", raising=False)
        req = self._req({"x-forwarded-host": "mcp.example.org, internal", "x-forwarded-proto": "https, http"})
        assert routes._get_base_url(req) == "https://mcp.example.org"

    def test_rejects_malicious_host_falls_back(self, monkeypatch):
        monkeypatch.delenv("MCP_BASE_URL", raising=False)
        monkeypatch.setenv("MCP_PORT", "8000")
        monkeypatch.setenv("MCP_HOST", "0.0.0.0")
        req = self._req({"host": "evil.com$(id)"})
        url = routes._get_base_url(req)
        assert "$(id)" not in url
        assert url == "http://localhost:8000"

    def test_no_request_falls_back_to_localhost(self, monkeypatch):
        monkeypatch.delenv("MCP_BASE_URL", raising=False)
        monkeypatch.setenv("MCP_PORT", "8000")
        monkeypatch.setenv("MCP_HOST", "0.0.0.0")
        assert routes._get_base_url() == "http://localhost:8000"

    def test_allowlist_rejette_host_non_liste(self, monkeypatch):
        monkeypatch.delenv("MCP_BASE_URL", raising=False)
        monkeypatch.setenv("MCP_ALLOWED_HOSTS", "mcp.example.org")
        monkeypatch.setenv("MCP_PORT", "8000")
        monkeypatch.setenv("MCP_HOST", "0.0.0.0")
        req = self._req({"host": "evil.com"})
        assert routes._get_base_url(req) == "http://localhost:8000"

    def test_allowlist_accepte_host_liste(self, monkeypatch):
        monkeypatch.delenv("MCP_BASE_URL", raising=False)
        monkeypatch.setenv("MCP_ALLOWED_HOSTS", "mcp.example.org, autre.example")
        req = self._req({"host": "mcp.example.org:8002"}, scheme="https")
        assert routes._get_base_url(req) == "https://mcp.example.org:8002"

    def test_scheme_invalide_ecarte(self, monkeypatch):
        monkeypatch.delenv("MCP_BASE_URL", raising=False)
        monkeypatch.delenv("MCP_ALLOWED_HOSTS", raising=False)
        req = self._req({"x-forwarded-host": "mcp.example.org", "x-forwarded-proto": "javascript"}, scheme="https")
        url = routes._get_base_url(req)
        assert "javascript" not in url
        assert url in ("https://mcp.example.org", "http://mcp.example.org")
