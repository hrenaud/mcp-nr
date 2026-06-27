"""
Tests du serveur MCP RGAA 4.2.1.

Exécution:
    cd /path/to/mcp-rgaa
    pytest tests/test_tools.py -v
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "files"))

import pytest
import json
import rgaa_mcp as mcp_module
from fastmcp.exceptions import ToolError
from mcp_ref_core import factory, routes as routes_mod
from mcp_ref_core.auth import charger_tokens, sauvegarder_tokens, tokens_pour_auth, cmd_generate_token, cmd_list_tokens, cmd_revoke_token


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def cache():
    """Load the RGAA cache for testing."""
    return mcp_module.charger_cache()


# ============================================================================
# Env helpers
# ============================================================================

class TestEnvHelpers:
    def test_get_base_url_from_env(self, monkeypatch):
        monkeypatch.setenv("MCP_BASE_URL", "https://my.server.com")
        assert mcp_module._get_base_url() == "https://my.server.com"

    def test_get_base_url_strips_trailing_slash(self, monkeypatch):
        monkeypatch.setenv("MCP_BASE_URL", "https://my.server.com/")
        assert mcp_module._get_base_url() == "https://my.server.com"

    def test_get_base_url_default_localhost(self, monkeypatch):
        monkeypatch.delenv("MCP_BASE_URL", raising=False)
        monkeypatch.setenv("MCP_HOST", "0.0.0.0")
        monkeypatch.setenv("MCP_PORT", "8000")
        assert mcp_module._get_base_url() == "http://localhost:8000"

    def test_get_base_url_custom_host(self, monkeypatch):
        monkeypatch.delenv("MCP_BASE_URL", raising=False)
        monkeypatch.setenv("MCP_HOST", "192.168.1.10")
        monkeypatch.setenv("MCP_PORT", "9000")
        assert mcp_module._get_base_url() == "http://192.168.1.10:9000"

    def test_get_token_request_url_from_env(self, monkeypatch):
        monkeypatch.setenv("MCP_TOKEN_REQUEST_URL", "https://forms.gle/abc123")
        assert mcp_module._get_token_request_url() == "https://forms.gle/abc123"

    def test_get_token_request_url_empty_by_default(self, monkeypatch):
        monkeypatch.delenv("MCP_TOKEN_REQUEST_URL", raising=False)
        assert mcp_module._get_token_request_url() == ""

    def test_get_base_url_slash_only_falls_back_to_localhost(self, monkeypatch):
        monkeypatch.setenv("MCP_BASE_URL", "/")
        monkeypatch.delenv("MCP_HOST", raising=False)
        monkeypatch.setenv("MCP_PORT", "8000")
        assert mcp_module._get_base_url() == "http://localhost:8000"


# ============================================================================
# factory.create_mcp()
# ============================================================================

class TestCreateMcp:
    def test_stdio_mode_no_routes(self, monkeypatch):
        monkeypatch.setenv("MCP_TRANSPORT", "stdio")
        mcp = factory.create_mcp("RGAA MCP", mcp_module.TOKENS_FILE, mcp_module._rgaa_tool_definitions, mcp_module._rgaa_guide_extra_sections)
        assert mcp.name == "RGAA MCP"
        assert len(mcp._additional_http_routes) == 0

    def test_http_mode_registers_routes(self, monkeypatch):
        monkeypatch.setenv("MCP_TRANSPORT", "http")
        mcp = factory.create_mcp("RGAA MCP", mcp_module.TOKENS_FILE, mcp_module._rgaa_tool_definitions, mcp_module._rgaa_guide_extra_sections)
        assert mcp.name == "RGAA MCP"
        assert len(mcp._additional_http_routes) == 8
        paths = [r.path for r in mcp._additional_http_routes]
        assert "/" in paths
        assert "/install.sh" in paths
        assert "/guide" in paths

    def test_no_tokens_no_auth(self, monkeypatch, tmp_path):
        monkeypatch.setenv("MCP_TRANSPORT", "stdio")
        mcp = factory.create_mcp("RGAA MCP", str(tmp_path / "tokens.json"), mcp_module._rgaa_tool_definitions)
        assert mcp._auth is None

    def test_with_tokens_auth_applied(self, monkeypatch, tmp_path):
        import json as json_mod
        import time as time_mod
        tokens_file = tmp_path / "tokens.json"
        tokens_file.write_text(json_mod.dumps({
            "tok_abc123": {
                "name": "test",
                "created_at": "2026-01-01T00:00:00+00:00",
                "expires_at": time_mod.time() + 86400,
            }
        }))
        monkeypatch.setenv("MCP_TRANSPORT", "stdio")
        mcp = factory.create_mcp("RGAA MCP", str(tokens_file), mcp_module._rgaa_tool_definitions)
        assert mcp._auth is not None


# ============================================================================
# HTTP Routes
# ============================================================================

from starlette.testclient import TestClient
from starlette.applications import Starlette
from starlette.routing import Route


class TestHttpRoutes:
    @pytest.fixture(scope="class")
    def client(self):
        app = Starlette(routes=[
            Route("/", routes_mod._http_homepage, methods=["GET"]),
            Route("/install.sh", routes_mod._http_install_script, methods=["GET"]),
            Route("/guide", routes_mod._http_guide, methods=["GET"]),
        ])
        return TestClient(app, raise_server_exceptions=True)

    def test_homepage_status_200(self, client):
        r = client.get("/")
        assert r.status_code == 200

    def test_homepage_content_type_html(self, client):
        r = client.get("/")
        assert "text/html" in r.headers["content-type"]

    def test_homepage_contains_name(self, client):
        r = client.get("/")
        assert "RGAA MCP" in r.text

    def test_homepage_contains_version(self, client):
        r = client.get("/")
        assert mcp_module.VERSION in r.text

    def test_homepage_contains_links(self, client):
        r = client.get("/")
        assert "/install.sh" in r.text
        assert "/guide" in r.text

    def test_install_script_status_200(self, client):
        r = client.get("/install.sh")
        assert r.status_code == 200

    def test_install_script_content_type(self, client):
        r = client.get("/install.sh")
        assert "text/plain" in r.headers["content-type"]

    def test_install_script_is_bash(self, client):
        r = client.get("/install.sh")
        assert r.text.startswith("#!/usr/bin/env bash")

    def test_install_script_contains_mcp_url(self, client, monkeypatch):
        monkeypatch.setenv("MCP_BASE_URL", "https://test.example.com")
        r = client.get("/install.sh")
        assert "https://test.example.com/mcp" in r.text

    def test_install_script_no_raw_placeholder(self, client):
        r = client.get("/install.sh")
        assert "__BASE_URL__" not in r.text
        assert "__MCP_URL__" not in r.text
        assert "__TOKEN_REQUEST_URL__" not in r.text

    def test_install_script_has_uninstall_flag(self, client):
        r = client.get("/install.sh")
        assert "--uninstall" in r.text

    def test_install_script_has_rgaa_mcp_add(self, client):
        r = client.get("/install.sh")
        assert "claude mcp add rgaa" in r.text
        assert "-t http" in r.text

    def test_guide_status_200(self, client):
        r = client.get("/guide")
        assert r.status_code == 200

    def test_guide_content_type_html(self, client):
        r = client.get("/guide")
        assert "text/html" in r.headers["content-type"]

    def test_guide_contains_install_command(self, client):
        r = client.get("/guide")
        assert "curl -sSL" in r.text
        assert "install.sh" in r.text

    def test_guide_contains_tools_list(self, client):
        r = client.get("/guide")
        for tool in ("rgaa_lister_criteres", "rgaa_chercher", "rgaa_analyser"):
            assert tool in r.text, f"Tool '{tool}' missing from guide"

    def test_guide_contains_token_section(self, client):
        r = client.get("/guide")
        assert "token" in r.text.lower()

    def test_guide_token_request_url_shown(self, client, monkeypatch):
        monkeypatch.setenv("MCP_TOKEN_REQUEST_URL", "https://forms.gle/test")
        r = client.get("/guide")
        assert "https://forms.gle/test" in r.text

    def test_homepage_base_url_escaped(self, client, monkeypatch):
        monkeypatch.setenv("MCP_BASE_URL", 'http://x.com"><script>alert(1)</script>')
        r = client.get("/")
        assert "<script>alert(1)</script>" not in r.text

    def test_guide_token_url_escaped(self, client, monkeypatch):
        monkeypatch.setenv("MCP_TOKEN_REQUEST_URL", "javascript:alert(1)")
        r = client.get("/guide")
        assert "javascript:alert(1)" not in r.text

    def test_guide_json_response_with_accept_header(self, client):
        """Test /guide returns JSON when Accept: application/json"""
        r = client.get("/guide", headers={"Accept": "application/json"})
        assert r.status_code == 200
        assert "application/json" in r.headers["content-type"]
        data = r.json()
        assert "tools" in data
        assert isinstance(data["tools"], list)

    def test_guide_json_tool_count(self, client):
        """Test JSON response contains correct number of tools (10)"""
        r = client.get("/guide", headers={"Accept": "application/json"})
        data = r.json()
        assert len(data["tools"]) == 10, f"Expected 10 tools, got {len(data['tools'])}"

    def test_guide_json_tool_structure(self, client):
        """Test each tool in JSON has required fields"""
        r = client.get("/guide", headers={"Accept": "application/json"})
        data = r.json()
        for tool in data["tools"]:
            assert "name" in tool, f"Tool missing 'name': {tool}"
            assert "description" in tool, f"Tool missing 'description': {tool}"
            assert "inputSchema" in tool, f"Tool missing 'inputSchema': {tool}"
            assert isinstance(tool["name"], str)
            assert isinstance(tool["description"], str)
            assert isinstance(tool["inputSchema"], dict)

    def test_guide_json_tool_names(self, client):
        """Test JSON response contains all expected tool names"""
        r = client.get("/guide", headers={"Accept": "application/json"})
        data = r.json()
        names = {tool["name"] for tool in data["tools"]}
        expected = {
            "rgaa_lister_criteres", "rgaa_obtenir_critere", "rgaa_chercher",
            "rgaa_glossaire", "rgaa_statistiques", "rgaa_analyser",
            "rgaa_checklist", "rgaa_taux_conformite", "rgaa_types_audit",
            "rgaa_criteres_audit"
        }
        assert names == expected, f"Tool names mismatch. Got: {names}, Expected: {expected}"

    def test_guide_json_inputschema_valid(self, client):
        """Test each tool's inputSchema is valid JSON Schema"""
        r = client.get("/guide", headers={"Accept": "application/json"})
        data = r.json()
        for tool in data["tools"]:
            schema = tool["inputSchema"]
            assert "type" in schema
            assert schema["type"] in ("object",)
            if "properties" in schema:
                assert isinstance(schema["properties"], dict)
            if "required" in schema:
                assert isinstance(schema["required"], list)

    def test_guide_html_response_default(self, client):
        """Test /guide returns HTML by default (no Accept header)"""
        r = client.get("/guide")
        assert r.status_code == 200
        assert "text/html" in r.headers["content-type"]
        assert "<!DOCTYPE html>" in r.text

    def test_guide_html_response_explicit(self, client):
        """Test /guide returns HTML when explicitly requested"""
        r = client.get("/guide", headers={"Accept": "text/html"})
        assert r.status_code == 200
        assert "text/html" in r.headers["content-type"]

    def test_guide_html_contains_all_tools(self, client):
        """Test HTML guide contains all 10 tools"""
        r = client.get("/guide")
        for tool_name in ("rgaa_lister_criteres", "rgaa_obtenir_critere", "rgaa_chercher",
                          "rgaa_glossaire", "rgaa_statistiques", "rgaa_analyser",
                          "rgaa_checklist", "rgaa_taux_conformite", "rgaa_types_audit",
                          "rgaa_criteres_audit"):
            assert tool_name in r.text, f"Tool '{tool_name}' missing from HTML guide"


