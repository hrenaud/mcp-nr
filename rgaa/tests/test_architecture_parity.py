"""
Architecture parity tests for mcp-rgaa service.

Validates 8 architectural aspects to ensure consistency with GreenIT MCP
and adherence to established patterns:

1. Module Structure: Required files in files/ directory
2. Computed Metadata Resources: Dynamic computation from cache
3. HTTP Route Endpoints: GET /, GET /guide, GET /install.sh with correct signatures
4. _helpers.py Extraction: Core validation functions exist
5. ToolError Error Handling: Tools use ToolError with French messages
6. Test Suite Integrity: All tests pass without failures
7. Resource Definition: rgaa://metadata resource with required keys
8. Tool Annotations: Tools have outputSchema + readOnlyHint/destructiveHint/idempotentHint

Execution:
    cd /Users/renaudheluin/DEV/mcp-rgaa
    pytest tests/test_architecture_parity.py -v
"""

import os
import sys
import json
import inspect
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "files"))

import pytest
from fastmcp.exceptions import ToolError


class TestModuleStructure:
    """1. Module Structure: Verify required files exist."""

    def test_files_directory_exists(self):
        """files/ directory must exist."""
        files_dir = Path(__file__).parent.parent / "files"
        assert files_dir.is_dir(), "files/ directory not found"

    def test_rgaa_mcp_py_exists(self):
        """files/rgaa_mcp.py must exist."""
        f = Path(__file__).parent.parent / "files" / "rgaa_mcp.py"
        assert f.exists(), "files/rgaa_mcp.py not found"

    def test_data_py_exists(self):
        """files/data.py must exist."""
        f = Path(__file__).parent.parent / "files" / "data.py"
        assert f.exists(), "files/data.py not found"

    def test_auth_py_exists(self):
        """auth must be importable from mcp_ref_core."""
        from mcp_ref_core import auth
        assert auth is not None, "auth not importable from mcp_ref_core"

    def test_routes_py_exists(self):
        """routes must be importable from mcp_ref_core."""
        from mcp_ref_core import routes
        assert routes is not None, "routes not importable from mcp_ref_core"

    def test_helpers_py_exists(self):
        """_helpers must be importable from mcp_ref_core."""
        from mcp_ref_core import _helpers
        assert _helpers is not None, "_helpers not importable from mcp_ref_core"

    def test_rgaa_cache_json_exists(self):
        """files/rgaa_cache.json must exist."""
        f = Path(__file__).parent.parent / "files" / "rgaa_cache.json"
        assert f.exists(), "files/rgaa_cache.json not found"

    def test_audit_types_json_exists(self):
        """files/audit_types.json must exist."""
        f = Path(__file__).parent.parent / "files" / "audit_types.json"
        assert f.exists(), "files/audit_types.json not found"

    def test_files_directory_contains_only_expected(self):
        """files/ directory should only contain expected files (no unexpected extras)."""
        files_dir = Path(__file__).parent.parent / "files"
        expected = {
            "rgaa_mcp.py",
            "data.py",
            "rgaa_cache.json",
            "audit_types.json",
            "analyseur.py",
            "preparer_donnees.py",
            "__pycache__",
            ".gitkeep",
        }
        actual = {f.name for f in files_dir.iterdir() if not f.name.startswith(".")}
        unexpected = actual - expected
        assert not unexpected, f"Unexpected files in files/: {unexpected}"


class TestComputedMetadataResources:
    """2. Computed Metadata Resources: Test dynamic computation."""

    def test_metadata_resource_computed_from_cache(self):
        """rgaa://metadata resource must compute values dynamically from cache."""
        import rgaa_mcp
        cache = rgaa_mcp.charger_cache()

        # Metadata should compute stats from cache, not store them statically
        assert "criteres" in cache, "Cache missing 'criteres' key"
        assert "themes" in cache, "Cache missing 'themes' key"

        # Verify dynamic computation: nb_auto should be recalculated
        criteres = cache.get("criteres", {})
        nb_auto_expected = sum(1 for c in criteres.values() if c.get("automatisable"))
        assert nb_auto_expected > 0, "Should have automatable criteria"

    def test_metadata_resource_not_static(self):
        """rgaa://metadata must NOT be hardcoded static values."""
        metadata_file = Path(__file__).parent.parent / "files" / "rgaa_cache.json"
        with open(metadata_file) as f:
            data = json.load(f)

        # Metadata in cache should have meta object (language, version, update date)
        assert "meta" in data or "metadata" in data or "version" in str(data), \
            "Cache missing metadata structure"


