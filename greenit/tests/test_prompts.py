"""
Tests des prompts MCP GreenIT.

Exécution:
    cd /chemin/vers/projet
    pytest tests/test_prompts.py -v
"""

import sys
from pathlib import Path

# Ajouter le dossier files/ au path pour importer le module
sys.path.insert(0, str(Path(__file__).parent.parent / "files"))

import pytest
import greenit_mcp as mcp_module


class TestGreenITPrompts:
    """Test that all 8 GreenIT prompts are defined and return valid templates."""

    def test_audit_ecoindex_returns_template(self):
        """Test audit_ecoindex prompt exists and returns a non-empty template."""
        result = mcp_module.audit_ecoindex("https://example.com")
        assert isinstance(result, str), "audit_ecoindex should return a string"
        assert len(result) > 50, "Template should be substantial (>50 chars)"
        assert "greenit_calculer_ecoindex" in result, "Should reference calculer_ecoindex tool"

    def test_audit_ecoindex_with_focus_parameter(self):
        """Test audit_ecoindex handles focus parameter."""
        result = mcp_module.audit_ecoindex("https://example.com", focus="dom")
        assert isinstance(result, str)
        assert "dom" in result.lower(), "Template should mention the focus parameter"

    def test_rapport_impact_returns_template(self):
        """Test rapport_impact prompt exists and returns a non-empty template."""
        result = mcp_module.rapport_impact("test results")
        assert isinstance(result, str), "rapport_impact should return a string"
        assert len(result) > 50, "Template should be substantial (>50 chars)"

    def test_expliquer_fiche_returns_template(self):
        """Test expliquer_fiche prompt exists and returns a non-empty template."""
        result = mcp_module.expliquer_fiche("RWEB_0001")
        assert isinstance(result, str), "expliquer_fiche should return a string"
        assert len(result) > 50, "Template should be substantial (>50 chars)"
        assert "greenit_obtenir_fiche_complete" in result, "Should reference obtenir_fiche_complete tool"

    def test_fiches_par_lifecycle_returns_template(self):
        """Test fiches_par_lifecycle prompt exists and returns a non-empty template."""
        result = mcp_module.fiches_par_lifecycle("conception")
        assert isinstance(result, str), "fiches_par_lifecycle should return a string"
        assert "conception" in result.lower(), "Template should mention the phase parameter"
        assert "greenit_lister_fiches" in result, "Should reference lister_fiches tool"

    def test_fiches_par_lifecycle_with_impact_min(self):
        """Test fiches_par_lifecycle handles impact_min parameter."""
        result = mcp_module.fiches_par_lifecycle("developpement", impact_min=4)
        assert isinstance(result, str)
        assert "4" in result, "Should include the impact_min value in template"

    def test_checklist_ecoindex_returns_template(self):
        """Test checklist_ecoindex prompt exists and returns a non-empty template."""
        result = mcp_module.checklist_ecoindex()
        assert isinstance(result, str), "checklist_ecoindex should return a string"
        assert len(result) > 50, "Template should be substantial (>50 chars)"
        assert "DOM" in result or "dom" in result, "Should mention DOM optimization"

    def test_checklist_ecoindex_with_domaines(self):
        """Test checklist_ecoindex handles domaines parameter."""
        result = mcp_module.checklist_ecoindex(domaines="requests")
        assert isinstance(result, str)
        assert "requests" in result.lower(), "Template should mention the domaines parameter"

    def test_ressources_comparaison_returns_template(self):
        """Test ressources_comparaison prompt exists and returns a non-empty template."""
        result = mcp_module.ressources_comparaison("RWEB_0001,RWEB_0002")
        assert isinstance(result, str), "ressources_comparaison should return a string"
        assert len(result) > 50, "Template should be substantial (>50 chars)"
        assert "greenit_obtenir_fiche_complete" in result, "Should reference obtenir_fiche_complete tool"

    def test_audit_rapide_greenit_returns_template(self):
        """Test audit_rapide_greenit prompt exists and returns a non-empty template."""
        result = mcp_module.audit_rapide_greenit("https://example.com")
        assert isinstance(result, str), "audit_rapide_greenit should return a string"
        assert len(result) > 50, "Template should be substantial (>50 chars)"
        assert "greenit_fiches_prioritaires" in result, "Should reference fiches_prioritaires tool"

    def test_audit_par_ressource_returns_template(self):
        """Test audit_par_ressource prompt exists and returns a non-empty template."""
        result = mcp_module.audit_par_ressource("network")
        assert isinstance(result, str), "audit_par_ressource should return a string"
        assert len(result) > 50, "Template should be substantial (>50 chars)"
        assert "network" in result.lower(), "Should mention the resource parameter"

    def test_audit_par_ressource_with_budget(self):
        """Test audit_par_ressource handles budget parameter."""
        result = mcp_module.audit_par_ressource("cpu", budget=4)
        assert isinstance(result, str)
        assert "4" in result, "Should include the budget value in template"