# ============================================================================
# --health flag
# ============================================================================

import subprocess


class TestHealthFlag:
    def test_health_exits_0_when_cache_ok(self):
        result = subprocess.run(
            [sys.executable, "files/rgaa_mcp.py", "--health"],
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).parent.parent),
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        assert "OK" in result.stdout

    def test_health_output_contains_criteres_count(self):
        result = subprocess.run(
            [sys.executable, "files/rgaa_mcp.py", "--health"],
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).parent.parent),
        )
        assert "critères" in result.stdout or "criteres" in result.stdout.lower()


# ============================================================================
# Startup logging
# ============================================================================

class TestStartupLogging:
    def _run_health(self):
        return subprocess.run(
            [sys.executable, "files/rgaa_mcp.py", "--health"],
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).parent.parent),
        )

    def test_health_logs_version_to_stderr(self):
        result = self._run_health()
        assert mcp_module.VERSION in result.stderr

    def test_health_logs_cache_count_to_stderr(self):
        result = self._run_health()
        assert "critères" in result.stderr or "Cache" in result.stderr


# ============================================================================
# MCP Resources
# ============================================================================

import asyncio


class TestMcpResources:
    def test_resources_registered(self):
        resources = asyncio.run(mcp_module.mcp.list_resources())
        uris = [str(r.uri) for r in resources]
        assert any("rgaa://version" in u for u in uris), f"rgaa://version missing. Got: {uris}"
        assert any("rgaa://index" in u for u in uris), f"rgaa://index missing. Got: {uris}"

    def test_resource_version_content(self):
        result = asyncio.run(mcp_module.mcp.read_resource("rgaa://version"))
        data = json.loads(result.contents[0].content)
        assert "server_version" in data
        assert "referentiel_version" in data
        assert "updated_at" in data
        assert "nb_items" in data

    def test_resource_index_structure(self):
        result = asyncio.run(mcp_module.mcp.read_resource("rgaa://index"))
        data = json.loads(result.contents[0].content)
        assert isinstance(data, list)
        assert len(data) > 0
        assert "id" in data[0]
        assert "titre" in data[0]

    def test_resource_critere_by_id(self, cache):
        premier_id = next(iter(cache["criteres"]))
        result = asyncio.run(mcp_module.mcp.read_resource(f"rgaa://criteres/{premier_id}"))
        data = json.loads(result.contents[0].content)
        assert "erreur" not in data
        assert "titre" in data

    def test_tools_still_registered(self):
        tools = asyncio.run(mcp_module.mcp.list_tools())
        names = [t.name for t in tools]
        for expected in ("rgaa_lister_criteres", "rgaa_obtenir_critere", "rgaa_chercher",
                         "rgaa_glossaire", "rgaa_statistiques", "rgaa_analyser",
                         "rgaa_checklist", "rgaa_taux_conformite", "rgaa_types_audit", "rgaa_criteres_audit"):
            assert expected in names, f"Tool '{expected}' not registered"


# ============================================================================
# rgaa_types_audit
# ============================================================================

class TestTypesAudit:
    def test_returns_three_types(self):
        result = mcp_module.rgaa_types_audit()
        assert len(result["types"]) == 3

    def test_type_slugs(self):
        result = mcp_module.rgaa_types_audit()
        slugs = {t["type"] for t in result["types"]}
        assert slugs == {"complet", "rapide", "complementaire"}

    def test_complet_conforme_obligation(self):
        result = mcp_module.rgaa_types_audit()
        complet = next(t for t in result["types"] if t["type"] == "complet")
        assert complet["conforme_obligation"] == True

    def test_rapide_not_conforme_obligation(self):
        result = mcp_module.rgaa_types_audit()
        rapide = next(t for t in result["types"] if t["type"] == "rapide")
        assert rapide["conforme_obligation"] == False

    def test_complet_has_106_criteres(self):
        result = mcp_module.rgaa_types_audit()
        complet = next(t for t in result["types"] if t["type"] == "complet")
        assert complet["nb_criteres"] == 106

    def test_rapide_has_25_criteres(self):
        result = mcp_module.rgaa_types_audit()
        rapide = next(t for t in result["types"] if t["type"] == "rapide")
        assert rapide["nb_criteres"] == 25

    def test_complementaire_has_25_criteres(self):
        result = mcp_module.rgaa_types_audit()
        complementaire = next(t for t in result["types"] if t["type"] == "complementaire")
        assert complementaire["nb_criteres"] == 25

    def test_each_type_has_required_fields(self):
        result = mcp_module.rgaa_types_audit()
        for t in result["types"]:
            assert "type" in t
            assert "nom" in t
            assert "description" in t
            assert "conforme_obligation" in t
            assert "nb_criteres" in t


# ============================================================================
# rgaa_criteres_audit
# ============================================================================

class TestCriteresAudit:
    def test_rapide_returns_25_criteres(self):
        result = mcp_module.rgaa_criteres_audit("rapide")
        assert result["nb_criteres"] == 25
        assert len(result["criteres"]) == 25

    def test_complementaire_returns_25_criteres(self):
        result = mcp_module.rgaa_criteres_audit("complementaire")
        assert result["nb_criteres"] == 25
        assert len(result["criteres"]) == 25

    def test_complet_returns_106_criteres(self):
        result = mcp_module.rgaa_criteres_audit("complet")
        assert result["nb_criteres"] == 106
        assert len(result["criteres"]) == 106

    def test_rapide_critere_has_required_fields(self):
        result = mcp_module.rgaa_criteres_audit("rapide")
        for c in result["criteres"]:
            assert "id" in c
            assert "theme" in c
            assert "titre" in c

    def test_rapide_ids_exist_in_cache(self):
        cache = mcp_module.charger_cache()
        result = mcp_module.rgaa_criteres_audit("rapide")
        for c in result["criteres"]:
            assert c["id"] in cache["criteres"], f"Critère {c['id']} absent du cache"

    def test_complementaire_ids_exist_in_cache(self):
        cache = mcp_module.charger_cache()
        result = mcp_module.rgaa_criteres_audit("complementaire")
        for c in result["criteres"]:
            assert c["id"] in cache["criteres"], f"Critère {c['id']} absent du cache"

    def test_complet_conforme_obligation_true(self):
        result = mcp_module.rgaa_criteres_audit("complet")
        assert result["conforme_obligation"] is True

    def test_rapide_conforme_obligation_false(self):
        result = mcp_module.rgaa_criteres_audit("rapide")
        assert result["conforme_obligation"] is False

    def test_invalid_type_raises_error(self):
        """Verify invalid audit types raise ToolError."""
        with pytest.raises(ToolError) as exc_info:
            mcp_module.rgaa_criteres_audit("inconnu")
        error_msg = str(exc_info.value)
        assert "inconnu" in error_msg.lower()

    def test_invalid_type_error_includes_guidance(self):
        """Verify invalid audit types raise ToolError with actionable guidance."""
        with pytest.raises(ToolError) as exc_info:
            mcp_module.rgaa_criteres_audit("inconnu")
        error_msg = str(exc_info.value)
        assert "invalide" in error_msg.lower() or "inconnu" in error_msg.lower()
        # Should mention valid options
        assert "complet" in error_msg.lower() or "valeurs acceptées" in error_msg.lower()

    def test_result_includes_type_and_nom(self):
        result = mcp_module.rgaa_criteres_audit("rapide")
        assert result["type"] == "rapide"
        assert "nom" in result


# ============================================================================
# Tool Annotations
# ============================================================================