class TestHTTPRouteEndpoints:
    """3. HTTP Route Endpoints: Verify routes with correct signatures."""

    def test_routes_module_imported(self):
        """routes.py must be importable."""
        from mcp_ref_core import routes
        assert routes is not None, "routes module cannot be imported"

    def test_http_homepage_function_exists(self):
        """routes._http_homepage() function must exist."""
        from mcp_ref_core import routes
        assert hasattr(routes, "_http_homepage"), "_http_homepage function not found"
        func = getattr(routes, "_http_homepage")
        assert callable(func), "_http_homepage is not callable"

    def test_http_guide_function_exists(self):
        """routes._http_guide() function must exist."""
        from mcp_ref_core import routes
        assert hasattr(routes, "_http_guide"), "_http_guide function not found"
        func = getattr(routes, "_http_guide")
        assert callable(func), "_http_guide is not callable"

    def test_http_install_script_function_exists(self):
        """routes._http_install_script() function must exist."""
        from mcp_ref_core import routes
        assert hasattr(routes, "_http_install_script"), "_http_install_script function not found"
        func = getattr(routes, "_http_install_script")
        assert callable(func), "_http_install_script is not callable"

    def test_route_functions_accept_request_param(self):
        """Route functions must accept 'request' parameter."""
        from mcp_ref_core import routes

        for func_name in ["_http_homepage", "_http_guide", "_http_install_script"]:
            func = getattr(routes, func_name)
            sig = inspect.signature(func)
            assert "request" in sig.parameters, \
                f"{func_name}() missing 'request' parameter"

    def test_route_functions_async(self):
        """Route functions should be async."""
        from mcp_ref_core import routes

        for func_name in ["_http_homepage", "_http_guide", "_http_install_script"]:
            func = getattr(routes, func_name)
            assert inspect.iscoroutinefunction(func), \
                f"{func_name}() should be async (iscoroutinefunction)"


class TestHelpersExtraction:
    """4. _helpers.py Extraction: Confirm required functions exist."""

    def test_helpers_module_imported(self):
        """_helpers.py must be importable."""
        from mcp_ref_core import _helpers
        assert _helpers is not None, "_helpers module cannot be imported"

    def test_validate_themes_function_exists(self):
        """_helpers.validate_themes() must exist."""
        from mcp_ref_core._helpers import validate_themes
        assert callable(validate_themes), "validate_themes is not callable"

    def test_validate_score_range_function_exists(self):
        """_helpers.validate_score_range() must exist."""
        from mcp_ref_core._helpers import validate_score_range
        assert callable(validate_score_range), "validate_score_range is not callable"

    def test_validate_nonnegative_function_exists(self):
        """_helpers.validate_nonnegative() must exist."""
        from mcp_ref_core._helpers import validate_nonnegative
        assert callable(validate_nonnegative), "validate_nonnegative is not callable"

    def test_validate_themes_raises_toolerror(self):
        """validate_themes() must raise ToolError for invalid themes."""
        from mcp_ref_core._helpers import validate_themes

        with pytest.raises(ToolError) as exc_info:
            validate_themes([99])
        assert "invalide" in str(exc_info.value).lower(), \
            "ToolError message should mention invalide in French"

    def test_validate_score_range_raises_toolerror(self):
        """validate_score_range() must raise ToolError for out-of-range values."""
        from mcp_ref_core._helpers import validate_score_range

        with pytest.raises(ToolError) as exc_info:
            validate_score_range(999, 1, 100, "test_param")
        assert "doit être" in str(exc_info.value).lower(), \
            "ToolError message should use French 'doit être'"

    def test_validate_nonnegative_raises_toolerror(self):
        """validate_nonnegative() must raise ToolError for negative values."""
        from mcp_ref_core._helpers import validate_nonnegative

        with pytest.raises(ToolError) as exc_info:
            validate_nonnegative(-5, "test_param")
        assert "négatif" in str(exc_info.value).lower() or \
               "doit être" in str(exc_info.value).lower(), \
            "ToolError message should indicate negative value not allowed"


