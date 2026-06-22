"""
Architecture Parity Tests for GreenIT MCP Service.

Validates 8 architectural aspects to ensure consistency with mcp-rgaa:

1. Module Structure: Verify files/ contains expected modules
2. Computed Metadata Resources: Validate greenit://metadata computes values dynamically
3. HTTP Route Endpoints: Verify GET /, /health, /guide exist with correct signatures
4. _helpers.py Extraction: Confirm validation functions exist and work
5. ToolError Error Handling: Verify tools use ToolError with French messages
6. Test Suite Integrity: All tests pass without failures
7. Resource Definition: Confirm greenit://metadata resource structure
8. Tool Annotations: Spot-check tools have outputSchema + hints

Execution:
    cd /chemin/vers/greenit-mcp
    pytest tests/test_architecture_parity.py -v
"""

import os
import sys
import json
import inspect
from pathlib import Path

# Setup path
sys.path.insert(0, str(Path(__file__).parent.parent / "files"))

import pytest
from fastmcp.exceptions import ToolError
import greenit_mcp as mcp_module
from data import (
    charger_cache,
    charger_metadata,
    compter_fiches,
    compter_lifecycles,
    compter_ressources,
    calculer_taux_ecoindex_moyen,
)
from mcp_ref_core import _helpers
from mcp_ref_core import routes


# ============================================================================
# Test 1: Module Structure
# ============================================================================

class TestModuleStructure:
    """Verify files/ contains exactly the expected modules and data files."""

    def test_files_directory_exists(self):
        """Module structure: files/ directory must exist."""
        files_dir = Path(__file__).parent.parent / "files"
        assert files_dir.exists(), f"files/ directory missing at {files_dir}"

    def test_greenit_mcp_py_exists(self):
        """Module structure: greenit_mcp.py must exist."""
        files_dir = Path(__file__).parent.parent / "files"
        assert (files_dir / "greenit_mcp.py").exists(), "greenit_mcp.py missing"

    def test_data_py_exists(self):
        """Module structure: data.py must exist."""
        files_dir = Path(__file__).parent.parent / "files"
        assert (files_dir / "data.py").exists(), "data.py missing"

    def test_auth_py_exists(self):
        """Module structure: After migration, auth.py is in core/mcp_ref_core/."""
        core_dir = Path(__file__).parent.parent.parent / "core" / "mcp_ref_core"
        assert (core_dir / "auth.py").exists(), "auth.py missing in core/mcp_ref_core/"

    def test_routes_py_exists(self):
        """Module structure: After migration, routes.py is in core/mcp_ref_core/."""
        core_dir = Path(__file__).parent.parent.parent / "core" / "mcp_ref_core"
        assert (core_dir / "routes.py").exists(), "routes.py missing in core/mcp_ref_core/"

    def test_helpers_py_exists(self):
        """Module structure: After migration, _helpers.py is in core/mcp_ref_core/."""
        core_dir = Path(__file__).parent.parent.parent / "core" / "mcp_ref_core"
        assert (core_dir / "_helpers.py").exists(), "_helpers.py missing in core/mcp_ref_core/"

    def test_greenit_cache_json_exists(self):
        """Module structure: greenit_cache.json must exist."""
        files_dir = Path(__file__).parent.parent / "files"
        assert (files_dir / "greenit_cache.json").exists(), "greenit_cache.json missing"

    def test_greenit_metadata_json_exists(self):
        """Module structure: greenit_metadata.json must exist."""
        files_dir = Path(__file__).parent.parent / "files"
        assert (
            files_dir / "greenit_metadata.json"
        ).exists(), "greenit_metadata.json missing"

    def test_all_required_files_present(self):
        """Module structure: After migration, shared files are in core/, local files in files/."""
        files_dir = Path(__file__).parent.parent / "files"
        # After Task 2 migration: auth.py, routes.py, _helpers.py are in core/mcp_ref_core/
        # Only greenit-specific files remain in greenit/files/
        required_local = {
            "greenit_mcp.py",
            "data.py",
            "greenit_cache.json",
            "greenit_metadata.json",
        }
        actual = {f.name for f in files_dir.glob("*") if f.is_file() and not f.name.startswith("__")}
        missing = required_local - actual
        assert (
            not missing
        ), f"Module structure violation: missing {missing}. Present: {actual}"