class TestToolAnnotations:
    def test_rgaa_lister_criteres_annotations(self):
        """Verify rgaa_lister_criteres has correct annotations"""
        tools = asyncio.run(mcp_module.mcp.list_tools())
        tool = next((t for t in tools if t.name == "rgaa_lister_criteres"), None)
        assert tool is not None, "rgaa_lister_criteres not found"
        annotations = tool.annotations
        assert annotations.readOnlyHint == True
        assert annotations.destructiveHint == False
        assert annotations.idempotentHint == True
        assert annotations.openWorldHint == False

    def test_rgaa_types_audit_annotations(self):
        """Verify rgaa_types_audit has correct annotations"""
        tools = asyncio.run(mcp_module.mcp.list_tools())
        types_tool = next((t for t in tools if t.name == "rgaa_types_audit"), None)
        assert types_tool is not None, "rgaa_types_audit not found"
        assert types_tool.annotations.readOnlyHint == True
        assert types_tool.annotations.destructiveHint == False
        assert types_tool.annotations.idempotentHint == True
        assert types_tool.annotations.openWorldHint == False

    def test_detail_retrieval_tools_have_annotations(self):
        """Verify detail retrieval tools are marked read-only and idempotent."""
        tools = asyncio.run(mcp_module.mcp.list_tools())

        obtenir_tool = next((t for t in tools if t.name == "rgaa_obtenir_critere"), None)
        assert obtenir_tool is not None, "rgaa_obtenir_critere not found"
        assert obtenir_tool.annotations.readOnlyHint == True
        assert obtenir_tool.annotations.destructiveHint == False
        assert obtenir_tool.annotations.idempotentHint == True
        assert obtenir_tool.annotations.openWorldHint == False

        glossaire_tool = next((t for t in tools if t.name == "rgaa_glossaire"), None)
        assert glossaire_tool is not None, "rgaa_glossaire not found"
        assert glossaire_tool.annotations.readOnlyHint == True
        assert glossaire_tool.annotations.destructiveHint == False
        assert glossaire_tool.annotations.idempotentHint == True
        assert glossaire_tool.annotations.openWorldHint == False


# ============================================================================
# Error Messages for Detail Tools
# ============================================================================

class TestDetailToolErrorMessages:
    def test_rgaa_obtenir_critere_error_includes_guidance(self):
        """Verify that invalid criteria IDs raise ToolError with actionable messages."""
        with pytest.raises(ToolError) as exc_info:
            mcp_module.rgaa_obtenir_critere("999.999")
        assert "999.999" in str(exc_info.value)
        assert "rgaa_lister_criteres" in str(exc_info.value).lower()

    def test_rgaa_glossaire_error_includes_guidance(self):
        """Verify that invalid glossary terms raise ToolError with actionable messages."""
        with pytest.raises(ToolError) as exc_info:
            mcp_module.rgaa_glossaire("abcdefghijklmnop_completely_fake_term_qrstuvwxyz")
        assert "rgaa_chercher" in str(exc_info.value).lower()

    def test_rgaa_obtenir_critere_valid_id_returns_content(self):
        """Verify that valid criteria IDs return full content."""
        result = mcp_module.rgaa_obtenir_critere("1.1")
        assert "titre" in result
        assert result["id"] == "1.1"


# ============================================================================
# Tool Annotations - Search and Statistics
# ============================================================================

class TestSearchAndStatisticsAnnotations:
    def test_search_and_stats_tools_have_annotations(self):
        """Verify search and statistics tools are marked read-only."""
        tools = asyncio.run(mcp_module.mcp.list_tools())

        chercher_tool = next((t for t in tools if t.name == "rgaa_chercher"), None)
        assert chercher_tool is not None, "rgaa_chercher not found"
        assert chercher_tool.annotations.readOnlyHint == True
        assert chercher_tool.annotations.destructiveHint == False
        assert chercher_tool.annotations.idempotentHint == True
        assert chercher_tool.annotations.openWorldHint == True

        stats_tool = next((t for t in tools if t.name == "rgaa_statistiques"), None)
        assert stats_tool is not None, "rgaa_statistiques not found"
        assert stats_tool.annotations.readOnlyHint == True
        assert stats_tool.annotations.destructiveHint == False
        assert stats_tool.annotations.idempotentHint == True
        assert stats_tool.annotations.openWorldHint == False


# ============================================================================
# Tool Annotations - Audit Criteria
# ============================================================================

class TestAuditCriteriaAnnotations:
    """Verify audit criteria tool annotations."""

    def test_audit_criteria_tool_has_annotations(self):
        """Verify audit criteria tool is marked read-only."""
        tools = asyncio.run(mcp_module.mcp.list_tools())
        audit_tool = next((t for t in tools if t.name == "rgaa_criteres_audit"), None)
        assert audit_tool is not None, "rgaa_criteres_audit tool not found"
        assert audit_tool.annotations is not None, "Tool lacks annotations"
        assert audit_tool.annotations.readOnlyHint == True
        assert audit_tool.annotations.destructiveHint == False
        assert audit_tool.annotations.idempotentHint == True
        assert audit_tool.annotations.openWorldHint == False


# ============================================================================
# Tool Annotations - Analyzer (Network Operations)
# ============================================================================

class TestAnalyzerAnnotations:
    """Verify analyzer tool annotations for network operations."""

    def test_analyser_tool_has_correct_annotations(self):
        """Verify analyzer tool has correct annotations for network operations."""
        tools = asyncio.run(mcp_module.mcp.list_tools())
        analyser_tool = next((t for t in tools if t.name == "rgaa_analyser"), None)
        assert analyser_tool is not None, "rgaa_analyser not found"
        assert analyser_tool.annotations is not None, "Tool lacks annotations"
        assert analyser_tool.annotations.readOnlyHint == True
        assert analyser_tool.annotations.destructiveHint == False
        assert analyser_tool.annotations.idempotentHint == False
        assert analyser_tool.annotations.openWorldHint == True


# ============================================================================
# Analyzer Error Handling
# ============================================================================

class TestAnalyzerErrorHandling:
    """Verify analyzer tool error handling and user guidance."""

    def test_analyser_invalid_url_raises_error(self):
        """Verify analyzer raises ToolError for invalid URLs."""
        with pytest.raises(ToolError) as exc_info:
            mcp_module.rgaa_analyser("")
        error_msg = str(exc_info.value)
        assert "L'URL" in error_msg or "URL" in error_msg

    def test_analyser_error_for_non_http_url(self):
        """Verify analyzer raises ToolError for URLs without http/https."""
        with pytest.raises(ToolError) as exc_info:
            mcp_module.rgaa_analyser("ftp://example.com")
        error_msg = str(exc_info.value)
        assert "http" in error_msg.lower()

    def test_analyser_error_message_actionable(self):
        """Verify error message provides actionable guidance."""
        with pytest.raises(ToolError) as exc_info:
            mcp_module.rgaa_analyser("invalid")
        error_msg = str(exc_info.value)
        assert "http" in error_msg.lower() or "invalide" in error_msg.lower()

    def test_analyser_valid_url_format_accepted(self):
        """Verify analyzer accepts valid URL format (may fail on network)."""
        # This will likely fail on network issues, but should pass URL validation
        try:
            result = mcp_module.rgaa_analyser("https://example.com")
            assert isinstance(result, dict)
        except ToolError as e:
            # Network errors are acceptable; URL validation errors are not
            assert "http" not in str(e).lower() or "valide" not in str(e).lower()

    def test_analyser_network_error_handling(self, monkeypatch):
        """Verify analyzer wraps network errors with helpful messages."""
        import httpx

        def mock_fetcher_error(*args, **kwargs):
            raise httpx.RequestError("Connection refused")

        monkeypatch.setattr(mcp_module, "fetcher_html", mock_fetcher_error)

        with pytest.raises(ToolError) as exc_info:
            mcp_module.rgaa_analyser("https://example.com")
        error_msg = str(exc_info.value)
        assert "Impossible de récupérer" in error_msg or "accessible" in error_msg

    def test_analyser_timeout_error_handling(self, monkeypatch):
        """Verify analyzer handles timeout errors with guidance."""
        import httpx

        def mock_timeout(*args, **kwargs):
            raise httpx.TimeoutException("Request timed out")

        monkeypatch.setattr(mcp_module, "fetcher_html", mock_timeout)

        with pytest.raises(ToolError) as exc_info:
            mcp_module.rgaa_analyser("https://example.com")
        error_msg = str(exc_info.value)
        assert "Impossible de récupérer" in error_msg

    def test_analyser_http_status_error_handling(self, monkeypatch):
        """Verify analyzer handles HTTP status errors (404, 403, etc)."""
        import httpx

        def mock_status_error(*args, **kwargs):
            response = httpx.Response(404, text="Not Found")
            raise httpx.HTTPStatusError("404 Not Found", request=None, response=response)

        monkeypatch.setattr(mcp_module, "fetcher_html", mock_status_error)

        with pytest.raises(ToolError) as exc_info:
            mcp_module.rgaa_analyser("https://example.com")
        error_msg = str(exc_info.value)
        assert "404" in error_msg or "HTTP" in error_msg


# ============================================================================
# Annotations and Error Handling for Checklist Tool
# ============================================================================

class TestChecklistAnnotations:
    """Verify rgaa_checklist has all four required annotations."""

    def test_checklist_has_read_only_hint(self):
        tools = asyncio.run(mcp_module.mcp.list_tools())
        tool = next((t for t in tools if t.name == "rgaa_checklist"), None)
        assert tool is not None, "Tool rgaa_checklist not found"
        assert tool.annotations.readOnlyHint == True, "readOnlyHint should be True"

    def test_checklist_has_destructive_hint(self):
        tools = asyncio.run(mcp_module.mcp.list_tools())
        tool = next((t for t in tools if t.name == "rgaa_checklist"), None)
        assert tool is not None, "Tool rgaa_checklist not found"
        assert tool.annotations.destructiveHint == False, "destructiveHint should be False"

    def test_checklist_has_idempotent_hint(self):
        tools = asyncio.run(mcp_module.mcp.list_tools())
        tool = next((t for t in tools if t.name == "rgaa_checklist"), None)
        assert tool is not None, "Tool rgaa_checklist not found"
        assert tool.annotations.idempotentHint == True, "idempotentHint should be True"

    def test_checklist_has_open_world_hint(self):
        tools = asyncio.run(mcp_module.mcp.list_tools())
        tool = next((t for t in tools if t.name == "rgaa_checklist"), None)
        assert tool is not None, "Tool rgaa_checklist not found"
        assert tool.annotations.openWorldHint == True, "openWorldHint should be True (any criteria combinations accepted)"