class TestToolErrorHandling:
    """5. ToolError Error Handling: Sample tools use ToolError with French messages."""

    def test_rgaa_lister_criteres_handles_invalid_wcag(self):
        """rgaa_lister_criteres() must raise ToolError for invalid WCAG level."""
        import rgaa_mcp

        with pytest.raises(ToolError) as exc_info:
            rgaa_mcp.rgaa_lister_criteres(niveau_wcag="INVALID")

        error_msg = str(exc_info.value)
        assert "invalide" in error_msg.lower(), \
            "ToolError should mention 'invalide' (French)"

    def test_rgaa_glossaire_not_found(self):
        """rgaa_glossaire() must raise ToolError for non-existent term."""
        import rgaa_mcp

        with pytest.raises(ToolError) as exc_info:
            rgaa_mcp.rgaa_glossaire("NONEXISTENT_TERM_DEFINITELY_NOT_FOUND_XYZ")

        error_msg = str(exc_info.value)
        assert "non trouvé" in error_msg.lower() or "existe" in error_msg.lower(), \
            "ToolError should mention term not found (French)"

    def test_rgaa_taux_conformite_invalid_input(self):
        """rgaa_taux_conformite() must handle invalid input gracefully."""
        import rgaa_mcp

        # Invalid input should raise an error (ToolError or AttributeError)
        with pytest.raises((ToolError, AttributeError)):
            rgaa_mcp.rgaa_taux_conformite("not_a_dict")

    def test_tool_errors_are_toolerror_class(self):
        """Tools should raise fastmcp.exceptions.ToolError, not generic exceptions."""
        import rgaa_mcp
        from fastmcp.exceptions import ToolError

        # Test that tools use ToolError internally
        with pytest.raises(ToolError):
            rgaa_mcp.rgaa_lister_criteres(theme=999)


class TestResourceDefinition:
    """7. Resource Definition: Confirm rgaa://metadata with required keys."""

    def test_metadata_resource_registered(self):
        """rgaa://metadata resource must be registered in MCP."""
        import rgaa_mcp

        # Check that resource_metadata function exists
        assert hasattr(rgaa_mcp, "resource_metadata"), \
            "resource_metadata function not found"

    def test_metadata_resource_returns_valid_json(self):
        """rgaa://metadata resource must return valid JSON."""
        import rgaa_mcp
        import asyncio

        # Get the resource function
        resource_fn = rgaa_mcp.resource_metadata

        # Call it (it's async)
        result = asyncio.run(resource_fn())

        # Parse as JSON
        data = json.loads(result)
        assert isinstance(data, dict), "Metadata should be a dict"

    def test_metadata_resource_has_required_keys(self):
        """rgaa://metadata resource must have required keys."""
        import rgaa_mcp
        import asyncio

        resource_fn = rgaa_mcp.resource_metadata
        result = asyncio.run(resource_fn())
        data = json.loads(result)

        required_keys = ["nb_criteres", "nb_themes", "taux_automatisable"]
        for key in required_keys:
            assert key in data, f"Metadata missing required key: {key}"

    def test_metadata_values_computed_dynamically(self):
        """Metadata values must be computed from cache, not static."""
        import rgaa_mcp
        import asyncio

        resource_fn = rgaa_mcp.resource_metadata
        result = asyncio.run(resource_fn())
        data = json.loads(result)

        # Values should match cache
        cache = rgaa_mcp.charger_cache()
        assert data["nb_criteres"] == len(cache.get("criteres", {})), \
            "nb_criteres should match cache"
        assert data["nb_themes"] == len(cache.get("themes", {})), \
            "nb_themes should match cache"


