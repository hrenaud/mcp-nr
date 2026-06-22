"""
Tests fonctionnels pour le MCP RGESN.
Écrits en TDD avant l'implémentation des outils.
"""
import sys
import pytest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "files"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "core"))


# ============================================================================
# Tests : chargement des données
# ============================================================================

def test_charger_cache_retourne_78_criteres():
    from data import charger_cache
    cache = charger_cache()
    assert len(cache["criteres"]) == 78


def test_cache_contient_9_themes():
    from data import charger_cache
    cache = charger_cache()
    assert len(cache["themes"]) == 9


def test_cache_ponderations():
    from data import charger_cache
    cache = charger_cache()
    p = cache["ponderations"]
    assert p["Prioritaire"] == 1.5
    assert p["Recommandé"] == 1.25
    assert p["Modéré"] == 1.0


def test_cache_critere_structure():
    from data import charger_cache
    cache = charger_cache()
    c = cache["criteres"]["1.1"]
    assert c["id"] == "1.1"
    assert c["theme"] == 1
    assert c["priorite"] == "Prioritaire"
    assert c["difficulte"] == "Fort"
    assert isinstance(c["question"], str) and len(c["question"]) > 10
    assert isinstance(c["cible"], str)
    assert isinstance(c["metiers"], list)
    assert isinstance(c["objectif"], str)


def test_cache_30_prioritaires():
    from data import charger_cache
    cache = charger_cache()
    p = [c for c in cache["criteres"].values() if c["priorite"] == "Prioritaire"]
    assert len(p) == 30


def test_cache_28_recommandes():
    from data import charger_cache
    cache = charger_cache()
    r = [c for c in cache["criteres"].values() if c["priorite"] == "Recommandé"]
    assert len(r) == 28


def test_cache_20_moderes():
    from data import charger_cache
    cache = charger_cache()
    m = [c for c in cache["criteres"].values() if c["priorite"] == "Modéré"]
    assert len(m) == 20


def test_theme_1_a_10_criteres():
    from data import charger_cache
    cache = charger_cache()
    t1 = [c for c in cache["criteres"].values() if c["theme"] == 1]
    assert len(t1) == 10


def test_theme_4_a_15_criteres():
    from data import charger_cache
    cache = charger_cache()
    t4 = [c for c in cache["criteres"].values() if c["theme"] == 4]
    assert len(t4) == 15


# ============================================================================
# Tests : rgesn_lister_criteres
# ============================================================================

def test_lister_criteres_sans_filtre():
    import rgesn_mcp
    result = rgesn_mcp.rgesn_lister_criteres()
    assert result["total"] == 78
    assert len(result["criteres"]) == 78


def test_lister_criteres_par_theme():
    import rgesn_mcp
    result = rgesn_mcp.rgesn_lister_criteres(theme=1)
    assert result["total"] == 10
    assert all(c["theme"] == 1 for c in result["criteres"])


def test_lister_criteres_par_priorite():
    import rgesn_mcp
    result = rgesn_mcp.rgesn_lister_criteres(priorite="Prioritaire")
    assert result["total"] == 30


def test_lister_criteres_par_difficulte():
    import rgesn_mcp
    result = rgesn_mcp.rgesn_lister_criteres(difficulte="Fort")
    # Toutes les difficultés Fort
    assert result["total"] > 0
    assert all(c["difficulte"] == "Fort" for c in result["criteres"])


def test_lister_criteres_theme_et_priorite():
    import rgesn_mcp
    result = rgesn_mcp.rgesn_lister_criteres(theme=1, priorite="Prioritaire")
    assert result["total"] == 5
    assert all(c["theme"] == 1 and c["priorite"] == "Prioritaire" for c in result["criteres"])


def test_lister_criteres_theme_invalide():
    import rgesn_mcp
    from fastmcp.exceptions import ToolError
    with pytest.raises(ToolError):
        rgesn_mcp.rgesn_lister_criteres(theme=10)


def test_lister_criteres_priorite_invalide():
    import rgesn_mcp
    from fastmcp.exceptions import ToolError
    with pytest.raises(ToolError):
        rgesn_mcp.rgesn_lister_criteres(priorite="Urgent")


# ============================================================================
# Tests : rgesn_obtenir_critere
# ============================================================================

def test_obtenir_critere_11():
    import rgesn_mcp
    c = rgesn_mcp.rgesn_obtenir_critere("1.1")
    assert c["id"] == "1.1"
    assert c["theme"] == 1
    assert c["priorite"] == "Prioritaire"
    assert c["difficulte"] == "Fort"
    assert len(c["objectif"]) > 50


def test_obtenir_critere_inconnu():
    import rgesn_mcp
    from fastmcp.exceptions import ToolError
    with pytest.raises(ToolError):
        rgesn_mcp.rgesn_obtenir_critere("99.99")


def test_obtenir_critere_97():
    import rgesn_mcp
    c = rgesn_mcp.rgesn_obtenir_critere("9.7")
    assert c["theme"] == 9
    assert c["priorite"] == "Prioritaire"


# ============================================================================
# Tests : rgesn_chercher
# ============================================================================

def test_chercher_chiffrement():
    import rgesn_mcp
    result = rgesn_mcp.rgesn_chercher("chiffrement")
    assert result["total"] >= 1
    ids = [c["id"] for c in result["criteres"]]
    assert "1.7" in ids


def test_chercher_hebergement():
    import rgesn_mcp
    result = rgesn_mcp.rgesn_chercher("hébergeur")
    assert result["total"] >= 3


def test_chercher_avec_filtre_theme():
    import rgesn_mcp
    result = rgesn_mcp.rgesn_chercher("données", theme=7)
    assert all(c["theme"] == 7 for c in result["criteres"])