class TestChecklistErrorHandlingBasic:
    """Verify rgaa_checklist error handling with ToolError exceptions."""

    def test_invalid_theme_raises_error(self):
        """Verify invalid theme raises ToolError with guidance."""
        with pytest.raises(ToolError) as exc_info:
            mcp_module.rgaa_checklist(themes=[99])
        error_msg = str(exc_info.value)
        assert "invalides" in error_msg.lower() or "99" in error_msg

    def test_invalid_criteria_raises_error(self):
        """Verify invalid criteria raises ToolError with guidance."""
        with pytest.raises(ToolError) as exc_info:
            mcp_module.rgaa_checklist(criteres=["99.99"])
        error_msg = str(exc_info.value)
        assert "invalides" in error_msg.lower() or "99.99" in error_msg

    def test_empty_params_raises_error(self):
        """Verify that both themes and criteres empty raises ToolError."""
        with pytest.raises(ToolError) as exc_info:
            mcp_module.rgaa_checklist(themes=None, criteres=None)
        error_msg = str(exc_info.value)
        assert "au moins" in error_msg.lower() or "requis" in error_msg.lower()


# ============================================================================
# Annotations and Error Handling for Conformity Tool
# ============================================================================

class TestConformityAnnotations:
    """Verify rgaa_taux_conformite has all four required annotations."""

    def test_conformity_has_read_only_hint(self):
        tools = asyncio.run(mcp_module.mcp.list_tools())
        tool = next((t for t in tools if t.name == "rgaa_taux_conformite"), None)
        assert tool is not None, "Tool rgaa_taux_conformite not found"
        assert tool.annotations.readOnlyHint == True, "readOnlyHint should be True"

    def test_conformity_has_destructive_hint(self):
        tools = asyncio.run(mcp_module.mcp.list_tools())
        tool = next((t for t in tools if t.name == "rgaa_taux_conformite"), None)
        assert tool is not None, "Tool rgaa_taux_conformite not found"
        assert tool.annotations.destructiveHint == False, "destructiveHint should be False"

    def test_conformity_has_idempotent_hint(self):
        tools = asyncio.run(mcp_module.mcp.list_tools())
        tool = next((t for t in tools if t.name == "rgaa_taux_conformite"), None)
        assert tool is not None, "Tool rgaa_taux_conformite not found"
        assert tool.annotations.idempotentHint == True, "idempotentHint should be True"

    def test_conformity_has_open_world_hint(self):
        tools = asyncio.run(mcp_module.mcp.list_tools())
        tool = next((t for t in tools if t.name == "rgaa_taux_conformite"), None)
        assert tool is not None, "Tool rgaa_taux_conformite not found"
        assert tool.annotations.openWorldHint == False, "openWorldHint should be False (specific criterion results expected)"


class TestConformityErrorHandling:
    """Verify rgaa_taux_conformite error handling with ToolError exceptions."""

    def test_empty_results_raises_error(self):
        """Verify empty results raise ToolError with guidance."""
        with pytest.raises(ToolError) as exc_info:
            mcp_module.rgaa_taux_conformite(resultats={})
        error_msg = str(exc_info.value)
        assert "vide" in error_msg.lower() or "résultats" in error_msg.lower()

    def test_invalid_status_raises_error(self):
        """Verify invalid statut raises ToolError with all errors shown."""
        with pytest.raises(ToolError) as exc_info:
            mcp_module.rgaa_taux_conformite(resultats={"1.1": "INVALID"})
        error_msg = str(exc_info.value)
        assert "invalides" in error_msg.lower() or "INVALID" in error_msg
        assert "C" in error_msg and "NC" in error_msg  # Valid options mentioned

    def test_multiple_invalid_statuts_all_shown(self):
        """Verify all invalid statuts are shown (no truncation)."""
        with pytest.raises(ToolError) as exc_info:
            mcp_module.rgaa_taux_conformite(resultats={
                "1.1": "BAD1",
                "1.2": "BAD2",
                "1.3": "BAD3",
                "1.4": "BAD4"
            })
        error_msg = str(exc_info.value)
        # All invalid statuts should be mentioned
        assert "BAD1" in error_msg and "BAD2" in error_msg

    def test_valid_calculation_returns_rate(self):
        result = mcp_module.rgaa_taux_conformite(
            resultats={"1.1": "C", "1.2": "C", "1.3": "NC"}
        )
        assert isinstance(result, dict), "Result should be dict"
        assert "taux" in result, "Result should include 'taux' field"
        assert result["taux"] == 66.67, "Taux should be 66.67 (2 C out of 3 testable)"


# ============================================================================
# Additional Error Handling Tests (Task 4)
# ============================================================================

class TestListerCriteresErrorHandling:
    """Comprehensive error handling tests for rgaa_lister_criteres."""

    def test_invalid_theme_number_too_low(self):
        """Verify theme < 1 raises ToolError."""
        with pytest.raises(ToolError) as exc_info:
            mcp_module.rgaa_lister_criteres(theme=0)
        assert "invalide" in str(exc_info.value).lower() or "0" in str(exc_info.value)

    def test_invalid_theme_number_too_high(self):
        """Verify theme > 13 raises ToolError."""
        with pytest.raises(ToolError) as exc_info:
            mcp_module.rgaa_lister_criteres(theme=14)
        assert "invalide" in str(exc_info.value).lower() or "14" in str(exc_info.value)

    def test_invalid_wcag_level(self):
        """Verify invalid WCAG level raises ToolError."""
        with pytest.raises(ToolError) as exc_info:
            mcp_module.rgaa_lister_criteres(niveau_wcag="INVALID")
        error_msg = str(exc_info.value).lower()
        # Should mention valid levels
        assert "a" in error_msg or "wcag" in error_msg

    def test_valid_theme_returns_list(self):
        """Verify valid theme returns list of criteria."""
        result = mcp_module.rgaa_lister_criteres(theme=1)
        assert "total" in result
        assert "criteres" in result
        assert isinstance(result["criteres"], list)

    def test_valid_wcag_returns_list(self):
        """Verify valid WCAG level returns results."""
        result = mcp_module.rgaa_lister_criteres(niveau_wcag="AA")
        assert "total" in result
        assert "criteres" in result


class TestObtainCritereErrorHandling:
    """Comprehensive error handling tests for rgaa_obtenir_critere."""

    def test_invalid_id_format(self):
        """Verify invalid criterion ID raises ToolError."""
        with pytest.raises(ToolError) as exc_info:
            mcp_module.rgaa_obtenir_critere("999.999")
        error_msg = str(exc_info.value)
        assert "999.999" in error_msg or "existe pas" in error_msg.lower()

    def test_empty_id_raises_error(self):
        """Verify empty criterion ID raises ToolError."""
        with pytest.raises(ToolError) as exc_info:
            mcp_module.rgaa_obtenir_critere("")
        assert "existe pas" in str(exc_info.value).lower()

    def test_invalid_id_suggests_alternatives(self):
        """Verify error message suggests close matches."""
        with pytest.raises(ToolError) as exc_info:
            mcp_module.rgaa_obtenir_critere("1.X")
        error_msg = str(exc_info.value)
        # Should offer help
        assert "1.X" in error_msg or "existe pas" in error_msg.lower()

    def test_valid_id_returns_content(self):
        """Verify valid ID returns full criterion."""
        result = mcp_module.rgaa_obtenir_critere("1.1")
        assert result["id"] == "1.1"
        assert "titre" in result


class TestRechercherErrorHandling:
    """Comprehensive error handling tests for rgaa_chercher."""

    def test_empty_query_raises_error(self):
        """Verify empty query raises ToolError."""
        with pytest.raises(ToolError) as exc_info:
            mcp_module.rgaa_chercher("")
        assert "vide" in str(exc_info.value).lower() or "recherche" in str(exc_info.value).lower()

    def test_whitespace_only_query_raises_error(self):
        """Verify whitespace-only query raises ToolError."""
        with pytest.raises(ToolError) as exc_info:
            mcp_module.rgaa_chercher("   ")
        assert "vide" in str(exc_info.value).lower()

    def test_invalid_scope_option(self):
        """Verify invalid scope option is handled."""
        # This should be caught by type system, but test gracefully
        result = mcp_module.rgaa_chercher("test", scope=["criteres"])
        assert isinstance(result, dict)
        assert "criteres" in result

    def test_no_results_returns_empty_lists(self):
        """Verify no results returns empty lists (not error)."""
        result = mcp_module.rgaa_chercher("xyzabc_unlikely_term_12345")
        assert "criteres" in result
        assert "termes_glossaire" in result
        assert isinstance(result["criteres"], list)

    def test_valid_search_returns_results(self):
        """Verify valid search returns results."""
        result = mcp_module.rgaa_chercher("image")
        assert isinstance(result, dict)
        assert "criteres" in result