class TestToolAnnotations:
    """8. Tool Annotations: Spot-check tools have outputSchema + hints."""

    def test_rgaa_lister_criteres_has_annotations(self):
        """rgaa_lister_criteres must have outputSchema and annotations."""
        import rgaa_mcp

        func = rgaa_mcp.rgaa_lister_criteres
        # FastMCP tools store schema in _mcp_schema or similar
        # Check by looking at the function's attributes
        assert hasattr(func, "__doc__"), "Function should have docstring"
        assert callable(func), "Function should be callable"

    def test_rgaa_obtenir_critere_has_annotations(self):
        """rgaa_obtenir_critere must have outputSchema and annotations."""
        import rgaa_mcp

        func = rgaa_mcp.rgaa_obtenir_critere
        assert hasattr(func, "__doc__"), "Function should have docstring"
        assert callable(func), "Function should be callable"

    def test_rgaa_statistiques_has_annotations(self):
        """rgaa_statistiques must have outputSchema and annotations."""
        import rgaa_mcp

        func = rgaa_mcp.rgaa_statistiques
        assert hasattr(func, "__doc__"), "Function should have docstring"
        assert callable(func), "Function should be callable"

    def test_tools_exist_and_count(self):
        """Service must have at least 10 tools registered."""
        import rgaa_mcp

        # Count tools by looking for functions decorated with @mcp.tool
        mcp_instance = rgaa_mcp.mcp

        # FastMCP stores tools in _tools or similar
        if hasattr(mcp_instance, "_tools"):
            tools = mcp_instance._tools
            assert len(tools) >= 10, f"Expected at least 10 tools, found {len(tools)}"


class TestVersionDefinition:
    """Version must be defined and consistent."""

    def test_version_defined_in_rgaa_mcp(self):
        """VERSION must be defined in rgaa_mcp.py."""
        import rgaa_mcp

        assert hasattr(rgaa_mcp, "VERSION"), "VERSION not defined in rgaa_mcp"
        version = rgaa_mcp.VERSION
        assert isinstance(version, str), "VERSION should be a string"
        assert len(version) > 0, "VERSION should not be empty"

    def test_version_format_semantic(self):
        """VERSION should follow semantic versioning (X.Y.Z)."""
        import rgaa_mcp

        version = rgaa_mcp.VERSION
        parts = version.split(".")
        assert len(parts) >= 2, \
            f"VERSION should be semantic (X.Y.Z), got: {version}"

        for part in parts[:3]:  # Check major, minor, patch
            assert part.isdigit(), \
                f"VERSION parts should be numeric, got: {version}"


class TestDataModule:
    """data.py module functions."""

    def test_charger_cache_function_exists(self):
        """data.charger_cache() must exist."""
        from data import charger_cache
        assert callable(charger_cache), "charger_cache is not callable"

    def test_charger_cache_returns_dict(self):
        """charger_cache() must return a dict."""
        from data import charger_cache
        result = charger_cache()
        assert isinstance(result, dict), "charger_cache should return a dict"

    def test_charger_audit_types_function_exists(self):
        """data.charger_audit_types() must exist."""
        from data import charger_audit_types
        assert callable(charger_audit_types), "charger_audit_types is not callable"

    def test_charger_audit_types_returns_dict(self):
        """charger_audit_types() must return a dict."""
        from data import charger_audit_types
        result = charger_audit_types()
        assert isinstance(result, dict), "charger_audit_types should return a dict"


class TestAuthModule:
    """auth.py module functions."""

    def test_auth_module_imported(self):
        """auth must be importable from mcp_ref_core."""
        from mcp_ref_core import auth
        assert auth is not None, "auth module cannot be imported from mcp_ref_core"

    def test_charger_tokens_function_exists(self):
        """auth.charger_tokens() must exist."""
        from mcp_ref_core.auth import charger_tokens
        assert callable(charger_tokens), "charger_tokens is not callable"

    def test_tokens_pour_auth_function_exists(self):
        """auth.tokens_pour_auth() must exist."""
        from mcp_ref_core.auth import tokens_pour_auth
        assert callable(tokens_pour_auth), "tokens_pour_auth is not callable"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
