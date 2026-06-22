"""Tests des prompts MCP RGESN."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "files"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "core"))

import rgesn_mcp as mcp_module


# ============================================================================
# Prompts existants
# ============================================================================

def test_audit_ecoconception_returns_template():
    result = mcp_module.audit_ecoconception("https://example.com")
    assert isinstance(result, str) and len(result) > 50
    assert "rgesn_lister_criteres" in result or "rgesn_checklist" in result


def test_audit_ecoconception_with_themes():
    result = mcp_module.audit_ecoconception("https://example.com", themes="1,4")
    assert "1,4" in result


def test_expliquer_critere_returns_template():
    result = mcp_module.expliquer_critere("1.1")
    assert isinstance(result, str) and len(result) > 50
    assert "rgesn_obtenir_critere" in result
    assert "1.1" in result


def test_checklist_prioritaire_returns_template():
    result = mcp_module.checklist_prioritaire()
    assert isinstance(result, str) and len(result) > 50
    assert "Prioritaire" in result


def test_checklist_prioritaire_with_themes():
    result = mcp_module.checklist_prioritaire(themes="1,4")
    assert "1,4" in result


# ============================================================================
# Nouveaux prompts
# ============================================================================

def test_rapport_conformite_returns_template():
    result = mcp_module.rapport_conformite('{"1.1": "C", "1.2": "NC"}')
    assert isinstance(result, str) and len(result) > 50
    assert "rgesn_taux_conformite" in result


def test_checklist_par_metier_returns_template():
    result = mcp_module.checklist_par_metier("développeur")
    assert isinstance(result, str) and len(result) > 50
    assert "développeur" in result


def test_checklist_par_metier_default():
    result = mcp_module.checklist_par_metier()
    assert isinstance(result, str) and len(result) > 50


def test_audit_rapide_rgesn_returns_template():
    result = mcp_module.audit_rapide_rgesn("https://example.com")
    assert isinstance(result, str) and len(result) > 50
    assert "Prioritaire" in result
    assert "https://example.com" in result


def test_plan_action_returns_template():
    result = mcp_module.plan_action("Site e-commerce B2B")
    assert isinstance(result, str) and len(result) > 50
    assert "Site e-commerce B2B" in result


def test_evaluer_score_returns_template():
    result = mcp_module.evaluer_score('{"1.1": "NC", "2.3": "NC"}')
    assert isinstance(result, str) and len(result) > 50
    assert "rgesn_taux_conformite" in result