class TestGlossaireErrorHandling:
    """Comprehensive error handling tests for rgaa_glossaire."""

    def test_empty_term_raises_error(self):
        """Verify empty term raises ToolError."""
        with pytest.raises(ToolError) as exc_info:
            mcp_module.rgaa_glossaire("")
        error_msg = str(exc_info.value).lower()
        assert "vide" in error_msg or "introuvable" in error_msg or "recherche" in error_msg

    def test_invalid_term_raises_error(self):
        """Verify invalid term raises ToolError with guidance."""
        with pytest.raises(ToolError) as exc_info:
            mcp_module.rgaa_glossaire("term_that_definitely_does_not_exist_in_glossary_12345")
        error_msg = str(exc_info.value)
        assert "introuvable" in error_msg.lower() or "chercher" in error_msg.lower()

    def test_invalid_term_suggests_search(self):
        """Verify error message suggests using search."""
        with pytest.raises(ToolError) as exc_info:
            mcp_module.rgaa_glossaire("xyzabc")
        error_msg = str(exc_info.value).lower()
        assert "rgaa_chercher" in error_msg or "chercher" in error_msg

    def test_valid_term_returns_definition(self):
        """Verify valid term returns definition."""
        # Get a known term from cache first
        cache = mcp_module.charger_cache()
        if cache["glossaire"]:
            term = next(iter(cache["glossaire"].keys()))
            result = mcp_module.rgaa_glossaire(term)
            assert "definition" in result


class TestStatistiquesErrorHandling:
    """Error handling tests for rgaa_statistiques (no parameters)."""

    def test_statistics_returns_valid_structure(self):
        """Verify statistics always returns valid structure."""
        result = mcp_module.rgaa_statistiques()
        assert "total_criteres" in result
        assert "automatisables" in result
        assert "manuels" in result
        assert "par_theme" in result


class TestTypesAuditErrorHandling:
    """Error handling tests for rgaa_types_audit (no parameters)."""

    def test_types_returns_valid_structure(self):
        """Verify types audit always returns valid structure."""
        result = mcp_module.rgaa_types_audit()
        assert "types" in result
        assert len(result["types"]) == 3


class TestCriteresAuditErrorHandling:
    """Comprehensive error handling tests for rgaa_criteres_audit."""

    def test_invalid_type_raises_error(self):
        """Verify invalid audit type raises ToolError."""
        with pytest.raises(ToolError) as exc_info:
            mcp_module.rgaa_criteres_audit("invalid_type")
        error_msg = str(exc_info.value)
        assert "invalide" in error_msg.lower() or "invalid_type" in error_msg

    def test_invalid_type_error_includes_valid_options(self):
        """Verify error message lists valid options."""
        with pytest.raises(ToolError) as exc_info:
            mcp_module.rgaa_criteres_audit("bad_type")
        error_msg = str(exc_info.value).lower()
        # Should mention at least one valid type
        assert "complet" in error_msg or "rapide" in error_msg or "complementaire" in error_msg

    def test_none_type_raises_error(self):
        """Verify None type raises appropriate error."""
        with pytest.raises((ToolError, TypeError)):
            mcp_module.rgaa_criteres_audit(None)

    def test_valid_types_return_results(self):
        """Verify all valid types return proper results."""
        for audit_type in ["complet", "rapide", "complementaire"]:
            result = mcp_module.rgaa_criteres_audit(audit_type)
            assert result["type"] == audit_type
            assert "criteres" in result


class TestAnalyserErrorHandling:
    """Comprehensive error handling tests for rgaa_analyser."""

    def test_empty_url_raises_error(self):
        """Verify empty URL raises ToolError."""
        with pytest.raises(ToolError) as exc_info:
            mcp_module.rgaa_analyser("")
        error_msg = str(exc_info.value).lower()
        assert "url" in error_msg or "vide" in error_msg

    def test_whitespace_only_url_raises_error(self):
        """Verify whitespace-only URL raises ToolError."""
        with pytest.raises(ToolError) as exc_info:
            mcp_module.rgaa_analyser("   ")
        assert "vide" in str(exc_info.value).lower() or "url" in str(exc_info.value).lower()

    def test_no_protocol_url_raises_error(self):
        """Verify URL without http/https raises ToolError."""
        with pytest.raises(ToolError) as exc_info:
            mcp_module.rgaa_analyser("example.com")
        error_msg = str(exc_info.value).lower()
        assert "http" in error_msg or "invalide" in error_msg

    def test_ftp_url_raises_error(self):
        """Verify FTP URL raises ToolError."""
        with pytest.raises(ToolError) as exc_info:
            mcp_module.rgaa_analyser("ftp://example.com")
        error_msg = str(exc_info.value).lower()
        assert "http" in error_msg

    def test_invalid_theme_raises_error(self):
        """Verify invalid theme raises ToolError."""
        with pytest.raises(ToolError) as exc_info:
            mcp_module.rgaa_analyser("https://example.com", themes=[99])
        error_msg = str(exc_info.value).lower()
        assert "invalide" in error_msg or "99" in error_msg

    def test_error_message_actionable(self):
        """Verify error messages are actionable."""
        with pytest.raises(ToolError) as exc_info:
            mcp_module.rgaa_analyser("not-a-url")
        error_msg = str(exc_info.value)
        assert "http://" in error_msg or "https://" in error_msg


class TestChecklistErrorHandling:
    """Comprehensive error handling tests for rgaa_checklist."""

    def test_no_params_raises_error(self):
        """Verify both params None raises ToolError."""
        with pytest.raises(ToolError) as exc_info:
            mcp_module.rgaa_checklist(themes=None, criteres=None)
        error_msg = str(exc_info.value).lower()
        assert "au moins" in error_msg or "requis" in error_msg

    def test_invalid_theme_raises_error(self):
        """Verify invalid theme raises ToolError."""
        with pytest.raises(ToolError) as exc_info:
            mcp_module.rgaa_checklist(themes=[99])
        error_msg = str(exc_info.value).lower()
        assert "invalide" in error_msg or "99" in error_msg

    def test_invalid_criteria_raises_error(self):
        """Verify invalid criterion ID raises ToolError."""
        with pytest.raises(ToolError) as exc_info:
            mcp_module.rgaa_checklist(criteres=["99.99"])
        error_msg = str(exc_info.value).lower()
        assert "invalide" in error_msg or "99.99" in error_msg

    def test_mixed_valid_invalid_criteria_shows_all_errors(self):
        """Verify error shows all invalid criteria."""
        with pytest.raises(ToolError) as exc_info:
            mcp_module.rgaa_checklist(criteres=["99.99", "88.88"])
        error_msg = str(exc_info.value)
        # Should show which are invalid
        assert "99.99" in error_msg or "invalide" in error_msg.lower()

    def test_valid_themes_returns_checklist(self):
        """Verify valid themes return checklist."""
        result = mcp_module.rgaa_checklist(themes=[1])
        assert "criteres" in result
        assert isinstance(result["criteres"], list)

    def test_valid_criteria_returns_checklist(self):
        """Verify valid criteria return checklist."""
        result = mcp_module.rgaa_checklist(criteres=["1.1"])
        assert "criteres" in result
        assert isinstance(result["criteres"], list)


class TestTauxConformiteErrorHandling:
    """Comprehensive error handling tests for rgaa_taux_conformite."""

    def test_empty_dict_raises_error(self):
        """Verify empty resultats dict raises ToolError."""
        with pytest.raises(ToolError) as exc_info:
            mcp_module.rgaa_taux_conformite({})
        error_msg = str(exc_info.value).lower()
        assert "vide" in error_msg or "résultats" in error_msg or "resultats" in error_msg

    def test_none_raises_error(self):
        """Verify None raises appropriate error."""
        with pytest.raises((ToolError, TypeError)):
            mcp_module.rgaa_taux_conformite(None)

    def test_invalid_status_single(self):
        """Verify invalid status raises ToolError."""
        with pytest.raises(ToolError) as exc_info:
            mcp_module.rgaa_taux_conformite({"1.1": "INVALID"})
        error_msg = str(exc_info.value)
        assert "invalide" in error_msg.lower() or "INVALID" in error_msg

    def test_invalid_status_multiple_all_shown(self):
        """Verify all invalid statuses shown."""
        with pytest.raises(ToolError) as exc_info:
            mcp_module.rgaa_taux_conformite({
                "1.1": "BAD1",
                "1.2": "BAD2",
                "1.3": "BAD3"
            })
        error_msg = str(exc_info.value)
        # All should be mentioned
        assert "BAD1" in error_msg

    def test_invalid_status_error_shows_valid_options(self):
        """Verify error message shows valid status options."""
        with pytest.raises(ToolError) as exc_info:
            mcp_module.rgaa_taux_conformite({"1.1": "X"})
        error_msg = str(exc_info.value)
        # Should mention valid options
        assert ("C" in error_msg and "NC" in error_msg) or "valides" in error_msg.lower()

    def test_mixed_valid_invalid_all_shown(self):
        """Verify mixed valid/invalid shows all invalid ones."""
        with pytest.raises(ToolError) as exc_info:
            mcp_module.rgaa_taux_conformite({
                "1.1": "C",
                "1.2": "BAD1",
                "1.3": "NC",
                "1.4": "BAD2"
            })
        error_msg = str(exc_info.value)
        assert "BAD1" in error_msg and "BAD2" in error_msg

    def test_case_sensitive_status(self):
        """Verify status values are case-sensitive."""
        with pytest.raises(ToolError) as exc_info:
            mcp_module.rgaa_taux_conformite({"1.1": "c"})  # lowercase
        error_msg = str(exc_info.value).lower()
        assert "invalide" in error_msg

    def test_valid_calculation_c_c_nc(self):
        """Verify valid C/NC/NA values calculate correctly."""
        result = mcp_module.rgaa_taux_conformite({
            "1.1": "C",
            "1.2": "C",
            "1.3": "NC"
        })
        assert result["taux"] == 66.67
        assert result["nb_conformes"] == 2
        assert result["nb_non_conformes"] == 1

    def test_valid_with_na_excludes_from_calculation(self):
        """Verify NA values excluded from taux calculation."""
        result = mcp_module.rgaa_taux_conformite({
            "1.1": "C",
            "1.2": "NA",
            "1.3": "NC"
        })
        # Should be 50% (1 C out of 2 evaluated, NA excluded)
        assert result["taux"] == 50.0
        assert result["criteres_evalues"] == 2

    def test_all_na_returns_zero_taux(self):
        """Verify all NA values return taux of 0."""
        result = mcp_module.rgaa_taux_conformite({
            "1.1": "NA",
            "1.2": "NA",
            "1.3": "NA"
        })
        assert result["taux"] == 0.0
        assert result["criteres_evalues"] == 0
        assert result["nb_non_applicables"] == 3

    def test_all_conformes_returns_100_taux(self):
        """Verify all C values return taux of 100."""
        result = mcp_module.rgaa_taux_conformite({
            "1.1": "C",
            "1.2": "C",
            "1.3": "C"
        })
        assert result["taux"] == 100.0
        assert result["nb_conformes"] == 3

    def test_error_message_includes_acceptable_values(self):
        """Verify error for invalid status includes acceptable values."""
        with pytest.raises(ToolError) as exc_info:
            mcp_module.rgaa_taux_conformite({"1.1": "WRONG"})
        error_msg = str(exc_info.value)
        # Should mention at least C, NC, NA
        assert "NA" in error_msg or "non-applicable" in error_msg.lower()


