"""
Tests de parité architecturale pour le MCP RGESN.

Valide que RGESN suit les mêmes patterns que greenit et rgaa :
1. Structure des fichiers dans files/
2. Routes HTTP (GET /, /guide, /install.sh)
3. Fonctions _helpers
4. Gestion des erreurs via ToolError
5. VERSION définie
6. Annotations sur les outils
7. Resource rgesn://metadata
"""

import sys
import inspect
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "files"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "core"))

import pytest
from fastmcp.exceptions import ToolError


class TestModuleStructure:
    def test_files_directory_exists(self):
        files_dir = Path(__file__).parent.parent / "files"
        assert files_dir.is_dir()

    def test_rgesn_mcp_py_exists(self):
        assert (Path(__file__).parent.parent / "files" / "rgesn_mcp.py").exists()

    def test_data_py_exists(self):
        assert (Path(__file__).parent.parent / "files" / "data.py").exists()

    def test_auth_py_in_core(self):
        from mcp_ref_core import auth
        assert auth is not None

    def test_routes_py_in_core(self):
        from mcp_ref_core import routes
        assert routes is not None

    def test_helpers_py_in_core(self):
        from mcp_ref_core import _helpers
        assert _helpers is not None

    def test_rgesn_cache_json_exists(self):
        data_file = Path(__file__).parent.parent / "files" / "rgesn_cache.json"
        assert data_file.exists(), "rgesn_cache.json not found in files/"


class TestHTTPRouteEndpoints:
    def test_http_homepage_exists(self):
        from mcp_ref_core import routes
        assert hasattr(routes, "_http_homepage")

    def test_http_guide_exists(self):
        from mcp_ref_core import routes
        assert hasattr(routes, "_http_guide")

    def test_http_install_script_exists(self):
        from mcp_ref_core import routes
        assert hasattr(routes, "_http_install_script")

    def test_route_functions_are_async(self):
        from mcp_ref_core import routes
        assert inspect.iscoroutinefunction(routes._http_homepage)
        assert inspect.iscoroutinefunction(routes._http_guide)

    def test_route_functions_accept_request_param(self):
        from mcp_ref_core import routes
        sig = inspect.signature(routes._http_homepage)
        assert "request" in sig.parameters


class TestHelpersExtraction:
    def test_validate_themes_exists(self):
        from mcp_ref_core._helpers import validate_themes
        assert callable(validate_themes)

    def test_validate_score_range_exists(self):
        from mcp_ref_core._helpers import validate_score_range
        assert callable(validate_score_range)

    def test_validate_nonnegative_exists(self):
        from mcp_ref_core._helpers import validate_nonnegative
        assert callable(validate_nonnegative)

    def test_validate_themes_raises_toolerror_on_invalid(self):
        from mcp_ref_core._helpers import validate_themes
        with pytest.raises(ToolError):
            validate_themes([0])

    def test_validate_themes_accepts_valid(self):
        from mcp_ref_core._helpers import validate_themes
        result = validate_themes([1, 5, 9])
        assert result == [1, 5, 9]


class TestToolErrorHandling:
    def test_lister_criteres_invalid_theme_raises_toolerror(self):
        import rgesn_mcp
        with pytest.raises(ToolError):
            rgesn_mcp.rgesn_lister_criteres(theme=99)

    def test_lister_criteres_invalid_priorite_raises_toolerror(self):
        import rgesn_mcp
        with pytest.raises(ToolError):
            rgesn_mcp.rgesn_lister_criteres(priorite="Urgent")

    def test_obtenir_critere_unknown_raises_toolerror(self):
        import rgesn_mcp
        with pytest.raises(ToolError):
            rgesn_mcp.rgesn_obtenir_critere("99.99")

    def test_chercher_empty_raises_toolerror(self):
        import rgesn_mcp
        with pytest.raises(ToolError):
            rgesn_mcp.rgesn_chercher("")

    def test_taux_conformite_empty_raises_toolerror(self):
        import rgesn_mcp
        with pytest.raises(ToolError):
            rgesn_mcp.rgesn_taux_conformite({})


class TestVersionDefined:
    def test_version_exists(self):
        import rgesn_mcp
        assert hasattr(rgesn_mcp, "VERSION")

    def test_version_is_string(self):
        import rgesn_mcp
        assert isinstance(rgesn_mcp.VERSION, str)

    def test_version_non_empty(self):
        import rgesn_mcp
        assert rgesn_mcp.VERSION

    def test_version_injected_into_routes(self):
        import rgesn_mcp
        from mcp_ref_core import routes
        assert routes._VERSION == rgesn_mcp.VERSION


class TestToolAnnotationsParity:
    def test_all_tools_have_descriptions(self):
        import asyncio
        import rgesn_mcp
        tools = asyncio.run(rgesn_mcp.mcp.list_tools())
        for tool in tools:
            assert tool.description, f"{tool.name} missing description"

    def test_all_tools_read_only(self):
        import asyncio
        import rgesn_mcp
        tools = asyncio.run(rgesn_mcp.mcp.list_tools())
        for tool in tools:
            assert tool.annotations.readOnlyHint == True, f"{tool.name} not readOnly"
            assert tool.annotations.destructiveHint == False, f"{tool.name} marked destructive"

    def test_six_tools_registered(self):
        import asyncio
        import rgesn_mcp
        tools = asyncio.run(rgesn_mcp.mcp.list_tools())
        assert len(tools) == 6


class TestMcpThemeVarsInjected:
    def test_mcp_name_injected(self):
        from mcp_ref_core import routes
        assert routes._MCP_NAME == "RGESN MCP"

    def test_mcp_id_injected(self):
        from mcp_ref_core import routes
        assert routes._MCP_ID == "rgesn"

    def test_accent_color_injected(self):
        from mcp_ref_core import routes
        assert routes._ACCENT == "#f59e0b"

    def test_tagline_injected(self):
        from mcp_ref_core import routes
        assert routes._TAGLINE

    def test_logo_injected(self):
        from mcp_ref_core import routes
        assert routes._LOGO == "💡"