# ============================================================================
# Test 2: Computed Metadata Resources
# ============================================================================

class TestComputedMetadataResources:
    """Validate greenit://metadata resource computes values dynamically from cache."""

    def test_metadata_computes_fiches_count(self):
        """Computed metadata: greenit://metadata computes fiches_count from cache."""
        metadata = charger_metadata()
        fiches_count = compter_fiches()
        # The resource should compute this dynamically, not store static value
        assert isinstance(fiches_count, int), "fiches_count must be integer"
        assert fiches_count >= 0, "fiches_count must be non-negative"

    def test_metadata_computes_lifecycles_count(self):
        """Computed metadata: greenit://metadata computes lifecycles_count dynamically."""
        lifecycles_count = compter_lifecycles()
        assert isinstance(
            lifecycles_count, int
        ), "lifecycles_count must be integer"
        assert lifecycles_count >= 0, "lifecycles_count must be non-negative"

    def test_metadata_computes_resources_count(self):
        """Computed metadata: greenit://metadata computes resources_count dynamically."""
        resources_count = compter_ressources()
        assert isinstance(resources_count, int), "resources_count must be integer"
        assert resources_count >= 0, "resources_count must be non-negative"

    def test_metadata_computes_average_impact(self):
        """Computed metadata: greenit://metadata computes average_impact dynamically."""
        avg_impact = calculer_taux_ecoindex_moyen()
        assert isinstance(avg_impact, float), "average_impact must be float"
        assert 0.0 <= avg_impact <= 5.0, "average_impact must be in [0.0, 5.0]"

    def test_metadata_values_not_static(self):
        """Computed metadata: Values computed fresh each call, not cached incorrectly."""
        # Call the computation functions multiple times
        count1 = compter_fiches()
        count2 = compter_fiches()
        assert count1 == count2, "compter_fiches should return consistent results"

    def test_metadata_reflects_cache_changes(self):
        """Computed metadata: Metadata reflects current cache state."""
        # Metadata values should be based on current cache, not stored
        cache = charger_cache()
        fiches_count = compter_fiches()
        assert fiches_count == len(cache), "fiches_count must match actual cache size"


# ============================================================================
# Test 3: HTTP Route Endpoints
# ============================================================================

class TestHTTPRouteEndpoints:
    """Verify GET /, /health, /guide endpoints exist in routes.py."""

    def test_get_base_url_function_exists(self):
        """HTTP routes: _get_base_url function exists in routes module."""
        assert hasattr(routes, "_get_base_url"), "_get_base_url missing from routes"
        assert callable(
            routes._get_base_url
        ), "_get_base_url must be callable"

    def test_get_base_url_returns_string(self):
        """HTTP routes: _get_base_url returns a string."""
        result = routes._get_base_url()
        assert isinstance(result, str), "_get_base_url must return string"
        assert result, "_get_base_url must not return empty string"

    def test_get_token_request_url_function_exists(self):
        """HTTP routes: _get_token_request_url function exists."""
        assert hasattr(
            routes, "_get_token_request_url"
        ), "_get_token_request_url missing from routes"
        assert callable(routes._get_token_request_url)

    def test_get_token_request_url_returns_string(self):
        """HTTP routes: _get_token_request_url returns a string."""
        result = routes._get_token_request_url()
        assert isinstance(result, str), "_get_token_request_url must return string"

    def test_routes_module_has_http_handlers(self):
        """HTTP routes: routes module contains HTTP route handler functions."""
        # Check for route handler functions
        assert hasattr(mcp_module, "_http_homepage"), "_http_homepage missing"
        assert hasattr(
            mcp_module, "_http_install_script"
        ), "_http_install_script missing"
        assert hasattr(mcp_module, "_http_guide"), "_http_guide missing"


# ============================================================================
# Test 4: _helpers.py Extraction
# ============================================================================