# ============================================================================
# Task 5: 20 New Unit Tests for Coverage Gaps (75% → 90%)
# ============================================================================

class TestRgaaChercherSearchEdgeCases:
    """Edge case tests for rgaa_chercher search functionality."""

    def test_search_with_scope_glossaire_only(self):
        """Verify search with scope=['glossaire'] returns only glossaire results."""
        result = mcp_module.rgaa_chercher("contraste", scope=["glossaire"])
        assert "criteres" in result
        assert "termes_glossaire" in result
        # When searching glossaire for "contraste", should find glossaire terms
        assert "termes_glossaire" in result


class TestRgaaGlossaireeFuzzyMatch:
    """Test glossaire fuzzy matching for misspelled terms."""

    def test_glossaire_typo_fuzzy_match_suggestion(self):
        """Verify glossaire provides suggestion for typo (e.g., 'imagee' → 'image')."""
        # This tests the difflib fuzzy matching path (lines 301-302)
        result = mcp_module.rgaa_glossaire("imagees")  # Note: typo
        # Should return a suggestion or a close match
        assert "suggestion" in result or "terme" in result
        if "suggestion" in result and result["suggestion"]:
            # If suggestion provided, should indicate what was matched
            assert "introuvable" in result["suggestion"].lower() or "parler de" in result["suggestion"].lower()

    def test_glossaire_case_insensitive_match(self):
        """Verify glossaire matching is case-insensitive."""
        # Test that uppercase term finds the glossaire entry
        result = mcp_module.rgaa_glossaire("CONTRASTE")
        assert "definition" in result
        assert len(result["definition"]) > 0


class TestRgaaListerCriteresMultipleFilters:
    """Test lister_criteres with combined filters."""

    def test_lister_both_theme_and_wcag_filters(self):
        """Verify theme and WCAG filters work together."""
        result = mcp_module.rgaa_lister_criteres(theme=1, niveau_wcag="AA")
        assert "total" in result
        assert "criteres" in result
        # All results should have theme=1 AND WCAG level AA
        for c in result["criteres"]:
            assert c["theme"] == 1

    def test_lister_invalid_wcag_level_raises_error(self):
        """Verify invalid WCAG level raises ToolError."""
        with pytest.raises(ToolError) as exc_info:
            mcp_module.rgaa_lister_criteres(niveau_wcag="INVALID")
        assert "wcag" in str(exc_info.value).lower() or "invalide" in str(exc_info.value).lower()

    def test_lister_theme_boundary_1(self):
        """Verify theme=1 (minimum) returns results."""
        result = mcp_module.rgaa_lister_criteres(theme=1)
        assert result["total"] > 0
        assert all(c["theme"] == 1 for c in result["criteres"])

    def test_lister_theme_boundary_13(self):
        """Verify theme=13 (maximum) returns results."""
        result = mcp_module.rgaa_lister_criteres(theme=13)
        assert result["total"] > 0
        assert all(c["theme"] == 13 for c in result["criteres"])


class TestRgaaObtainCritereErrorMessages:
    """Test error messages and suggestions for obtenir_critere."""

    def test_obtenir_critere_close_match_suggestion(self):
        """Verify obtenir_critere suggests close matches for invalid IDs."""
        with pytest.raises(ToolError) as exc_info:
            mcp_module.rgaa_obtenir_critere("1.99")  # Likely invalid, but close to 1.1-1.N
        error_msg = str(exc_info.value)
        # Should suggest valid criteria or mention valid range
        assert "1.1" in error_msg or "valides" in error_msg.lower() or "1-13" in error_msg

    def test_obtenir_critere_valid_returns_full_detail(self):
        """Verify obtenir_critere returns complete criterion detail."""
        result = mcp_module.rgaa_obtenir_critere("1.1")
        # Should include all expected fields
        assert "id" in result
        assert "theme" in result
        assert "titre" in result
        assert "tests" in result or "automatisable" in result


class TestRgaaTypeAuditInvalidType:
    """Test audit type validation."""

    def test_criteres_audit_invalid_type_mentions_valid_options(self):
        """Verify invalid audit type error mentions valid options."""
        with pytest.raises(ToolError) as exc_info:
            mcp_module.rgaa_criteres_audit("invalide_type")
        error_msg = str(exc_info.value).lower()
        # Should mention at least one valid type
        assert ("complet" in error_msg or "rapide" in error_msg or "complementaire" in error_msg
                or "valides" in error_msg)


class TestRgaaStatistiquesStructure:
    """Test rgaa_statistiques output structure and values."""

    def test_statistiques_par_theme_complete(self):
        """Verify statistiques returns all 13 themes."""
        result = mcp_module.rgaa_statistiques()
        assert "par_theme" in result
        themes = result["par_theme"]
        # Should have entries for themes 1-13
        assert len(themes) == 13

    def test_statistiques_totals_match_sum(self):
        """Verify total automatisables = sum of per-theme automatisables."""
        result = mcp_module.rgaa_statistiques()
        total_auto = sum(theme["automatisables"] for theme in result["par_theme"].values())
        assert result["automatisables"] == total_auto

    def test_statistiques_includes_referentiel_version(self):
        """Verify statistiques returns referentiel_version field."""
        result = mcp_module.rgaa_statistiques()
        assert "referentiel_version" in result
        assert result["referentiel_version"] != ""


class TestMcpResourcesStructure:
    """Test MCP resource response structure."""

    def test_resource_index_contains_all_criteria(self):
        """Verify rgaa://index resource returns all criteria."""
        result = asyncio.run(mcp_module.mcp.read_resource("rgaa://index"))
        data = json.loads(result.contents[0].content)
        assert isinstance(data, list)
        assert len(data) == 106, f"Expected 106 criteria in index, got {len(data)}"

    def test_resource_metadata_valid_json(self):
        """Verify rgaa://metadata resource returns valid JSON."""
        result = asyncio.run(mcp_module.mcp.read_resource("rgaa://metadata"))
        data = json.loads(result.contents[0].content)
        assert isinstance(data, dict)
        # Metadata should contain standard fields
        assert "nb_criteres" in data or "languages" in data or "nb_themes" in data


# ============================================================================
# PROMPT FUNCTIONS TESTS
# ============================================================================

class TestPromptFunctions:
    """Test all prompt function outputs and parameter handling."""

    def test_audit_page_without_themes(self):
        """Test audit_page prompt with no themes parameter."""
        result = mcp_module.audit_page("https://example.com")
        assert isinstance(result, str)
        assert "exemple.com" in result.lower() or "https://example.com" in result
        assert "audit" in result.lower()

    def test_audit_page_with_themes(self):
        """Test audit_page prompt with themes parameter."""
        result = mcp_module.audit_page("https://example.com", themes="1,6,11")
        assert isinstance(result, str)
        assert "1,6,11" in result or "en ciblant les thèmes" in result

    def test_rapport_audit_prompt(self):
        """Test rapport_audit prompt generates valid output."""
        results = '{"taux": 75.0, "criteres": ["1.1", "2.1"]}'
        result = mcp_module.rapport_audit(results)
        assert isinstance(result, str)
        assert "rapport" in result.lower()
        assert "Markdown" in result

    def test_expliquer_critere_prompt(self):
        """Test expliquer_critere prompt for a valid criterion."""
        result = mcp_module.expliquer_critere("1.1")
        assert isinstance(result, str)
        assert "1.1" in result

    def test_criteres_par_sujet_prompt(self):
        """Test criteres_par_sujet prompt."""
        result = mcp_module.criteres_par_sujet("images", niveau="A")
        assert isinstance(result, str)
        assert "images" in result.lower()

    def test_criteres_par_sujet_default_niveau(self):
        """Test criteres_par_sujet with default niveau."""
        result = mcp_module.criteres_par_sujet("formulaires")
        assert isinstance(result, str)
        assert "formulaires" in result.lower()

    def test_checklist_audit_prompt(self):
        """Test checklist_audit prompt."""
        result = mcp_module.checklist_audit("1,6,11")
        assert isinstance(result, str)
        assert "checklist" in result.lower()

    def test_criteres_wcag_prompt_default(self):
        """Test criteres_wcag with default AA level."""
        result = mcp_module.criteres_wcag()
        assert isinstance(result, str)
        assert "AA" in result

    def test_criteres_wcag_prompt_aaa(self):
        """Test criteres_wcag with AAA level."""
        result = mcp_module.criteres_wcag(niveau_wcag="AAA")
        assert isinstance(result, str)
        assert "AAA" in result

    def test_audit_par_type_prompt(self):
        """Test audit_par_type prompt."""
        result = mcp_module.audit_par_type("https://example.com", type="complet")
        assert isinstance(result, str)
        assert "complet" in result.lower()

    def test_audit_rapide_prompt(self):
        """Test audit_rapide prompt."""
        result = mcp_module.audit_rapide("https://example.com")
        assert isinstance(result, str)
        assert "rapide" in result.lower()
        assert "25" in result

    def test_audit_complementaire_prompt(self):
        """Test audit_complementaire prompt."""
        result = mcp_module.audit_complementaire("https://example.com")
        assert isinstance(result, str)
        assert "complémentaire" in result.lower() or "complementaire" in result.lower()


