"""
Tests du serveur MCP RGESN.

Exécution:
    cd rgesn/files && pytest ../tests/test_tools.py -v
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "files"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "core"))

import pytest
import json
import rgesn_mcp as mcp_module
from fastmcp.exceptions import ToolError
from mcp_ref_core import factory, routes as routes_mod
from mcp_ref_core import routes


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


# ============================================================================
# factory.create_mcp()
# ============================================================================

class TestCreateMcp:
    def test_stdio_mode_no_routes(self, monkeypatch):
        monkeypatch.setenv("MCP_TRANSPORT", "stdio")
        mcp = factory.create_mcp("RGESN MCP", mcp_module.TOKENS_FILE, guide_extra_sections_fn=mcp_module._rgesn_guide_extra_sections)
        assert mcp.name == "RGESN MCP"
        assert len(mcp._additional_http_routes) == 0

    def test_http_mode_registers_routes(self, monkeypatch):
        monkeypatch.setenv("MCP_TRANSPORT", "http")
        mcp = factory.create_mcp("RGESN MCP", mcp_module.TOKENS_FILE, guide_extra_sections_fn=mcp_module._rgesn_guide_extra_sections)
        assert mcp.name == "RGESN MCP"
        assert len(mcp._additional_http_routes) == 8
        paths = [r.path for r in mcp._additional_http_routes]
        assert "/" in paths
        assert "/install.sh" in paths
        assert "/guide" in paths

    def test_no_tokens_no_auth(self, monkeypatch, tmp_path):
        monkeypatch.setenv("MCP_TRANSPORT", "stdio")
        mcp = factory.create_mcp("RGESN MCP", str(tmp_path / "tokens.json"))
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
        mcp = factory.create_mcp("RGESN MCP", str(tokens_file))
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
        assert "RGESN MCP" in r.text

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

    def test_install_script_has_uninstall_flag(self, client):
        r = client.get("/install.sh")
        assert "--uninstall" in r.text

    def test_install_script_has_rgesn_mcp_add(self, client):
        r = client.get("/install.sh")
        assert "claude mcp add rgesn" in r.text

    def test_guide_status_200(self, client):
        r = client.get("/guide")
        assert r.status_code == 200

    def test_guide_contains_tools(self, client):
        r = client.get("/guide")
        assert "rgesn_lister_criteres" in r.text
        assert "rgesn_obtenir_critere" in r.text

    def test_guide_json_accept(self, client):
        r = client.get("/guide", headers={"Accept": "application/json"})
        assert r.status_code == 200
        assert "application/json" in r.headers["content-type"]
        data = r.json()
        assert "tools" in data
        assert isinstance(data["tools"], list)
        assert len(data["tools"]) >= 6


# ============================================================================
# Tool Annotations
# ============================================================================

import asyncio


class TestToolAnnotations:
    def test_all_rgesn_tools_read_only(self):
        tools = asyncio.run(mcp_module.mcp.list_tools())
        for tool in tools:
            assert tool.annotations.readOnlyHint == True, f"{tool.name} should be read-only"
            assert tool.annotations.destructiveHint == False, f"{tool.name} should not be destructive"

    def test_lister_criteres_annotations(self):
        tools = asyncio.run(mcp_module.mcp.list_tools())
        tool = next((t for t in tools if t.name == "rgesn_lister_criteres"), None)
        assert tool is not None
        assert tool.annotations.readOnlyHint == True
        assert tool.annotations.idempotentHint == True
        assert tool.annotations.openWorldHint == False

    def test_obtenir_critere_annotations(self):
        tools = asyncio.run(mcp_module.mcp.list_tools())
        tool = next((t for t in tools if t.name == "rgesn_obtenir_critere"), None)
        assert tool is not None
        assert tool.annotations.readOnlyHint == True
        assert tool.annotations.idempotentHint == True

    def test_chercher_annotations(self):
        tools = asyncio.run(mcp_module.mcp.list_tools())
        tool = next((t for t in tools if t.name == "rgesn_chercher"), None)
        assert tool is not None
        assert tool.annotations.readOnlyHint == True

    def test_seven_tools_registered(self):
        tools = asyncio.run(mcp_module.mcp.list_tools())
        names = {t.name for t in tools}
        expected = {
            "rgesn_lister_criteres", "rgesn_obtenir_critere",
            "rgesn_chercher", "rgesn_statistiques",
            "rgesn_taux_conformite", "rgesn_checklist",
            "rgesn_criteres_prioritaires",
        }
        assert expected.issubset(names)


# ============================================================================
# Error messages — guidance included
# ============================================================================

class TestToolErrorMessages:
    def test_obtenir_critere_error_includes_id(self):
        with pytest.raises(ToolError) as exc_info:
            mcp_module.rgesn_obtenir_critere("99.99")
        assert "99.99" in str(exc_info.value)

    def test_lister_criteres_theme_error_mentions_range(self):
        with pytest.raises(ToolError) as exc_info:
            mcp_module.rgesn_lister_criteres(theme=15)
        msg = str(exc_info.value)
        assert "15" in msg
        assert "1" in msg and "9" in msg

    def test_chercher_empty_raises_toolerror(self):
        with pytest.raises(ToolError):
            mcp_module.rgesn_chercher("")

    def test_taux_conformite_invalid_status_raises(self):
        with pytest.raises(ToolError):
            mcp_module.rgesn_taux_conformite({"1.1": "INCONNU"})

    def test_taux_conformite_empty_raises(self):
        with pytest.raises(ToolError):
            mcp_module.rgesn_taux_conformite({})

    def test_taux_conformite_unknown_critere_raises(self):
        with pytest.raises(ToolError):
            mcp_module.rgesn_taux_conformite({"99.99": "C"})


# ============================================================================
# Tool definitions
# ============================================================================

class TestToolDefinitions:
    def test_returns_list_of_seven_tools(self):
        defs = routes._get_tool_definitions()
        assert len(defs) == 7

    def test_all_have_required_fields(self):
        defs = routes._get_tool_definitions()
        for d in defs:
            assert "name" in d
            assert "description" in d
            assert "inputSchema" in d

    def test_expected_tool_names(self):
        defs = routes._get_tool_definitions()
        names = [d["name"] for d in defs]
        assert "rgesn_lister_criteres" in names
        assert "rgesn_obtenir_critere" in names
        assert "rgesn_chercher" in names
        assert "rgesn_statistiques" in names
        assert "rgesn_taux_conformite" in names
        assert "rgesn_checklist" in names
        assert "rgesn_criteres_prioritaires" in names

    def test_no_duplicate_tool_names(self):
        defs = routes._get_tool_definitions()
        names = [d["name"] for d in defs]
        assert len(names) == len(set(names))

    def test_descriptions_non_empty(self):
        defs = routes._get_tool_definitions()
        for d in defs:
            assert len(d["description"]) > 10, f"{d['name']} has short description"


class TestCriteresPrioritaires:
    def test_returns_dict_with_criteres_key(self):
        result = mcp_module.rgesn_criteres_prioritaires()
        assert isinstance(result, dict)
        assert "criteres" in result
        assert "total" in result

    def test_returns_only_prioritaire_criteres(self):
        result = mcp_module.rgesn_criteres_prioritaires()
        for c in result["criteres"]:
            assert c["priorite"] == "Prioritaire"

    def test_returns_thirty_prioritaire_criteres(self):
        result = mcp_module.rgesn_criteres_prioritaires()
        assert result["total"] == 30
        assert len(result["criteres"]) == 30

    def test_each_critere_has_required_fields(self):
        result = mcp_module.rgesn_criteres_prioritaires()
        for c in result["criteres"]:
            assert "id" in c
            assert "theme" in c
            assert "question" in c
            assert "priorite" in c
            assert "difficulte" in c

    def test_criteres_prioritaires_annotations(self):
        tools = asyncio.run(mcp_module.mcp.list_tools())
        tool = next((t for t in tools if t.name == "rgesn_criteres_prioritaires"), None)
        assert tool is not None
        assert tool.annotations.readOnlyHint == True
        assert tool.annotations.destructiveHint == False
        assert tool.annotations.idempotentHint == True


class TestPromptCriteresPrioritaires:
    def test_criteres_prioritaires_prompt_exists(self):
        assert hasattr(mcp_module, "criteres_prioritaires_rgesn"), \
            "criteres_prioritaires_rgesn prompt missing"
        assert callable(mcp_module.criteres_prioritaires_rgesn)

    def test_criteres_prioritaires_prompt_returns_string(self):
        result = mcp_module.criteres_prioritaires_rgesn()
        assert isinstance(result, str)
        assert len(result) > 50

    def test_criteres_prioritaires_prompt_mentions_tool(self):
        result = mcp_module.criteres_prioritaires_rgesn()
        assert "rgesn_criteres_prioritaires" in result


class TestMcpResources:
    def test_version_resource_registered(self):
        import asyncio
        resources = asyncio.run(mcp_module.mcp.list_resources())
        uris = [str(r.uri) for r in resources]
        assert any("rgesn://version" in u for u in uris), f"rgesn://version missing. Got: {uris}"

    def test_version_resource_unified_structure(self):
        import asyncio
        result = asyncio.run(mcp_module.mcp.read_resource("rgesn://version"))
        data = json.loads(result.contents[0].content)
        assert "server_version" in data
        assert "referentiel_version" in data
        assert "updated_at" in data
        assert "nb_items" in data

    def test_metadata_resource_registered(self):
        import asyncio
        resources = asyncio.run(mcp_module.mcp.list_resources())
        uris = [str(r.uri) for r in resources]
        assert any("rgesn://metadata" in u for u in uris), f"rgesn://metadata missing. Got: {uris}"

    def test_metadata_resource_structure(self):
        import asyncio
        result = asyncio.run(mcp_module.mcp.read_resource("rgesn://metadata"))
        data = json.loads(result.contents[0].content)
        assert "source" in data
        assert "updated_at" in data
        assert "nb_criteres" in data
        assert "nb_themes" in data
        assert "nb_prioritaires" in data
        assert "ponderations" in data

    def test_metadata_resource_values(self):
        import asyncio
        result = asyncio.run(mcp_module.mcp.read_resource("rgesn://metadata"))
        data = json.loads(result.contents[0].content)
        assert data["nb_criteres"] == 78
        assert data["nb_themes"] == 9
        assert data["nb_prioritaires"] == 30
        assert data["ponderations"]["Prioritaire"] == 1.5
        assert data["ponderations"]["Recommandé"] == 1.25
        assert data["ponderations"]["Modéré"] == 1.0


class TestRgesnStatistiquesStructure:
    def test_statistiques_includes_referentiel_version(self):
        result = mcp_module.rgesn_statistiques()
        assert "referentiel_version" in result
        assert result["referentiel_version"] != ""