def test_chercher_vide_leve_erreur():
    import rgesn_mcp
    from fastmcp.exceptions import ToolError
    with pytest.raises(ToolError):
        rgesn_mcp.rgesn_chercher("")


# ============================================================================
# Tests : rgesn_statistiques
# ============================================================================

def test_statistiques_total():
    import rgesn_mcp
    stats = rgesn_mcp.rgesn_statistiques()
    assert stats["total_criteres"] == 78


def test_statistiques_par_priorite():
    import rgesn_mcp
    stats = rgesn_mcp.rgesn_statistiques()
    assert stats["par_priorite"]["Prioritaire"] == 30
    assert stats["par_priorite"]["Recommandé"] == 28
    assert stats["par_priorite"]["Modéré"] == 20


def test_statistiques_par_theme():
    import rgesn_mcp
    stats = rgesn_mcp.rgesn_statistiques()
    assert len(stats["par_theme"]) == 9
    assert stats["par_theme"]["1"]["nb_criteres"] == 10
    assert stats["par_theme"]["4"]["nb_criteres"] == 15


def test_statistiques_par_difficulte():
    import rgesn_mcp
    stats = rgesn_mcp.rgesn_statistiques()
    total = sum(stats["par_difficulte"].values())
    assert total == 78


# ============================================================================
# Tests : rgesn_taux_conformite
# ============================================================================

def test_taux_conformite_simple():
    import rgesn_mcp
    # 1.1 Prioritaire (poids 1.5) = Conforme
    result = rgesn_mcp.rgesn_taux_conformite({"1.1": "C"})
    assert result["score"] == 100.0
    assert result["nb_conformes"] == 1
    assert result["nb_non_conformes"] == 0
    assert result["nb_non_applicables"] == 0


def test_taux_conformite_avec_nc():
    import rgesn_mcp
    # 1.1 Prioritaire (1.5) = C, 1.2 Prioritaire (1.5) = NC
    result = rgesn_mcp.rgesn_taux_conformite({"1.1": "C", "1.2": "NC"})
    # Score = 1.5 / (1.5 + 1.5) * 100 = 50.0
    assert result["score"] == 50.0
    assert result["nb_conformes"] == 1
    assert result["nb_non_conformes"] == 1


def test_taux_conformite_na_exclut():
    import rgesn_mcp
    # 1.1 (P, 1.5) = C, 1.7 = NA
    result = rgesn_mcp.rgesn_taux_conformite({"1.1": "C", "1.7": "NA"})
    # Score = 1.5 / 1.5 * 100 = 100.0 (NA exclu)
    assert result["score"] == 100.0
    assert result["nb_non_applicables"] == 1


def test_taux_conformite_ponderations_differentes():
    import rgesn_mcp
    # 1.1 Prioritaire (1.5) = C, 1.3 Recommandé (1.25) = NC
    result = rgesn_mcp.rgesn_taux_conformite({"1.1": "C", "1.3": "NC"})
    # Score = 1.5 / (1.5 + 1.25) * 100 = 54.55
    expected = round(1.5 / (1.5 + 1.25) * 100, 2)
    assert result["score"] == expected


def test_taux_conformite_statut_invalide():
    import rgesn_mcp
    from fastmcp.exceptions import ToolError
    with pytest.raises(ToolError):
        rgesn_mcp.rgesn_taux_conformite({"1.1": "INCONNU"})


def test_taux_conformite_vide():
    import rgesn_mcp
    from fastmcp.exceptions import ToolError
    with pytest.raises(ToolError):
        rgesn_mcp.rgesn_taux_conformite({})


def test_taux_conformite_critere_inconnu():
    import rgesn_mcp
    from fastmcp.exceptions import ToolError
    with pytest.raises(ToolError):
        rgesn_mcp.rgesn_taux_conformite({"99.99": "C"})


# ============================================================================
# Tests : rgesn_checklist
# ============================================================================

def test_checklist_par_theme():
    import rgesn_mcp
    result = rgesn_mcp.rgesn_checklist(themes=[1])
    assert result["total"] == 10
    assert all(item["theme"] == 1 for item in result["criteres"])


def test_checklist_par_priorite():
    import rgesn_mcp
    result = rgesn_mcp.rgesn_checklist(priorites=["Prioritaire"])
    assert result["total"] == 30


def test_checklist_sans_filtre():
    import rgesn_mcp
    result = rgesn_mcp.rgesn_checklist()
    assert result["total"] == 78


def test_checklist_champs_presents():
    import rgesn_mcp
    result = rgesn_mcp.rgesn_checklist(themes=[1])
    c = result["criteres"][0]
    assert "id" in c
    assert "question" in c
    assert "priorite" in c
    assert "difficulte" in c
    assert "statut" in c
    assert c["statut"] == "NE"  # Non évalué par défaut


# ============================================================================
# Tests : instance MCP et outils enregistrés
# ============================================================================

def test_import_rgesn_mcp():
    import rgesn_mcp
    assert isinstance(rgesn_mcp.VERSION, str) and rgesn_mcp.VERSION


def test_mcp_instance_exists():
    import rgesn_mcp
    assert rgesn_mcp.mcp is not None


def test_tool_definitions_non_vides():
    import rgesn_mcp
    defs = rgesn_mcp._rgesn_tool_definitions()
    assert len(defs) >= 6
    noms = [d["name"] for d in defs]
    assert "rgesn_lister_criteres" in noms
    assert "rgesn_obtenir_critere" in noms
    assert "rgesn_chercher" in noms
    assert "rgesn_statistiques" in noms
    assert "rgesn_taux_conformite" in noms
    assert "rgesn_checklist" in noms