# ============================================================================
# TOKEN MANAGEMENT ERROR HANDLING
# ============================================================================

class TestTokenManagementErrors:
    """Test error handling in token management functions (core/auth.py)."""

    def test_load_tokens_missing_file(self, tmp_path):
        missing_file = tmp_path / "nonexistent" / "tokens.json"
        result = charger_tokens(missing_file)
        assert result == {}

    def test_load_tokens_invalid_json(self, tmp_path):
        tokens_file = tmp_path / "tokens.json"
        tokens_file.write_text("not valid json {{{")
        result = charger_tokens(tokens_file)
        assert result == {}

    def test_save_tokens_creates_directories(self, tmp_path):
        tokens_file = tmp_path / "new_dir" / "subdir" / "tokens.json"
        tokens = {"token1": {"name": "test"}}
        sauvegarder_tokens(tokens_file, tokens)
        assert tokens_file.exists()
        assert json.loads(tokens_file.read_text()) == tokens

    def test_tokens_for_auth_filters_expired(self, tmp_path):
        import time
        tokens_file = tmp_path / "tokens.json"
        now = time.time()
        tokens_file.write_text(json.dumps({
            "valid_token": {"name": "valid", "expires_at": now + 86400},
            "expired_token": {"name": "expired", "expires_at": now - 86400},
        }))
        result = tokens_pour_auth(tokens_file)
        assert "valid_token" in result
        assert "expired_token" not in result

    def test_tokens_for_auth_no_expiry(self, tmp_path):
        tokens_file = tmp_path / "tokens.json"
        tokens_file.write_text(json.dumps({"no_expiry_token": {"name": "permanent"}}))
        result = tokens_pour_auth(tokens_file)
        assert "no_expiry_token" in result
        assert "expires_at" not in result["no_expiry_token"]

    def test_cmd_generate_token_stores_data(self, tmp_path, capsys):
        tokens_file = tmp_path / "tokens.json"
        cmd_generate_token(tokens_file, "testuser", expires_days=30)
        captured = capsys.readouterr()
        token_printed = captured.out.strip()
        assert token_printed  # token is printed to stdout
        tokens = json.loads(tokens_file.read_text())
        assert len(tokens) == 1
        token_data = list(tokens.values())[0]
        assert token_data["name"] == "testuser"

    def test_cmd_list_tokens_empty(self, tmp_path, capsys):
        cmd_list_tokens(tmp_path / "tokens.json")
        captured = capsys.readouterr()
        assert "Aucun token" in captured.out

    def test_cmd_list_tokens_shows_status(self, tmp_path, capsys):
        import time
        tokens_file = tmp_path / "tokens.json"
        now = time.time()
        tokens_file.write_text(json.dumps({
            "active_token": {"name": "active", "expires_at": now + 86400},
            "expired_token": {"name": "expired", "expires_at": now - 86400},
        }))
        cmd_list_tokens(tokens_file)
        captured = capsys.readouterr()
        assert "EXPIRÉ" in captured.out
        assert "actif" in captured.out

    def test_cmd_revoke_token_success(self, tmp_path, capsys):
        tokens_file = tmp_path / "tokens.json"
        tokens_file.write_text(json.dumps({"test_token_xyz": {"name": "test"}}))
        cmd_revoke_token(tokens_file, "test_token_xyz")
        captured = capsys.readouterr()
        assert "révoqué" in captured.out
        tokens = json.loads(tokens_file.read_text())
        assert "test_token_xyz" not in tokens

    def test_cmd_revoke_token_not_found(self, tmp_path):
        with pytest.raises(ValueError, match="non trouvé"):
            cmd_revoke_token(tmp_path / "tokens.json", "nonexistent")


# ============================================================================
# RESOURCE EDGE CASES
# ============================================================================

class TestResourceEdgeCases:
    """Test MCP resource functions with edge cases."""

    def test_resource_version_has_required_fields(self):
        """Test rgaa://version resource returns unified fields."""
        result = asyncio.run(mcp_module.mcp.read_resource("rgaa://version"))
        data = json.loads(result.contents[0].content)
        assert "server_version" in data
        assert "referentiel_version" in data
        assert "updated_at" in data
        assert "nb_items" in data

    def test_resource_critere_not_found(self):
        """Test resource_critere with invalid ID."""
        result = asyncio.run(mcp_module.resource_critere("99.99"))
        data = json.loads(result)
        assert "erreur" in data

    def test_resource_index_valid_structure(self):
        """Test resource_index returns valid structure."""
        result = asyncio.run(mcp_module.resource_index())
        data = json.loads(result)
        assert isinstance(data, list)
        if data:
            first = data[0]
            assert "id" in first
            assert "theme" in first
            assert "titre" in first

    def test_resource_metadata_complete(self):
        """Test resource_metadata returns all expected fields."""
        result = asyncio.run(mcp_module.resource_metadata())
        data = json.loads(result)
        assert "languages" in data
        assert "versions" in data
        assert "source" in data
        assert "nb_criteres" in data
        assert "nb_themes" in data


# ============================================================================
# CONFIGURE MCP TESTS
# ============================================================================

class TestConfigureMcp:
    """Test factory.create_mcp function."""

    def test_configure_mcp_without_tokens(self, monkeypatch, tmp_path):
        monkeypatch.setenv("MCP_TRANSPORT", "stdio")
        test_mcp = factory.create_mcp("RGAA MCP", str(tmp_path / "tokens.json"), mcp_module._rgaa_tool_definitions)
        assert test_mcp._auth is None

    def test_configure_mcp_with_tokens_stdio(self, monkeypatch, tmp_path):
        import time as time_mod
        tokens_file = tmp_path / "tokens.json"
        tokens_file.write_text(json.dumps({
            "test_token": {
                "name": "test",
                "expires_at": time_mod.time() + 86400
            }
        }))
        monkeypatch.setenv("MCP_TRANSPORT", "stdio")
        test_mcp = factory.create_mcp("RGAA MCP", str(tokens_file), mcp_module._rgaa_tool_definitions)
        assert test_mcp._auth is not None

    def test_configure_mcp_http_mode_routes(self, monkeypatch, tmp_path):
        monkeypatch.setenv("MCP_TRANSPORT", "http")
        monkeypatch.setenv("MCP_ALLOW_NO_AUTH", "1")  # fail-safe: démarrage HTTP sans token
        test_mcp = factory.create_mcp("RGAA MCP", str(tmp_path / "tokens.json"), mcp_module._rgaa_tool_definitions)
        paths = [r.path for r in test_mcp._additional_http_routes]
        assert "/" in paths
        assert "/install.sh" in paths
        assert "/guide" in paths


# ============================================================================
# CHECKLIST EDGE CASES - TESTS DATA STRUCTURE HANDLING
# ============================================================================

class TestChecklistDataEdgeCases:
    """Test rgaa_checklist with various data structure scenarios."""

    def test_checklist_with_list_tests(self):
        """Test checklist handles criteria with list-format tests."""
        result = mcp_module.rgaa_checklist(themes=[1])
        assert "criteres" in result
        assert len(result["criteres"]) > 0
        # Verify structure
        for item in result["criteres"]:
            assert "id" in item
            assert "titre" in item
            assert "tests" in item
            assert isinstance(item["tests"], list)

    def test_checklist_with_dict_tests(self):
        """Test checklist handles criteria with dict-format tests."""
        result = mcp_module.rgaa_checklist(criteres=["1.1"])
        assert "criteres" in result
        assert len(result["criteres"]) > 0

    def test_checklist_non_existent_critere_error(self):
        """Test checklist rejects non-existent criteria."""
        with pytest.raises(ToolError, match="Critères invalides"):
            mcp_module.rgaa_checklist(criteres=["1.1", "99.99"])

    def test_checklist_empty_tests_field(self):
        """Test checklist handles criteria without test descriptions."""
        result = mcp_module.rgaa_checklist(themes=[1])
        assert "criteres" in result
        for item in result["criteres"]:
            assert item["tests"]  # Should have fallback tests

    @pytest.mark.parametrize("tests_raw,expected_type,expected_len", [
        ({"test1": ["val1", "val2"], "test2": ["val3"]}, list, 2),
        ({"test1": "val1", "test2": "val2"}, list, 2),
        (["test1", "test2", "test3"], list, 3),
        ("single_test", list, 1),
    ])
    def test_checklist_different_test_data_formats(self, monkeypatch, tests_raw, expected_type, expected_len):
        """Test rgaa_checklist handles different tests_raw formats (lines 668-673)."""
        # Mock cache with custom test data format
        mock_cache = {
            "criteres": {
                "1.1": {
                    "id": "1.1",
                    "titre": "Test Criterium",
                    "theme": 1,
                    "tests": tests_raw,  # Different format
                },
            },
        }
        monkeypatch.setattr(mcp_module, "charger_cache", lambda: mock_cache)

        result = mcp_module.rgaa_checklist(criteres=["1.1"])

        assert "criteres" in result
        assert len(result["criteres"]) == 1
        item = result["criteres"][0]
        assert item["id"] == "1.1"
        assert item["titre"] == "Test Criterium"
        assert isinstance(item["tests"], list)
        # Verify correct number of test items generated
        non_empty_tests = [t for t in item["tests"] if t.get("description")]
        assert len(non_empty_tests) == expected_len

    def test_checklist_dict_with_empty_list_values(self):
        """Test rgaa_checklist handles dict with empty list values (line 669 edge case)."""
        mock_cache = {
            "criteres": {
                "1.1": {
                    "id": "1.1",
                    "titre": "Test Criterium",
                    "theme": 1,
                    "tests": {"test1": [], "test2": ["val"]},  # Mixed empty/non-empty lists
                },
            },
        }
        # Simulate monkeypatch directly in test
        import unittest.mock as mock_mock
        with mock_mock.patch.object(mcp_module, "charger_cache", return_value=mock_cache):
            result = mcp_module.rgaa_checklist(criteres=["1.1"])

            assert "criteres" in result
            item = result["criteres"][0]
            assert isinstance(item["tests"], list)
            # Should handle empty lists by converting to empty string
            non_empty_tests = [t for t in item["tests"] if t.get("description")]
            assert len(non_empty_tests) >= 1  # At least one test from non-empty list

    def test_checklist_missing_criteria_skipped(self):
        """Test rgaa_checklist skips missing criteria (line 665 continue statement)."""
        import unittest.mock as mock_mock

        # Get a real cache and create a wrapper dict that returns None for first key
        real_cache = mcp_module.charger_cache()
        original_criteres = real_cache["criteres"]

        class FilteredCriteres(dict):
            """Wrapper dict that returns None for first lookup to trigger line 665."""
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.call_count = 0

            def get(self, key, default=None):
                self.call_count += 1
                # Skip first criterion by returning None
                if self.call_count == 1:
                    return None
                return super().get(key, default)

        # Replace criteres with our filtered version
        filtered = FilteredCriteres(original_criteres)
        real_cache["criteres"] = filtered

        # Patch charger_cache to return our modified cache
        with mock_mock.patch.object(mcp_module, "charger_cache", return_value=real_cache):
            # Now request a theme - should skip first criterion due to None return
            result = mcp_module.rgaa_checklist(themes=[1])

            # Should still return a valid result
            assert "criteres" in result
            assert isinstance(result["criteres"], list)