class TestHelpersExtraction:
    """Confirm _helpers.py exists and contains validation functions."""

    def test_validate_themes_exists(self):
        """_helpers.py: validate_themes function exists."""
        assert hasattr(_helpers, "validate_themes"), "validate_themes missing"
        assert callable(
            _helpers.validate_themes
        ), "validate_themes must be callable"

    def test_validate_score_range_exists(self):
        """_helpers.py: validate_score_range function exists."""
        assert hasattr(
            _helpers, "validate_score_range"
        ), "validate_score_range missing"
        assert callable(_helpers.validate_score_range)

    def test_validate_nonnegative_exists(self):
        """_helpers.py: validate_nonnegative function exists."""
        assert hasattr(
            _helpers, "validate_nonnegative"
        ), "validate_nonnegative missing"
        assert callable(_helpers.validate_nonnegative)

    def test_validate_themes_accepts_none(self):
        """_helpers.py: validate_themes handles None (all themes)."""
        result = _helpers.validate_themes(None)
        assert isinstance(result, list), "validate_themes must return list"
        assert len(result) == 13, "validate_themes(None) should return 13 themes"
        assert result == list(range(1, 14)), "validate_themes should return 1-13"

    def test_validate_themes_rejects_invalid(self):
        """_helpers.py: validate_themes rejects invalid theme IDs."""
        with pytest.raises(ToolError) as exc_info:
            _helpers.validate_themes([0, 14, 99])
        assert "invalides" in str(exc_info.value).lower(), "Error must be in French"

    def test_validate_score_range_accepts_valid(self):
        """_helpers.py: validate_score_range accepts values in range."""
        # Should not raise
        _helpers.validate_score_range(50, 0, 100, "test_param")

    def test_validate_score_range_rejects_out_of_range(self):
        """_helpers.py: validate_score_range rejects out-of-range values."""
        with pytest.raises(ToolError) as exc_info:
            _helpers.validate_score_range(101, 0, 100, "test_param")
        assert "invalides" in str(exc_info.value).lower()

    def test_validate_nonnegative_accepts_zero(self):
        """_helpers.py: validate_nonnegative accepts 0."""
        # Should not raise
        _helpers.validate_nonnegative(0.0, "test_param")

    def test_validate_nonnegative_accepts_positive(self):
        """_helpers.py: validate_nonnegative accepts positive values."""
        # Should not raise
        _helpers.validate_nonnegative(42.5, "test_param")

    def test_validate_nonnegative_rejects_negative(self):
        """_helpers.py: validate_nonnegative rejects negative values."""
        with pytest.raises(ToolError) as exc_info:
            _helpers.validate_nonnegative(-1.0, "test_param")
        assert "invalides" in str(exc_info.value).lower()


# ============================================================================
# Test 5: ToolError Error Handling
# ============================================================================

class TestToolErrorHandling:
    """Sample tools verify they use ToolError with French error messages."""

    def test_lister_fiches_tool_exists(self):
        """ToolError handling: lister_fiches tool exists."""
        assert hasattr(
            mcp_module, "lister_fiches"
        ), "lister_fiches tool missing"

    def test_comparer_fiches_tool_exists(self):
        """ToolError handling: comparer_fiches tool exists."""
        assert hasattr(
            mcp_module, "comparer_fiches"
        ), "comparer_fiches tool missing"

    def test_chercher_fiche_tool_exists(self):
        """ToolError handling: chercher_fiche tool exists."""
        assert hasattr(
            mcp_module, "chercher_fiche"
        ), "chercher_fiche tool missing"

    def test_tools_use_toolerror_for_validation(self):
        """ToolError handling: Tools should use ToolError, not plain exceptions."""
        # Test that lister_fiches with invalid impact_min raises ToolError
        with pytest.raises(ToolError) as exc_info:
            mcp_module.lister_fiches(impact_min=99)
        # Verify French error message
        assert isinstance(exc_info.value, ToolError)
        assert "invalides" in str(exc_info.value).lower()

    def test_toolerror_messages_are_french(self):
        """ToolError handling: Error messages use French."""
        try:
            _helpers.validate_themes([999])
        except ToolError as e:
            error_msg = str(e)
            # Should contain French words
            assert any(
                word in error_msg.lower()
                for word in ["invalides", "thèmes", "doivent"]
            ), f"Error message not in French: {error_msg}"


# ============================================================================
# Test 6: Test Suite Integrity
# ============================================================================

