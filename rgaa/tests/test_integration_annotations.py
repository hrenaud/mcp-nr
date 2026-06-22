"""Integration tests for MCP tool annotations.

Verifies that all 10 RGAA MCP tools have complete and consistent annotations
across the entire server.
"""

import asyncio
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "files"))

import rgaa_mcp as mcp_module


class TestAnnotationsIntegration:
    """Integration tests verifying annotations across all tools."""

    @pytest.fixture(autouse=True)
    def setup_tools(self):
        """Load all tools from the MCP server."""
        self.tools = asyncio.run(mcp_module.mcp.list_tools())
        assert len(self.tools) >= 10, f"Expected at least 10 tools, found {len(self.tools)}"

    def test_all_tools_have_annotations(self):
        """Verify every tool has annotations dict."""
        for tool in self.tools:
            assert hasattr(tool, 'annotations'), f"Tool {tool.name} missing annotations attribute"
            assert tool.annotations is not None, f"Tool {tool.name} annotations should not be None"

    def test_all_tools_have_four_annotation_types(self):
        """Verify every tool has all four annotation types."""
        expected_keys = {"readOnlyHint", "destructiveHint", "idempotentHint", "openWorldHint"}

        for tool in self.tools:
            tool_keys = set()
            if hasattr(tool.annotations, 'readOnlyHint'):
                tool_keys.add('readOnlyHint')
            if hasattr(tool.annotations, 'destructiveHint'):
                tool_keys.add('destructiveHint')
            if hasattr(tool.annotations, 'idempotentHint'):
                tool_keys.add('idempotentHint')
            if hasattr(tool.annotations, 'openWorldHint'):
                tool_keys.add('openWorldHint')

            missing = expected_keys - tool_keys
            assert not missing, f"Tool {tool.name} missing annotations: {missing}"

    def test_annotation_values_are_booleans(self):
        """Verify all annotation values are booleans."""
        for tool in self.tools:
            assert isinstance(tool.annotations.readOnlyHint, bool), (
                f"Tool {tool.name} annotation 'readOnlyHint' should be boolean, got {type(tool.annotations.readOnlyHint)}"
            )
            assert isinstance(tool.annotations.destructiveHint, bool), (
                f"Tool {tool.name} annotation 'destructiveHint' should be boolean, got {type(tool.annotations.destructiveHint)}"
            )
            assert isinstance(tool.annotations.idempotentHint, bool), (
                f"Tool {tool.name} annotation 'idempotentHint' should be boolean, got {type(tool.annotations.idempotentHint)}"
            )
            assert isinstance(tool.annotations.openWorldHint, bool), (
                f"Tool {tool.name} annotation 'openWorldHint' should be boolean, got {type(tool.annotations.openWorldHint)}"
            )

    def test_read_only_tools_marked_correctly(self):
        """Verify read-only tools are marked with readOnlyHint=True."""
        read_only_tools = {
            "rgaa_lister_criteres",
            "rgaa_obtenir_critere",
            "rgaa_chercher",
            "rgaa_glossaire",
            "rgaa_statistiques",
            "rgaa_types_audit",
            "rgaa_criteres_audit",
            "rgaa_analyser",
            "rgaa_checklist",
            "rgaa_taux_conformite"
        }

        for tool in self.tools:
            if tool.name in read_only_tools:
                assert tool.annotations.readOnlyHint == True, (
                    f"Tool {tool.name} should have readOnlyHint=True"
                )

    def test_no_destructive_tools(self):
        """Verify no tools are marked as destructive."""
        for tool in self.tools:
            assert tool.annotations.destructiveHint == False, (
                f"Tool {tool.name} should have destructiveHint=False"
            )

    def test_idempotent_tools_marked_correctly(self):
        """Verify idempotent tools are marked with idempotentHint=True."""
        idempotent_tools = {
            "rgaa_lister_criteres",
            "rgaa_obtenir_critere",
            "rgaa_chercher",
            "rgaa_glossaire",
            "rgaa_statistiques",
            "rgaa_types_audit",
            "rgaa_criteres_audit",
            "rgaa_checklist",
            "rgaa_taux_conformite"
        }

        for tool in self.tools:
            if tool.name in idempotent_tools:
                assert tool.annotations.idempotentHint == True, (
                    f"Tool {tool.name} should have idempotentHint=True"
                )

    def test_non_idempotent_tools_marked_correctly(self):
        """Verify non-idempotent tools are marked correctly."""
        # rgaa_analyser includes datetime.now() in output, making it non-idempotent
        non_idempotent_tools = {"rgaa_analyser"}
        # All other 9 RGAA tools are idempotent - they perform read-only operations
        # with no persistent side effects on data or system state
        idempotent_tools = {
            "rgaa_lister_criteres",
            "rgaa_obtenir_critere",
            "rgaa_chercher",
            "rgaa_glossaire",
            "rgaa_statistiques",
            "rgaa_checklist",
            "rgaa_taux_conformite",
            "rgaa_types_audit",
            "rgaa_criteres_audit"
        }

        for tool in self.tools:
            if tool.name in non_idempotent_tools:
                assert tool.annotations.idempotentHint == False, (
                    f"Tool {tool.name} should have idempotentHint=False (includes datetime in output)"
                )
            elif tool.name in idempotent_tools:
                assert tool.annotations.idempotentHint == True, (
                    f"Tool {tool.name} should have idempotentHint=True"
                )

    def test_open_world_hints_correct(self):
        """Verify openWorldHint is set appropriately for each tool."""
        open_world_tools = {
            "rgaa_chercher",         # Accepts any search query
            "rgaa_analyser",         # Accepts any URL
            "rgaa_checklist"         # Accepts any theme/criteria combination
        }

        for tool in self.tools:
            expected_open_world = tool.name in open_world_tools
            actual_open_world = tool.annotations.openWorldHint
            assert actual_open_world == expected_open_world, (
                f"Tool {tool.name} openWorldHint should be {expected_open_world}, "
                f"got {actual_open_world}"
            )

    def test_annotation_consistency_across_similar_tools(self):
        """Verify similar tools have consistent annotation patterns."""
        # All listing/retrieval tools (except analyser) should have same basic pattern
        data_retrieval_tools = {
            "rgaa_lister_criteres",
            "rgaa_obtenir_critere",
            "rgaa_types_audit",
            "rgaa_criteres_audit",
            "rgaa_glossaire",
            "rgaa_statistiques"
        }

        for tool in self.tools:
            if tool.name in data_retrieval_tools:
                assert tool.annotations.readOnlyHint == True, (
                    f"Tool {tool.name} should be read-only"
                )
                assert tool.annotations.destructiveHint == False, (
                    f"Tool {tool.name} should not be destructive"
                )
                assert tool.annotations.idempotentHint == True, (
                    f"Tool {tool.name} should be idempotent"
                )


