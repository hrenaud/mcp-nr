"""Tests des prompts MCP RGAA."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "files"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "core"))

import rgaa_mcp as mcp_module


# ============================================================================
# Prompts existants
# ============================================================================

def test_audit_page_returns_template():
    result = mcp_module.audit_page("https://example.com")
    assert isinstance(result, str) and len(result) > 50
    assert "rgaa_analyser" in result
    assert "https://example.com" in result


def test_audit_page_with_themes():
    result = mcp_module.audit_page("https://example.com", themes="1,6")
    assert "1,6" in result


def test_rapport_audit_returns_template():
    result = mcp_module.rapport_audit('{"1.1": "NC"}')
    assert isinstance(result, str) and len(result) > 50
    assert "rgaa_taux_conformite" in result or "rgaa_obtenir_critere" in result


def test_expliquer_critere_returns_template():
    result = mcp_module.expliquer_critere("1.1")
    assert isinstance(result, str) and len(result) > 50
    assert "rgaa_obtenir_critere" in result
    assert "1.1" in result


def test_criteres_par_sujet_returns_template():
    result = mcp_module.criteres_par_sujet("images")
    assert isinstance(result, str) and len(result) > 50
    assert "rgaa_chercher" in result
    assert "images" in result


def test_criteres_par_sujet_with_niveau():
    result = mcp_module.criteres_par_sujet("formulaires", niveau="AA")
    assert "AA" in result


def test_checklist_audit_returns_template():
    result = mcp_module.checklist_audit("formulaires, navigation")
    assert isinstance(result, str) and len(result) > 50
    assert "rgaa_checklist" in result


def test_criteres_wcag_returns_template():
    result = mcp_module.criteres_wcag()
    assert isinstance(result, str) and len(result) > 50
    assert "rgaa_lister_criteres" in result


def test_criteres_wcag_with_niveau():
    result = mcp_module.criteres_wcag(niveau_wcag="A")
    assert "A" in result


def test_audit_par_type_returns_template():
    result = mcp_module.audit_par_type("https://example.com")
    assert isinstance(result, str) and len(result) > 50
    assert "rgaa_types_audit" in result or "rgaa_criteres_audit" in result


def test_audit_par_type_with_type():
    result = mcp_module.audit_par_type("https://example.com", type="rapide")
    assert "rapide" in result


def test_audit_rapide_returns_template():
    result = mcp_module.audit_rapide("https://example.com")
    assert isinstance(result, str) and len(result) > 50
    assert "https://example.com" in result


# ============================================================================
# Nouveaux prompts
# ============================================================================

def test_plan_correction_returns_template():
    result = mcp_module.plan_correction('{"1.1": "NC", "11.1": "NC"}')
    assert isinstance(result, str) and len(result) > 50
    assert "rgaa_obtenir_critere" in result


def test_formuler_exigences_returns_template():
    result = mcp_module.formuler_exigences("Application mobile bancaire")
    assert isinstance(result, str) and len(result) > 50
    assert "Application mobile bancaire" in result