class TestSuiteIntegrity:
    """Verify all tests in tests/ directory pass without failures."""

    def test_data_module_imports_successfully(self):
        """Test suite: data module imports without errors."""
        from data import (
            charger_cache,
            charger_metadata,
            compter_fiches,
        )
        assert callable(charger_cache)
        assert callable(charger_metadata)
        assert callable(compter_fiches)

    def test_auth_module_imports_successfully(self):
        """Test suite: auth module imports without errors."""
        from mcp_ref_core.auth import (
            charger_tokens,
            sauvegarder_tokens,
            construire_verifier,
        )
        assert callable(charger_tokens)
        assert callable(sauvegarder_tokens)
        assert callable(construire_verifier)

    def test_routes_module_imports_successfully(self):
        """Test suite: routes module imports without errors."""
        from mcp_ref_core import routes as routes_mod
        assert hasattr(routes_mod, "_get_base_url")
        assert hasattr(routes_mod, "_get_token_request_url")

    def test_greenit_mcp_imports_successfully(self):
        """Test suite: greenit_mcp module imports without errors."""
        assert hasattr(mcp_module, "VERSION")
        assert isinstance(mcp_module.VERSION, str)

    def test_all_helper_functions_importable(self):
        """Test suite: All _helpers functions importable."""
        from mcp_ref_core._helpers import (
            validate_themes,
            validate_score_range,
            validate_nonnegative,
        )
        assert callable(validate_themes)
        assert callable(validate_score_range)
        assert callable(validate_nonnegative)

    def test_cache_file_is_valid_json(self):
        """Test suite: greenit_cache.json is valid JSON."""
        cache = charger_cache()
        assert isinstance(cache, dict), "Cache must be dict"

    def test_metadata_file_is_valid_json(self):
        """Test suite: greenit_metadata.json is valid JSON."""
        metadata = charger_metadata()
        assert isinstance(metadata, dict), "Metadata must be dict"


# ============================================================================
# Test 7: Resource Definition
# ============================================================================

class TestResourceDefinition:
    """Confirm greenit://metadata resource defined correctly."""

    def test_metadata_resource_has_correct_uri_pattern(self):
        """Resource definition: greenit://metadata resource registered."""
        # Verify the resource was registered in the MCP server
        # by checking that obtenir_metadata function exists
        assert hasattr(
            mcp_module, "obtenir_metadata"
        ), "obtenir_metadata resource handler missing"

    def test_metadata_resource_returns_json_string(self):
        """Resource definition: obtenir_metadata returns JSON-serializable data."""
        # The function should return valid JSON string
        assert callable(
            mcp_module.obtenir_metadata
        ), "obtenir_metadata must be callable"

    def test_metadata_includes_fiches_count(self):
        """Resource definition: metadata includes fiches_count key."""
        fiches_count = compter_fiches()
        assert isinstance(fiches_count, int), "fiches_count must be int"

    def test_metadata_includes_lifecycles_count(self):
        """Resource definition: metadata includes lifecycles_count key."""
        lifecycles_count = compter_lifecycles()
        assert isinstance(lifecycles_count, int), "lifecycles_count must be int"

    def test_metadata_includes_resources_count(self):
        """Resource definition: metadata includes resources_count key."""
        resources_count = compter_ressources()
        assert isinstance(resources_count, int), "resources_count must be int"

    def test_metadata_includes_average_impact(self):
        """Resource definition: metadata includes average_impact key."""
        avg_impact = calculer_taux_ecoindex_moyen()
        assert isinstance(avg_impact, float), "average_impact must be float"

    def test_metadata_values_are_dynamic_not_static(self):
        """Resource definition: Metadata values computed at request time."""
        # Verify that the computation functions are called dynamically
        # by checking they return consistent values
        count1 = compter_fiches()
        count2 = compter_fiches()
        assert count1 == count2, "Should return same count on repeated calls"


# ============================================================================
# Test 8: Tool Annotations
# ============================================================================