class TestAnnotationCompleteness:
    """Verify that having annotations is complete workflow."""

    @pytest.fixture(autouse=True)
    def setup_tools(self):
        """Load all tools from the MCP server."""
        self.tools = asyncio.run(mcp_module.mcp.list_tools())

    def test_all_10_tools_present(self):
        """Verify all 10 RGAA tools are registered."""
        expected_tools = {
            "rgaa_lister_criteres",
            "rgaa_obtenir_critere",
            "rgaa_chercher",
            "rgaa_glossaire",
            "rgaa_statistiques",
            "rgaa_types_audit",
            "rgaa_criteres_audit",
            "rgaa_analyser",
            "rgaa_checklist",
            "rgaa_taux_conformite"
        }

        actual_tools = {t.name for t in self.tools}
        missing = expected_tools - actual_tools
        assert not missing, f"Missing tools: {missing}"

    def test_tool_descriptions_not_empty(self):
        """Verify every tool has a description."""
        for tool in self.tools:
            assert tool.description, f"Tool {tool.name} has empty description"
            assert len(tool.description) > 10, f"Tool {tool.name} description too short"

    def test_tool_descriptions_are_strings(self):
        """Verify every tool description is a string."""
        for tool in self.tools:
            assert isinstance(tool.description, str), (
                f"Tool {tool.name} description should be string, got {type(tool.description)}"
            )


class TestAnnotationIntegrationWithErrorHandling:
    """Verify that annotated tools with improved error messages work together."""

    @pytest.fixture(autouse=True)
    def setup_tools(self):
        """Load all tools from the MCP server."""
        self.tools = asyncio.run(mcp_module.mcp.list_tools())

    def test_tools_with_error_improvements_have_annotations(self):
        """Verify tools with improved error messages also have complete annotations."""
        error_improved_tools = {
            "rgaa_obtenir_critere",
            "rgaa_criteres_audit",
            "rgaa_analyser",
            "rgaa_checklist",
            "rgaa_taux_conformite"
        }

        for tool in self.tools:
            if tool.name in error_improved_tools:
                # Must have all 4 annotations
                assert hasattr(tool.annotations, 'readOnlyHint'), (
                    f"Tool {tool.name} with error improvements missing readOnlyHint"
                )
                assert hasattr(tool.annotations, 'destructiveHint'), (
                    f"Tool {tool.name} with error improvements missing destructiveHint"
                )
                assert hasattr(tool.annotations, 'idempotentHint'), (
                    f"Tool {tool.name} with error improvements missing idempotentHint"
                )
                assert hasattr(tool.annotations, 'openWorldHint'), (
                    f"Tool {tool.name} with error improvements missing openWorldHint"
                )
                # Must have description
                assert tool.description, f"Tool {tool.name} missing description"

    def test_annotation_pattern_consistency_by_category(self):
        """Verify annotation patterns are consistent within tool categories."""
        # Category 1: Reference data tools (no network calls, accept fixed filters)
        reference_tools = {
            "rgaa_lister_criteres",  # Accepts only themes 1-13 and fixed WCAG levels
            "rgaa_types_audit"
        }

        for tool in self.tools:
            if tool.name in reference_tools:
                # These should be read-only, non-destructive, idempotent, NOT open-world
                assert tool.annotations.readOnlyHint == True
                assert tool.annotations.destructiveHint == False
                assert tool.annotations.idempotentHint == True
                assert tool.annotations.openWorldHint == False

        # Category 2: Detail retrieval tools (no network calls, accept specific IDs)
        detail_tools = {
            "rgaa_obtenir_critere",
            "rgaa_glossaire",
            "rgaa_criteres_audit"
        }

        for tool in self.tools:
            if tool.name in detail_tools:
                # These should be read-only, non-destructive, idempotent, NOT open-world
                assert tool.annotations.readOnlyHint == True
                assert tool.annotations.destructiveHint == False
                assert tool.annotations.idempotentHint == True
                assert tool.annotations.openWorldHint == False

        # Category 3: Analysis tools (network calls, accept URLs)
        analysis_tools = {
            "rgaa_analyser"
        }

        for tool in self.tools:
            if tool.name in analysis_tools:
                # These should be read-only, non-idempotent (includes datetime), and open-world
                assert tool.annotations.readOnlyHint == True
                assert tool.annotations.destructiveHint == False
                assert tool.annotations.idempotentHint == False
                assert tool.annotations.openWorldHint == True