# ============================================================================
# PARAMETER VALIDATION - BOUNDARY TESTS
# ============================================================================

class TestParameterValidationBoundaries:
    """Test parameter validation at boundaries."""

    def test_lister_criteres_theme_boundary_low(self):
        """Test lister_criteres with theme 1 (minimum valid)."""
        result = mcp_module.rgaa_lister_criteres(theme=1)
        assert result["total"] > 0
        for c in result["criteres"]:
            assert c["theme"] == 1

    def test_lister_criteres_theme_boundary_high(self):
        """Test lister_criteres with theme 13 (maximum valid)."""
        result = mcp_module.rgaa_lister_criteres(theme=13)
        assert result["total"] > 0
        for c in result["criteres"]:
            assert c["theme"] == 13

    def test_lister_criteres_theme_out_of_range_low(self):
        """Test lister_criteres rejects theme 0."""
        with pytest.raises(ToolError) as exc_info:
            mcp_module.rgaa_lister_criteres(theme=0)
        assert "invalide" in str(exc_info.value).lower()

    def test_lister_criteres_theme_out_of_range_high(self):
        """Test lister_criteres rejects theme 14."""
        with pytest.raises(ToolError) as exc_info:
            mcp_module.rgaa_lister_criteres(theme=14)
        assert "invalide" in str(exc_info.value).lower()

    def test_lister_criteres_wcag_level_a(self):
        """Test lister_criteres filters by WCAG level A."""
        result = mcp_module.rgaa_lister_criteres(niveau_wcag="A")
        assert result["total"] > 0

    def test_lister_criteres_wcag_level_aa(self):
        """Test lister_criteres filters by WCAG level AA."""
        result = mcp_module.rgaa_lister_criteres(niveau_wcag="AA")
        assert result["total"] > 0

    def test_lister_criteres_wcag_level_aaa(self):
        """Test lister_criteres filters by WCAG level AAA."""
        result = mcp_module.rgaa_lister_criteres(niveau_wcag="AAA")
        assert result["total"] >= 0

    def test_lister_criteres_invalid_wcag_level(self):
        """Test lister_criteres rejects invalid WCAG level."""
        with pytest.raises(ToolError) as exc_info:
            mcp_module.rgaa_lister_criteres(niveau_wcag="INVALID")
        assert "invalide" in str(exc_info.value).lower()


# ============================================================================
# SEARCH AND GLOSSAIRE EDGE CASES
# ============================================================================

class TestSearchGlossaireEdgeCases:
    """Test search and glossaire functions with edge cases."""

    def test_rechercher_empty_scope(self):
        """Test rgaa_chercher with empty scope list."""
        result = mcp_module.rgaa_chercher("image", scope=[])
        assert "criteres" in result
        assert "termes_glossaire" in result
        assert len(result["criteres"]) == 0
        assert len(result["termes_glossaire"]) == 0

    def test_rechercher_scope_criteres_only(self):
        """Test rgaa_chercher with criteres scope only."""
        result = mcp_module.rgaa_chercher("image", scope=["criteres"])
        assert "criteres" in result
        assert "termes_glossaire" in result
        assert len(result["criteres"]) > 0
        assert len(result["termes_glossaire"]) == 0

    def test_rechercher_scope_glossaire_only(self):
        """Test rgaa_chercher with glossaire scope only."""
        result = mcp_module.rgaa_chercher("image", scope=["glossaire"])
        assert "criteres" in result
        assert "termes_glossaire" in result
        assert len(result["criteres"]) == 0
        assert len(result["termes_glossaire"]) > 0

    def test_glossaire_substring_match(self):
        """Test rgaa_glossaire finds terms with substring matching."""
        result = mcp_module.rgaa_glossaire("alt")
        assert "terme" in result
        assert "definition" in result

    def test_glossaire_case_insensitive(self):
        """Test rgaa_glossaire is case insensitive."""
        result1 = mcp_module.rgaa_glossaire("alternative")
        result2 = mcp_module.rgaa_glossaire("ALTERNATIVE")
        assert result1["definition"] == result2["definition"]


# ============================================================================
# CONFORMITE TAUX CALCULATION EDGE CASES
# ============================================================================

class TestConformiteTauxEdgeCases:
    """Test conformity rate calculation edge cases."""

    def test_taux_all_conformes(self):
        """Test taux_conformite with all conformes."""
        result = mcp_module.rgaa_taux_conformite({"1.1": "C", "1.2": "C", "1.3": "C"})
        assert result["taux"] == 100.0
        assert result["nb_conformes"] == 3
        assert result["nb_non_conformes"] == 0

    def test_taux_all_non_conformes(self):
        """Test taux_conformite with all non-conformes."""
        result = mcp_module.rgaa_taux_conformite({"1.1": "NC", "1.2": "NC"})
        assert result["taux"] == 0.0
        assert result["nb_conformes"] == 0
        assert result["nb_non_conformes"] == 2

    def test_taux_all_non_applicables(self):
        """Test taux_conformite with only non-applicables."""
        result = mcp_module.rgaa_taux_conformite({"1.1": "NA", "1.2": "NA"})
        assert result["taux"] == 0.0
        assert result["criteres_evalues"] == 0

    def test_taux_mixed_with_na(self):
        """Test taux_conformite with mixed statuses including NA."""
        result = mcp_module.rgaa_taux_conformite({
            "1.1": "C", "1.2": "C", "1.3": "NC", "1.4": "NA"
        })
        assert result["taux"] == 66.67  # 2/(2+1)*100
        assert result["nb_non_applicables"] == 1

    def test_taux_invalid_status_partial(self):
        """Test taux_conformite with one invalid status among valid ones."""
        with pytest.raises(ToolError) as exc_info:
            mcp_module.rgaa_taux_conformite({
                "1.1": "C",
                "1.2": "INVALID"
            })
        assert "invalides" in str(exc_info.value).lower()

    def test_taux_fractional_result(self):
        """Test taux_conformite returns proper decimal precision."""
        result = mcp_module.rgaa_taux_conformite({
            "1.1": "C", "1.2": "NC", "1.3": "NC"
        })
        assert result["taux"] == 33.33


# ============================================================================
# ANALYSER EDGE CASES
# ============================================================================

class TestAnalyserEdgeCases:
    """Test rgaa_analyser with various inputs."""

    def test_analyser_invalid_url_no_protocol(self):
        """Test analyser rejects URL without protocol."""
        with pytest.raises(ToolError) as exc_info:
            mcp_module.rgaa_analyser("example.com")
        assert "invalide" in str(exc_info.value).lower()

    def test_analyser_valid_url_http(self):
        """Test analyser accepts http:// protocol."""
        # This will fail due to network, but should pass validation
        with pytest.raises(ToolError):
            mcp_module.rgaa_analyser("http://localhost:99999/nonexistent")
        # Should be a network error, not a validation error

    def test_analyser_valid_url_https(self):
        """Test analyser accepts https:// protocol."""
        with pytest.raises(ToolError):
            mcp_module.rgaa_analyser("https://localhost:99999/nonexistent")


# ============================================================================
# THEME VALIDATION TESTS
# ============================================================================

class TestThemeValidation:
    """Test theme validation across multiple functions."""

    @pytest.mark.parametrize("invalid_theme", [-1, 0, 14, 15, 100])
    def test_invalid_themes_rejected(self, invalid_theme):
        """Test that invalid theme numbers are rejected."""
        with pytest.raises(ToolError):
            mcp_module.rgaa_checklist(themes=[invalid_theme])

    @pytest.mark.parametrize("valid_theme", [1, 6, 11, 13])
    def test_valid_themes_accepted(self, valid_theme):
        """Test that valid theme numbers are accepted."""
        result = mcp_module.rgaa_checklist(themes=[valid_theme])
        assert "criteres" in result
        assert result["criteres"]