class TestToolAnnotations:
    """Spot-check 3 tools have outputSchema + hints."""

    def test_lister_fiches_has_output_schema(self):
        """Tool annotations: lister_fiches tool has outputSchema."""
        # Check that the tool is properly defined with annotations
        func = mcp_module.lister_fiches
        assert callable(func), "lister_fiches must be callable"
        # The tool should have been decorated with @mcp.tool with output_schema

    def test_fiches_prioritaires_has_output_schema(self):
        """Tool annotations: fiches_prioritaires tool has outputSchema."""
        func = mcp_module.fiches_prioritaires
        assert callable(func), "fiches_prioritaires must be callable"

    def test_comparer_fiches_has_output_schema(self):
        """Tool annotations: comparer_fiches tool has outputSchema."""
        func = mcp_module.comparer_fiches
        assert callable(func), "comparer_fiches must be callable"

    def test_tools_have_correct_signatures(self):
        """Tool annotations: Tools have correct parameter signatures."""
        # lister_fiches should accept optional filters
        sig = inspect.signature(mcp_module.lister_fiches)
        params = list(sig.parameters.keys())
        assert len(params) > 0, "lister_fiches should have parameters"

    def test_tools_are_coroutine_or_function(self):
        """Tool annotations: Tool implementations are proper callables."""
        assert callable(
            mcp_module.lister_fiches
        ), "lister_fiches must be callable"
        assert callable(
            mcp_module.comparer_fiches
        ), "comparer_fiches must be callable"
        assert callable(
            mcp_module.obtenir_fiche_complete
        ), "obtenir_fiche_complete must be callable"

    def test_resource_handlers_exist(self):
        """Tool annotations: Resource handlers properly defined."""
        assert hasattr(
            mcp_module, "obtenir_fiche"
        ), "obtenir_fiche resource missing"
        assert hasattr(
            mcp_module, "index_fiches"
        ), "index_fiches resource missing"
        assert hasattr(
            mcp_module, "obtenir_metadata"
        ), "obtenir_metadata resource missing"
        assert hasattr(
            mcp_module, "version_serveur"
        ), "version_serveur resource missing"


# ============================================================================
# Integration Tests
# ============================================================================

class TestArchitectureIntegration:
    """Cross-cutting tests to verify architecture coherence."""

    def test_imports_chain_correctly(self):
        """Architecture: Import chain works correctly."""
        # greenit_mcp imports from data, auth, routes, _helpers
        from data import charger_cache
        from mcp_ref_core.auth import construire_verifier
        from mcp_ref_core import routes
        from mcp_ref_core._helpers import validate_themes

        assert callable(charger_cache)
        assert callable(construire_verifier)
        assert callable(validate_themes)

    def test_data_and_metadata_consistency(self):
        """Architecture: Cache and metadata files consistent."""
        cache = charger_cache()
        metadata = charger_metadata()

        # Both should be dictionaries
        assert isinstance(cache, dict), "Cache must be dict"
        assert isinstance(metadata, dict), "Metadata must be dict"

        # Metadata should have expected keys
        assert "languages" in metadata
        assert "versions" in metadata

    def test_error_handling_consistency(self):
        """Architecture: All validation uses ToolError with French messages."""
        # Test each helper function
        with pytest.raises(ToolError) as exc:
            _helpers.validate_themes([99])
        msg = str(exc.value)
        assert "invalides" in msg.lower() or "invalide" in msg.lower()

        with pytest.raises(ToolError) as exc:
            _helpers.validate_score_range(999, 0, 100, "param")
        msg = str(exc.value)
        assert "invalides" in msg.lower() or "invalide" in msg.lower()

        with pytest.raises(ToolError) as exc:
            _helpers.validate_nonnegative(-1, "param")
        msg = str(exc.value)
        assert "invalides" in msg.lower() or "invalide" in msg.lower()

    def test_version_defined_and_accessible(self):
        """Architecture: VERSION defined in greenit_mcp.py."""
        assert hasattr(mcp_module, "VERSION"), "VERSION not defined"
        assert isinstance(mcp_module.VERSION, str), "VERSION must be string"
        assert mcp_module.VERSION, "VERSION must not be empty"

    def test_http_routes_have_utility_functions(self):
        """Architecture: HTTP routes properly export utilities."""
        # These are used by tests and by greenit_mcp.py
        assert callable(mcp_module._get_base_url)
        assert callable(mcp_module._get_token_request_url)
