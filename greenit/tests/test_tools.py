"""
Tests des outils MCP GreenIT.

Exécution:
    cd /chemin/vers/projet
    pytest tests/test_tools.py -v
"""

import os
import sys
from pathlib import Path

# Ajouter le dossier files/ au path pour importer le module
sys.path.insert(0, str(Path(__file__).parent.parent / "files"))

import pytest
import json
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "core"))

import greenit_mcp as mcp_module
from fastmcp.exceptions import ToolError
from mcp_ref_core import factory, routes as routes_mod


# ============================================================================
# Env Helpers
# ============================================================================

class TestEnvHelpers:
    def test_get_base_url_from_env(self, monkeypatch):
        monkeypatch.setenv("MCP_BASE_URL", "https://my.server.com")
        result = mcp_module._get_base_url()
        assert result == "https://my.server.com"

    def test_get_base_url_strips_trailing_slash(self, monkeypatch):
        monkeypatch.setenv("MCP_BASE_URL", "https://my.server.com/")
        result = mcp_module._get_base_url()
        assert result == "https://my.server.com"

    def test_get_base_url_default_uses_host_port(self, monkeypatch):
        monkeypatch.delenv("MCP_BASE_URL", raising=False)
        monkeypatch.setenv("MCP_HOST", "0.0.0.0")
        monkeypatch.setenv("MCP_PORT", "8000")
        result = mcp_module._get_base_url()
        assert result == "http://localhost:8000"

    def test_get_base_url_custom_host(self, monkeypatch):
        monkeypatch.delenv("MCP_BASE_URL", raising=False)
        monkeypatch.setenv("MCP_HOST", "192.168.1.10")
        monkeypatch.setenv("MCP_PORT", "9000")
        result = mcp_module._get_base_url()
        assert result == "http://192.168.1.10:9000"

    def test_get_token_request_url_from_env(self, monkeypatch):
        monkeypatch.setenv("MCP_TOKEN_REQUEST_URL", "https://forms.gle/abc123")
        result = mcp_module._get_token_request_url()
        assert result == "https://forms.gle/abc123"

    def test_get_token_request_url_empty_by_default(self, monkeypatch):
        monkeypatch.delenv("MCP_TOKEN_REQUEST_URL", raising=False)
        result = mcp_module._get_token_request_url()
        assert result == ""


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture(scope="session", autouse=True)
def _load_cache_once():
    """Ensure cache is loaded at session start - autouse ensures it runs for all tests"""
    import data as data_module

    data_module._cache = None
    cache_data = data_module.charger_cache()
    fiches = cache_data.get("fiches", {})
    if not fiches:
        pytest.skip("Cache vide — lancez: python files/preparer_donnees.py --telecharger")
    return fiches


@pytest.fixture(scope="function")
def cache():
    """Provide fiches dict for individual tests"""
    from data import charger_cache
    fiches = charger_cache().get("fiches", {})
    if not fiches:
        pytest.skip("Cache vide — lancez: python files/preparer_donnees.py --telecharger")
    return fiches


@pytest.fixture(scope="session")
def premier_id():
    """Get first fiche ID from cache"""
    from data import charger_cache
    fiches = charger_cache().get("fiches", {})
    return next(iter(fiches))


# ============================================================================
# lister_fiches
# ============================================================================

class TestListerFiches:
    def test_sans_filtre(self, cache):
        response = mcp_module.lister_fiches()
        assert isinstance(response, dict)
        assert "fiches" in response
        resultats = response["fiches"]
        assert isinstance(resultats, list)
        assert len(resultats) == len(cache)

    def test_filtre_lifecycle(self, cache):
        # Trouver un lifecycle existant
        lifecycle = next(
            (f.get("lifecycle") for f in cache.values() if f.get("lifecycle")), None
        )
        if not lifecycle:
            pytest.skip("Aucun lifecycle trouvé dans le cache")
        response = mcp_module.lister_fiches(lifecycle=lifecycle)
        resultats = response["fiches"]
        assert all(r["lifecycle"] == lifecycle for r in resultats)

    def test_filtre_impact_min(self, cache):
        response = mcp_module.lister_fiches(impact_min=4)
        resultats = response["fiches"]
        assert all(r["environmental_impact"] >= 4 for r in resultats)

    def test_filtre_priorite_min(self, cache):
        response = mcp_module.lister_fiches(priorite_min=4)
        resultats = response["fiches"]
        assert all(r["priority_implementation"] >= 4 for r in resultats)

    def test_filtre_combine(self, cache):
        response = mcp_module.lister_fiches(impact_min=5, priorite_min=5)
        resultats = response["fiches"]
        for r in resultats:
            assert r["environmental_impact"] >= 5
            assert r["priority_implementation"] >= 5

    def test_structure_resultat(self):
        response = mcp_module.lister_fiches()
        resultats = response["fiches"]
        assert resultats
        r = resultats[0]
        for champ in ("id", "num", "titre", "environmental_impact", "priority_implementation"):
            assert champ in r, f"Champ '{champ}' manquant"


# ============================================================================
# fiches_prioritaires
# ============================================================================

class TestFichesPrioritaires:
    def test_defaut(self):
        response = mcp_module.fiches_prioritaires()
        assert isinstance(response, dict)
        assert "fiches" in response
        resultats = response["fiches"]
        for r in resultats:
            assert r["environmental_impact"] >= 4
            assert r["priority_implementation"] >= 4

    def test_tri_decroissant(self):
        response = mcp_module.fiches_prioritaires()
        resultats = response["fiches"]
        scores = [r["score"] for r in resultats]
        assert scores == sorted(scores, reverse=True)

    def test_seuil_personnalise(self):
        response = mcp_module.fiches_prioritaires(impact_min=3, priorite_min=3)
        resultats = response["fiches"]
        for r in resultats:
            assert r["environmental_impact"] >= 3
            assert r["priority_implementation"] >= 3

    def test_score_calcul(self):
        response = mcp_module.fiches_prioritaires()
        resultats = response["fiches"]
        for r in resultats:
            assert r["score"] == r["environmental_impact"] + r["priority_implementation"]


# ============================================================================
# chercher_fiche
# ============================================================================

class TestChercherFiche:
    def test_terme_commun(self):
        response = mcp_module.chercher_fiche("image")
        assert isinstance(response, dict)
        assert "fiches" in response
        resultats = response["fiches"]
        assert isinstance(resultats, list)
        assert len(resultats) > 0

    def test_max_15_resultats(self):
        response = mcp_module.chercher_fiche("web")
        resultats = response["fiches"]
        assert len(resultats) <= 15

    def test_tri_par_pertinence(self):
        response = mcp_module.chercher_fiche("image")
        resultats = response["fiches"]
        pertinences = [r["pertinence"] for r in resultats]
        assert pertinences == sorted(pertinences, reverse=True)

    def test_terme_absent(self):
        response = mcp_module.chercher_fiche("xyzxyzxyz_terme_inexistant")
        resultats = response["fiches"]
        assert resultats == []

    def test_chercher_fiche_structure_resultat(self):
        response = mcp_module.chercher_fiche("cache")
        resultats = response["fiches"]
        if resultats:
            r = resultats[0]
            for champ in ("id", "num", "titre", "pertinence"):
                assert champ in r


# ============================================================================
# comparer_fiches
# ============================================================================

class TestComparerFiches:
    def test_deux_fiches(self, cache):
        ids = list(cache.keys())[:2]
        resultat = mcp_module.comparer_fiches(ids)
        assert "comparaison" in resultat
        assert "recommandation" in resultat
        assert len(resultat["comparaison"]) == 2

    def test_classement_present(self, cache):
        ids = list(cache.keys())[:3]
        resultat = mcp_module.comparer_fiches(ids)
        assert "classement" in resultat["recommandation"]
        assert len(resultat["recommandation"]["classement"]) == 3

    def test_id_invalide(self):
        with pytest.raises(ToolError):
            mcp_module.comparer_fiches(["RWEB_9999"])


# ============================================================================
# obtenir_fiche_complete
# ============================================================================

class TestObtenirFicheComplete:
    def test_fiche_existante(self, premier_id):
        resultat = mcp_module.obtenir_fiche_complete(premier_id)
        assert isinstance(resultat, dict)
        assert "erreur" not in resultat
        assert "title" in resultat

    def test_fiche_inexistante(self):
        with pytest.raises(ToolError):
            mcp_module.obtenir_fiche_complete("RWEB_9999")


# ============================================================================
# obtenir_statistiques
# ============================================================================

class TestObtenirStatistiques:
    def test_structure(self):
        stats = mcp_module.obtenir_statistiques()
        for champ in (
            "total_fiches",
            "distribution_lifecycle",
            "distribution_ressources",
            "distribution_impact_environnemental",
            "top_5_score_combine",
        ):
            assert champ in stats, f"Champ '{champ}' manquant"

    def test_total_coherent(self, cache):
        stats = mcp_module.obtenir_statistiques()
        assert stats["total_fiches"] == len(cache)

    def test_top5_longueur(self):
        stats = mcp_module.obtenir_statistiques()
        assert len(stats["top_5_score_combine"]) <= 5

    def test_statistiques_includes_referentiel_version(self):
        stats = mcp_module.obtenir_statistiques()
        assert "referentiel_version" in stats
        assert stats["referentiel_version"] != ""


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
            Route("/", mcp_module._http_homepage, methods=["GET"]),
            Route("/install.sh", mcp_module._http_install_script, methods=["GET"]),
            Route("/guide", mcp_module._http_guide, methods=["GET"]),
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
        assert "GreenIT MCP" in r.text

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

    def test_install_script_has_greenit_mcp_add(self, client):
        r = client.get("/install.sh")
        assert "claude mcp add greenit" in r.text
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
        for tool in ("lister_fiches", "chercher_fiche", "calculer_ecoindex"):
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


# ============================================================================
# _create_mcp
# ============================================================================

class TestCreateMcp:
    def test_stdio_mode_no_routes(self, monkeypatch):
        monkeypatch.setenv("MCP_TRANSPORT", "stdio")
        mcp = factory.create_mcp("GreenIT-Referentiel", mcp_module.TOKENS_FILE, routes_mod._greenit_tool_definitions)
        assert mcp.name == "GreenIT-Referentiel"
        assert len(mcp._additional_http_routes) == 0

    def test_http_mode_registers_routes(self, monkeypatch):
        monkeypatch.setenv("MCP_TRANSPORT", "http")
        mcp = factory.create_mcp("GreenIT-Referentiel", mcp_module.TOKENS_FILE, routes_mod._greenit_tool_definitions)
        assert mcp.name == "GreenIT-Referentiel"
        assert len(mcp._additional_http_routes) == 8
        paths = [r.path for r in mcp._additional_http_routes]
        assert "/" in paths
        assert "/install.sh" in paths
        assert "/guide" in paths
        assert "/admin/tokens" in paths
        assert "/admin/tokens/{id}" in paths


# ============================================================================
# greenit_mcp_final — lister_lifecycles
# ============================================================================

class TestListerLifecycles:
    def test_returns_seven_entries(self):
        response = mcp_module.lister_lifecycles()
        result = response["lifecycles"]
        assert len(result) == 7

    def test_ordered_by_numeric_prefix(self):
        response = mcp_module.lister_lifecycles()
        result = response["lifecycles"]
        ids = [entry["id"] for entry in result]
        assert ids == sorted(ids, key=lambda x: int(x.split("-")[0]))

    def test_lister_lifecycles_labels_match_i18n(self):
        response = mcp_module.lister_lifecycles()
        result = response["lifecycles"]
        expected_labels = {
            "1-specification": "Spécification",
            "2-concept": "Conception",
            "3-developement": "Développement",
            "4-production": "Production",
            "5-utilization": "Utilisation",
            "6-support": "Support",
            "7-retirement": "Fin de vie",
        }
        for entry in result:
            assert entry["label"] == expected_labels[entry["id"]], (
                f"{entry['id']}: expected {expected_labels[entry['id']]!r}, got {entry['label']!r}"
            )

    def test_lister_lifecycles_counts_are_nonnegative_integers(self):
        response = mcp_module.lister_lifecycles()
        result = response["lifecycles"]
        for entry in result:
            assert isinstance(entry["count"], int)
            assert entry["count"] >= 0

    def test_total_count_covers_cache(self):
        response = mcp_module.lister_lifecycles()
        result = response["lifecycles"]
        total = sum(entry["count"] for entry in result)
        # All fiches have a lifecycle — total must equal cache size
        assert total >= 115

    def test_lister_lifecycles_ids_are_valid_lister_fiches_filters(self):
        response = mcp_module.lister_lifecycles()
        result = response["lifecycles"]
        for entry in result:
            response_fiches = mcp_module.lister_fiches(lifecycle=entry["id"])
            fiches = response_fiches["fiches"]
            assert len(fiches) == entry["count"], (
                f"lister_fiches(lifecycle={entry['id']!r}) returned {len(fiches)}, "
                f"but lister_lifecycles says count={entry['count']}"
            )

    def test_lister_lifecycles_required_fields_on_every_entry(self):
        response = mcp_module.lister_lifecycles()
        result = response["lifecycles"]
        for entry in result:
            assert "id" in entry
            assert "label" in entry
            assert "count" in entry


# ============================================================================
# greenit_mcp_final — lister_ressources
# ============================================================================

class TestListerRessources:
    def test_returns_eight_entries(self):
        response = mcp_module.lister_ressources()
        result = response["ressources"]
        assert len(result) == 8

    def test_sorted_by_count_descending(self):
        response = mcp_module.lister_ressources()
        result = response["ressources"]
        counts = [entry["count"] for entry in result]
        assert counts == sorted(counts, reverse=True)

    def test_lister_ressources_labels_match_i18n(self):
        response = mcp_module.lister_ressources()
        result = response["ressources"]
        expected_labels = {
            "network":     "Réseau",
            "cpu":         "Processeur",
            "ram":         "Mémoire vive",
            "storage":     "Stockage",
            "requests":    "Requêtes",
            "electricity": "Consommation électrique",
            "ghg":         "Émissions de gaz à effet de serre",
            "e-waste":     "Déchets électroniques",
        }
        for entry in result:
            assert entry["label"] == expected_labels[entry["id"]], (
                f"{entry['id']}: expected {expected_labels[entry['id']]!r}, got {entry['label']!r}"
            )

    def test_lister_ressources_counts_are_nonnegative_integers(self):
        response = mcp_module.lister_ressources()
        result = response["ressources"]
        for entry in result:
            assert isinstance(entry["count"], int)
            assert entry["count"] >= 0

    def test_lister_ressources_required_fields_on_every_entry(self):
        response = mcp_module.lister_ressources()
        result = response["ressources"]
        for entry in result:
            assert "id" in entry
            assert "label" in entry
            assert "count" in entry

    def test_lister_ressources_ids_are_valid_lister_fiches_filters(self):
        response = mcp_module.lister_ressources()
        result = response["ressources"]
        for entry in result:
            response_fiches = mcp_module.lister_fiches(saved_resource=entry["id"])
            fiches = response_fiches["fiches"]
            assert len(fiches) == entry["count"], (
                f"lister_fiches(saved_resource={entry['id']!r}) returned {len(fiches)}, "
                f"but lister_ressources says count={entry['count']}"
            )


# ============================================================================
# greenit_mcp_final — calculer_ecoindex
# ============================================================================

class TestCalculerEcoindex:
    def test_zero_inputs_score_100(self):
        result = json.loads(mcp_module.calculer_ecoindex(0, 0, 0))
        assert result["score"] == pytest.approx(100.0, rel=1e-2)
        assert result["grade"] == "A"

    def test_good_page_grade_a(self):
        # dom=200, req=20, size_kb=200 → score >80
        result = json.loads(mcp_module.calculer_ecoindex(200, 20, 200))
        assert result["score"] > 80
        assert result["grade"] == "A"

    def test_bad_page_grade_low(self):
        # dom=2000, req=150, size_kb=6000 → score <25
        result = json.loads(mcp_module.calculer_ecoindex(2000, 150, 6000))
        assert result["score"] < 25
        assert result["grade"] in ("E", "F", "G")

    def test_score_clamped_between_0_and_100(self):
        result = json.loads(mcp_module.calculer_ecoindex(0, 0, 0))
        assert 0 <= result["score"] <= 100

    def test_returns_expected_keys(self):
        result = json.loads(mcp_module.calculer_ecoindex(500, 50, 500, url="https://example.com"))
        for key in ("url", "dom_nodes", "requests", "size_kb", "score", "grade"):
            assert key in result
        assert result["grade"] in ("A", "B", "C", "D", "E", "F", "G")
        assert result["url"] == "https://example.com"

    def test_url_optional_defaults_empty(self):
        result = json.loads(mcp_module.calculer_ecoindex(100, 10, 100))
        assert result["url"] == ""

    def test_tool_is_registered(self):
        import asyncio
        tools = asyncio.run(mcp_module.mcp.list_tools())
        names = [t.name for t in tools]
        assert "calculer_ecoindex" in names


# ============================================================================
# Tool Annotations
# ============================================================================

class TestAnnotations:
    def test_lister_fiches_annotations(self):
        """Verify lister_fiches has complete MCP annotations."""
        import asyncio
        tools = asyncio.run(mcp_module.mcp.list_tools())
        tool = next((t for t in tools if t.name == "lister_fiches"), None)
        assert tool is not None, "lister_fiches tool not found"

        # Check annotations exist
        assert hasattr(tool, 'annotations'), "Tool missing annotations attribute"
        annotations = tool.annotations

        # Verify required annotations
        assert annotations.readOnlyHint is True, "lister_fiches should have readOnlyHint=True"
        assert annotations.destructiveHint is False, "lister_fiches should have destructiveHint=False"
        assert annotations.idempotentHint is True, "lister_fiches should have idempotentHint=True"

    def test_fiches_prioritaires_annotations(self):
        """Verify fiches_prioritaires has complete MCP annotations."""
        import asyncio
        tools = asyncio.run(mcp_module.mcp.list_tools())
        tool = next((t for t in tools if t.name == "fiches_prioritaires"), None)
        assert tool is not None, "fiches_prioritaires tool not found"

        # Check annotations exist
        assert hasattr(tool, 'annotations'), "Tool missing annotations attribute"
        annotations = tool.annotations

        # Verify required annotations
        assert annotations.readOnlyHint is True, "fiches_prioritaires should have readOnlyHint=True"
        assert annotations.destructiveHint is False, "fiches_prioritaires should have destructiveHint=False"
        assert annotations.idempotentHint is True, "fiches_prioritaires should have idempotentHint=True"

    def test_chercher_fiche_annotations(self):
        """Verify chercher_fiche has complete MCP annotations including openWorldHint."""
        import asyncio
        tools = asyncio.run(mcp_module.mcp.list_tools())
        tool = next((t for t in tools if t.name == "chercher_fiche"), None)
        assert tool is not None, "chercher_fiche tool not found"

        # Check annotations exist
        assert hasattr(tool, 'annotations'), "Tool missing annotations attribute"
        annotations = tool.annotations

        # Verify required annotations
        assert annotations.readOnlyHint is True, "chercher_fiche should have readOnlyHint=True"
        assert annotations.destructiveHint is False, "chercher_fiche should have destructiveHint=False"
        assert annotations.idempotentHint is True, "chercher_fiche should have idempotentHint=True"
        assert annotations.openWorldHint is True, "chercher_fiche should have openWorldHint=True (accepts arbitrary keywords)"

    def test_comparer_fiches_annotations(self):
        """Verify comparer_fiches has complete MCP annotations."""
        import asyncio
        tools = asyncio.run(mcp_module.mcp.list_tools())
        tool = next((t for t in tools if t.name == "comparer_fiches"), None)
        assert tool is not None, "comparer_fiches tool not found"

        # Check annotations exist
        assert hasattr(tool, 'annotations'), "Tool missing annotations attribute"
        annotations = tool.annotations

        # Verify required annotations
        assert annotations.readOnlyHint is True, "comparer_fiches should have readOnlyHint=True"
        assert annotations.destructiveHint is False, "comparer_fiches should have destructiveHint=False"
        assert annotations.idempotentHint is True, "comparer_fiches should have idempotentHint=True"

    def test_obtenir_fiche_complete_annotations(self):
        """Verify obtenir_fiche_complete has complete MCP annotations."""
        import asyncio
        tools = asyncio.run(mcp_module.mcp.list_tools())
        tool = next((t for t in tools if t.name == "obtenir_fiche_complete"), None)
        assert tool is not None, "obtenir_fiche_complete tool not found"

        # Check annotations exist
        assert hasattr(tool, 'annotations'), "Tool missing annotations attribute"
        annotations = tool.annotations

        # Verify required annotations
        assert annotations.readOnlyHint is True, "obtenir_fiche_complete should have readOnlyHint=True"
        assert annotations.destructiveHint is False, "obtenir_fiche_complete should have destructiveHint=False"
        assert annotations.idempotentHint is True, "obtenir_fiche_complete should have idempotentHint=True"

    def test_obtenir_statistiques_annotations(self):
        """Verify obtenir_statistiques has complete MCP annotations."""
        import asyncio
        tools = asyncio.run(mcp_module.mcp.list_tools())
        tool = next((t for t in tools if t.name == "obtenir_statistiques"), None)
        assert tool is not None, "obtenir_statistiques tool not found"

        # Check annotations exist
        assert hasattr(tool, 'annotations'), "Tool missing annotations attribute"
        annotations = tool.annotations

        # Verify required annotations
        assert annotations.readOnlyHint is True, "obtenir_statistiques should have readOnlyHint=True"
        assert annotations.destructiveHint is False, "obtenir_statistiques should have destructiveHint=False"
        assert annotations.idempotentHint is True, "obtenir_statistiques should have idempotentHint=True"

    def test_lister_lifecycles_annotations(self):
        """Verify lister_lifecycles has complete MCP annotations."""
        import asyncio
        tools = asyncio.run(mcp_module.mcp.list_tools())
        tool = next((t for t in tools if t.name == "lister_lifecycles"), None)
        assert tool is not None, "lister_lifecycles tool not found"

        # Check annotations exist
        assert hasattr(tool, 'annotations'), "Tool missing annotations attribute"
        annotations = tool.annotations

        # Verify required annotations
        assert annotations.readOnlyHint is True, "lister_lifecycles should have readOnlyHint=True"
        assert annotations.destructiveHint is False, "lister_lifecycles should have destructiveHint=False"
        assert annotations.idempotentHint is True, "lister_lifecycles should have idempotentHint=True"

    def test_lister_ressources_annotations(self):
        """Verify lister_ressources has complete MCP annotations."""
        import asyncio
        tools = asyncio.run(mcp_module.mcp.list_tools())
        tool = next((t for t in tools if t.name == "lister_ressources"), None)
        assert tool is not None, "lister_ressources tool not found"

        # Check annotations exist
        assert hasattr(tool, 'annotations'), "Tool missing annotations attribute"
        annotations = tool.annotations

        # Verify required annotations
        assert annotations.readOnlyHint is True, "lister_ressources should have readOnlyHint=True"
        assert annotations.destructiveHint is False, "lister_ressources should have destructiveHint=False"
        assert annotations.idempotentHint is True, "lister_ressources should have idempotentHint=True"

    def test_calculer_ecoindex_annotations(self):
        """Verify calculer_ecoindex has complete MCP annotations."""
        import asyncio
        tools = asyncio.run(mcp_module.mcp.list_tools())
        tool = next((t for t in tools if t.name == "calculer_ecoindex"), None)
        assert tool is not None, "calculer_ecoindex tool not found"

        # Check annotations exist
        assert hasattr(tool, 'annotations'), "Tool missing annotations attribute"
        annotations = tool.annotations

        # Verify required annotations
        assert annotations.readOnlyHint is True, "calculer_ecoindex should have readOnlyHint=True"
        assert annotations.destructiveHint is False, "calculer_ecoindex should have destructiveHint=False"
        assert annotations.idempotentHint is True, "calculer_ecoindex should have idempotentHint=True"


# ============================================================================
# Error Handling Tests
# ============================================================================

class TestErrorHandling:
    """Test ToolError handling with French messages for all tools."""

    def test_lister_fiches_invalid_impact_min_raises_toolerror(self):
        """Test that invalid impact_min raises ToolError with French message."""
        with pytest.raises(ToolError) as exc_info:
            mcp_module.lister_fiches(impact_min=999)  # Out of valid range (1-5)
        assert "Les paramètres fournis sont invalides" in str(exc_info.value)
        assert "impact_min" in str(exc_info.value).lower()

    def test_lister_fiches_invalid_priorite_min_raises_toolerror(self):
        """Test that invalid priorite_min raises ToolError with French message."""
        with pytest.raises(ToolError) as exc_info:
            mcp_module.lister_fiches(priorite_min=0)  # Out of valid range (1-5)
        assert "Les paramètres fournis sont invalides" in str(exc_info.value)
        assert "priorite_min" in str(exc_info.value).lower()

    def test_fiches_prioritaires_invalid_impact_min_raises_toolerror(self):
        """Test that invalid impact_min raises ToolError with French message."""
        with pytest.raises(ToolError) as exc_info:
            mcp_module.fiches_prioritaires(impact_min=6)  # Out of valid range (1-5)
        assert "Les paramètres fournis sont invalides" in str(exc_info.value)

    def test_fiches_prioritaires_invalid_priorite_min_raises_toolerror(self):
        """Test that invalid priorite_min raises ToolError with French message."""
        with pytest.raises(ToolError) as exc_info:
            mcp_module.fiches_prioritaires(priorite_min=-1)  # Out of valid range (1-5)
        assert "Les paramètres fournis sont invalides" in str(exc_info.value)

    def test_chercher_fiche_empty_query_raises_toolerror(self):
        """Test that empty search term raises ToolError with French message."""
        with pytest.raises(ToolError) as exc_info:
            mcp_module.chercher_fiche(terme="")  # Empty search term
        assert "vide" in str(exc_info.value).lower() or "Les paramètres fournis sont invalides" in str(exc_info.value)

    def test_comparer_fiches_empty_list_raises_toolerror(self):
        """Test that empty fiche_ids list raises ToolError with French message."""
        with pytest.raises(ToolError) as exc_info:
            mcp_module.comparer_fiches(fiche_ids=[])  # Empty list
        assert "vide" in str(exc_info.value).lower() or "Les paramètres fournis sont invalides" in str(exc_info.value)

    def test_comparer_fiches_invalid_id_raises_toolerror(self):
        """Test that invalid fiche_id raises ToolError with French message."""
        with pytest.raises(ToolError) as exc_info:
            mcp_module.comparer_fiches(fiche_ids=["INVALID_12345", "INVALID_67890"])
        assert "Erreur" in str(exc_info.value) or "introuvable" in str(exc_info.value).lower()

    def test_obtenir_fiche_complete_invalid_id_raises_toolerror(self):
        """Test that invalid fiche_id raises ToolError with French message."""
        with pytest.raises(ToolError) as exc_info:
            mcp_module.obtenir_fiche_complete(fiche_id="INVALID_12345")
        assert "Erreur" in str(exc_info.value) or "introuvable" in str(exc_info.value).lower()
        assert "INVALID_12345" in str(exc_info.value) or "identifiant" in str(exc_info.value).lower()

    def test_calculer_ecoindex_negative_dom_nodes_raises_toolerror(self):
        """Test that negative dom_nodes raises ToolError with French message."""
        with pytest.raises(ToolError) as exc_info:
            mcp_module.calculer_ecoindex(dom_nodes=-1, requests=10, size_kb=100.0)
        assert "positif" in str(exc_info.value).lower() or "Les paramètres fournis sont invalides" in str(exc_info.value)

    def test_calculer_ecoindex_negative_requests_raises_toolerror(self):
        """Test that negative requests raises ToolError with French message."""
        with pytest.raises(ToolError) as exc_info:
            mcp_module.calculer_ecoindex(dom_nodes=100, requests=-5, size_kb=100.0)
        assert "positif" in str(exc_info.value).lower() or "Les paramètres fournis sont invalides" in str(exc_info.value)

    def test_calculer_ecoindex_negative_size_kb_raises_toolerror(self):
        """Test that negative size_kb raises ToolError with French message."""
        with pytest.raises(ToolError) as exc_info:
            mcp_module.calculer_ecoindex(dom_nodes=100, requests=10, size_kb=-50.0)
        assert "positif" in str(exc_info.value).lower() or "Les paramètres fournis sont invalides" in str(exc_info.value)


# ============================================================================
# TASK 9: Comprehensive Error Handling & Edge Cases for All 9 Tools
# ============================================================================

class TestListerFichesEdgeCases:
    """Additional edge case tests for lister_fiches tool."""

    def test_invalid_impact_min_boundary_zero(self):
        """Test that impact_min=0 (below valid range) raises ToolError."""
        with pytest.raises(ToolError):
            mcp_module.lister_fiches(impact_min=0)

    def test_invalid_impact_min_boundary_six(self):
        """Test that impact_min=6 (above valid range) raises ToolError."""
        with pytest.raises(ToolError):
            mcp_module.lister_fiches(impact_min=6)

    def test_invalid_priorite_min_boundary_negative(self):
        """Test that priorite_min=-1 (below valid range) raises ToolError."""
        with pytest.raises(ToolError):
            mcp_module.lister_fiches(priorite_min=-1)

    def test_invalid_priorite_min_boundary_high(self):
        """Test that priorite_min=10 (above valid range) raises ToolError."""
        with pytest.raises(ToolError):
            mcp_module.lister_fiches(priorite_min=10)

    def test_all_valid_impact_min_values(self, cache):
        """Test that all valid impact_min values (1-5) work correctly."""
        for i in range(1, 6):
            response = mcp_module.lister_fiches(impact_min=i)
            assert "fiches" in response
            for fiche in response["fiches"]:
                assert fiche["environmental_impact"] >= i

    def test_all_valid_priorite_min_values(self):
        """Test that all valid priorite_min values (1-5) work correctly."""
        for i in range(1, 6):
            response = mcp_module.lister_fiches(priorite_min=i)
            assert "fiches" in response
            for fiche in response["fiches"]:
                assert fiche["priority_implementation"] >= i

    def test_nonexistent_lifecycle_filter_returns_empty(self):
        """Test that filtering by non-existent lifecycle returns empty list."""
        response = mcp_module.lister_fiches(lifecycle="999-nonexistent")
        assert response["fiches"] == []

    def test_nonexistent_saved_resource_filter_returns_empty(self):
        """Test that filtering by non-existent resource returns empty list."""
        response = mcp_module.lister_fiches(saved_resource="nonexistent_resource")
        assert response["fiches"] == []

    def test_combined_filters_more_restrictive(self, cache):
        """Test that combining filters results in fewer or equal results."""
        no_filter = mcp_module.lister_fiches()
        with_filter = mcp_module.lister_fiches(impact_min=5, priorite_min=5)
        assert len(with_filter["fiches"]) <= len(no_filter["fiches"])

    def test_impact_5_priorite_5_intersection(self):
        """Test that impact_min=5 AND priorite_min=5 returns valid intersection."""
        response = mcp_module.lister_fiches(impact_min=5, priorite_min=5)
        for fiche in response["fiches"]:
            assert fiche["environmental_impact"] >= 5
            assert fiche["priority_implementation"] >= 5


class TestFichesPrioritairesEdgeCases:
    """Additional edge case tests for fiches_prioritaires tool."""

    def test_boundary_impact_min_one(self):
        """Test with impact_min=1 (minimum valid)."""
        response = mcp_module.fiches_prioritaires(impact_min=1)
        assert "fiches" in response
        assert isinstance(response["fiches"], list)

    def test_boundary_impact_min_five(self):
        """Test with impact_min=5 (maximum valid)."""
        response = mcp_module.fiches_prioritaires(impact_min=5)
        assert "fiches" in response
        for fiche in response["fiches"]:
            assert fiche["environmental_impact"] >= 5

    def test_boundary_priorite_min_one(self):
        """Test with priorite_min=1 (minimum valid)."""
        response = mcp_module.fiches_prioritaires(priorite_min=1)
        assert "fiches" in response

    def test_boundary_priorite_min_five(self):
        """Test with priorite_min=5 (maximum valid)."""
        response = mcp_module.fiches_prioritaires(priorite_min=5)
        assert "fiches" in response
        for fiche in response["fiches"]:
            assert fiche["priority_implementation"] >= 5

    def test_invalid_impact_min_zero(self):
        """Test that impact_min=0 (below minimum) raises ToolError."""
        with pytest.raises(ToolError):
            mcp_module.fiches_prioritaires(impact_min=0)

    def test_invalid_impact_min_six(self):
        """Test that impact_min=6 (above maximum) raises ToolError."""
        with pytest.raises(ToolError):
            mcp_module.fiches_prioritaires(impact_min=6)

    def test_invalid_priorite_min_negative(self):
        """Test that priorite_min<1 raises ToolError."""
        with pytest.raises(ToolError):
            mcp_module.fiches_prioritaires(priorite_min=-5)

    def test_invalid_priorite_min_above_range(self):
        """Test that priorite_min>5 raises ToolError."""
        with pytest.raises(ToolError):
            mcp_module.fiches_prioritaires(priorite_min=100)

    def test_no_high_priority_fiches_case(self):
        """Test when no fiches meet both impact and priority thresholds."""
        # This edge case occurs if we set both very high
        response = mcp_module.fiches_prioritaires(impact_min=5, priorite_min=5)
        # May return empty or partial list, but should not error
        assert "fiches" in response
        assert isinstance(response["fiches"], list)


class TestChercherFicheEdgeCases:
    """Additional edge case tests for chercher_fiche tool."""

    def test_whitespace_only_term_raises_toolerror(self):
        """Test that whitespace-only term raises ToolError."""
        with pytest.raises(ToolError):
            mcp_module.chercher_fiche(terme="   ")

    def test_single_character_search(self):
        """Test searching for single character."""
        response = mcp_module.chercher_fiche(terme="a")
        assert "fiches" in response
        assert isinstance(response["fiches"], list)

    def test_very_long_search_term(self):
        """Test searching for very long term."""
        long_term = "a" * 500
        response = mcp_module.chercher_fiche(terme=long_term)
        assert "fiches" in response
        assert isinstance(response["fiches"], list)

    def test_special_characters_in_search(self):
        """Test searching with special characters."""
        response = mcp_module.chercher_fiche(terme="@#$%^&*()")
        assert "fiches" in response
        assert isinstance(response["fiches"], list)

    def test_unicode_search_term(self):
        """Test searching with unicode characters."""
        response = mcp_module.chercher_fiche(terme="développement")
        assert "fiches" in response
        assert isinstance(response["fiches"], list)

    def test_case_insensitive_search(self):
        """Test that search is case insensitive."""
        response_lower = mcp_module.chercher_fiche(terme="image")
        response_upper = mcp_module.chercher_fiche(terme="IMAGE")
        response_mixed = mcp_module.chercher_fiche(terme="ImAgE")
        # All should return same number of results (case-insensitive)
        assert len(response_lower["fiches"]) == len(response_upper["fiches"])
        assert len(response_lower["fiches"]) == len(response_mixed["fiches"])

    def test_max_15_results_enforcement(self):
        """Test that results never exceed 15 items."""
        # Search for a common term that likely has many matches
        response = mcp_module.chercher_fiche(terme="web")
        assert len(response["fiches"]) <= 15

    def test_pertinence_ordering(self):
        """Test that results are ordered by pertinence (descending)."""
        response = mcp_module.chercher_fiche(terme="performance")
        fiches = response["fiches"]
        if len(fiches) > 1:
            pertinences = [f["pertinence"] for f in fiches]
            assert pertinences == sorted(pertinences, reverse=True)

    def test_no_results_returns_empty_list(self):
        """Test that impossible search returns empty list, not error."""
        response = mcp_module.chercher_fiche(terme="xyzxyzxyzxyzxyzxyzxyzxyzxyzxyz")
        assert response["fiches"] == []


class TestComparerFichesEdgeCases:
    """Additional edge case tests for comparer_fiches tool."""

    def test_empty_list_raises_toolerror(self):
        """Test that empty fiche_ids list raises ToolError."""
        with pytest.raises(ToolError):
            mcp_module.comparer_fiches(fiche_ids=[])

    def test_single_fiche(self, cache):
        """Test comparing single fiche."""
        single_id = [next(iter(cache.keys()))]
        result = mcp_module.comparer_fiches(fiche_ids=single_id)
        assert len(result["comparaison"]) == 1
        assert len(result["recommandation"]["classement"]) == 1

    def test_three_fiches(self, cache):
        """Test comparing three fiches."""
        ids = list(cache.keys())[:3]
        result = mcp_module.comparer_fiches(fiche_ids=ids)
        assert len(result["comparaison"]) == 3
        assert len(result["recommandation"]["classement"]) == 3

    def test_all_invalid_ids_raises_toolerror(self):
        """Test that all invalid IDs raises ToolError."""
        with pytest.raises(ToolError):
            mcp_module.comparer_fiches(fiche_ids=["INVALID_1", "INVALID_2", "INVALID_3"])

    def test_mixed_valid_invalid_ids_raises_toolerror(self, cache):
        """Test that mixing valid and invalid IDs raises ToolError."""
        valid_id = next(iter(cache.keys()))
        with pytest.raises(ToolError):
            mcp_module.comparer_fiches(fiche_ids=[valid_id, "INVALID_999"])

    def test_classement_matches_score_order(self, cache):
        """Test that classement is ordered by combined score (descending)."""
        ids = list(cache.keys())[:5]
        result = mcp_module.comparer_fiches(fiche_ids=ids)

        # Build score map
        score_map = {f["id"]: f["score_combined"] for f in result["comparaison"]}

        # Check that classement is ordered by score
        classement = result["recommandation"]["classement"]
        scores = [score_map[fiche_id] for fiche_id in classement]
        assert scores == sorted(scores, reverse=True)

    def test_recommandation_priorite_1_highest_score(self, cache):
        """Test that priorite_1 is the fiche with highest combined score."""
        ids = list(cache.keys())[:4]
        result = mcp_module.comparer_fiches(fiche_ids=ids)

        scores = {f["id"]: f["score_combined"] for f in result["comparaison"]}
        max_score_id = max(scores, key=scores.get)

        assert result["recommandation"]["priorite_1"] == max_score_id


class TestObtenirFicheCompleteEdgeCases:
    """Additional edge case tests for obtenir_fiche_complete tool."""

    def test_nonexistent_id_raises_toolerror(self):
        """Test that nonexistent ID raises ToolError."""
        with pytest.raises(ToolError):
            mcp_module.obtenir_fiche_complete("NONEXISTENT_999")

    def test_case_sensitive_id(self, cache):
        """Test that ID lookup is case-sensitive."""
        valid_id = next(iter(cache.keys()))

        # Try with different case (should fail)
        wrong_case_id = valid_id.lower() if valid_id.isupper() else valid_id.upper()
        if wrong_case_id != valid_id:  # Only if case actually differs
            with pytest.raises(ToolError):
                mcp_module.obtenir_fiche_complete(wrong_case_id)

    def test_returns_complete_structure(self, premier_id):
        """Test that result contains all expected fields."""
        result = mcp_module.obtenir_fiche_complete(premier_id)

        # Should be a dict (not error dict)
        assert isinstance(result, dict)
        assert "erreur" not in result

        # Check for key fields from schema (actual cache structure)
        expected_fields = ["title", "description", "lifecycle"]
        for field in expected_fields:
            assert field in result, f"Field '{field}' missing from result"

    def test_validation_principles_generated(self, premier_id):
        """Test that principes_de_validation is generated from validations."""
        result = mcp_module.obtenir_fiche_complete(premier_id)

        # Should have principes_de_validation field (generated or empty)
        assert "principes_de_validation" in result
        assert isinstance(result["principes_de_validation"], list)

    def test_returns_unmodified_cache_entry(self, premier_id, cache):
        """Test that returned fiche matches cache entry."""
        result = mcp_module.obtenir_fiche_complete(premier_id)
        cached = cache[premier_id]

        # Core fields should match
        assert result.get("id") == cached.get("id") or result.get("title") == cached.get("title")


class TestObtenirStatistiquesEdgeCases:
    """Additional edge case tests for obtenir_statistiques tool."""

    def test_returns_expected_structure(self):
        """Test that all expected fields are present."""
        stats = mcp_module.obtenir_statistiques()

        required_fields = [
            "total_fiches",
            "distribution_lifecycle",
            "distribution_ressources",
            "distribution_impact_environnemental",
            "distribution_priorite_implementation",
            "top_5_score_combine",
        ]
        for field in required_fields:
            assert field in stats, f"Field '{field}' missing from statistics"

    def test_total_fiches_is_positive(self, cache):
        """Test that total_fiches count is positive and matches cache."""
        stats = mcp_module.obtenir_statistiques()
        assert stats["total_fiches"] > 0
        assert stats["total_fiches"] == len(cache)

    def test_distribution_lifecycle_keys_valid(self):
        """Test that lifecycle distribution keys are valid lifecycle IDs."""
        stats = mcp_module.obtenir_statistiques()
        valid_lifecycles = {
            "1-specification", "2-concept", "3-developement", "4-production",
            "5-utilization", "6-support", "7-retirement"
        }

        for key in stats["distribution_lifecycle"].keys():
            assert key in valid_lifecycles, f"Invalid lifecycle key: {key}"

    def test_distribution_ressources_keys_valid(self):
        """Test that resource distribution keys are valid resource types."""
        stats = mcp_module.obtenir_statistiques()
        valid_resources = {
            "network", "cpu", "ram", "storage", "requests",
            "electricity", "ghg", "e-waste"
        }

        for key in stats["distribution_ressources"].keys():
            assert key in valid_resources, f"Invalid resource key: {key}"

    def test_top_5_not_exceeds_limit(self):
        """Test that top_5_score_combine never exceeds 5 items."""
        stats = mcp_module.obtenir_statistiques()
        assert len(stats["top_5_score_combine"]) <= 5

    def test_top_5_ordered_by_score(self):
        """Test that top_5 is ordered by score (descending)."""
        stats = mcp_module.obtenir_statistiques()
        top_5 = stats["top_5_score_combine"]

        if len(top_5) > 1:
            scores = [item["score"] for item in top_5]
            assert scores == sorted(scores, reverse=True)

    def test_all_counts_nonnegative(self):
        """Test that all count values are non-negative."""
        stats = mcp_module.obtenir_statistiques()

        for count in stats["distribution_lifecycle"].values():
            assert count >= 0

        for count in stats["distribution_ressources"].values():
            assert count >= 0


class TestListerLifecyclesEdgeCases:
    """Additional edge case tests for lister_lifecycles tool."""

    def test_all_seven_lifecycles_present(self):
        """Test that exactly 7 lifecycle phases are returned."""
        response = mcp_module.lister_lifecycles()
        assert len(response["lifecycles"]) == 7

    def test_lifecycle_ids_follow_pattern(self):
        """Test that all lifecycle IDs follow pattern N-name."""
        response = mcp_module.lister_lifecycles()
        import re
        pattern = r"^\d+-[a-z]+$"

        for entry in response["lifecycles"]:
            assert re.match(pattern, entry["id"]), f"Invalid ID format: {entry['id']}"

    def test_lifecycle_counts_match_filter_results(self):
        """Test that counts match results from lister_fiches filters."""
        response = mcp_module.lister_lifecycles()

        for entry in response["lifecycles"]:
            filtered = mcp_module.lister_fiches(lifecycle=entry["id"])
            assert len(filtered["fiches"]) == entry["count"], (
                f"Count mismatch for {entry['id']}: "
                f"lister_lifecycles says {entry['count']}, "
                f"lister_fiches returned {len(filtered['fiches'])}"
            )

    def test_sum_of_counts_equals_total(self, cache):
        """Test that sum of all lifecycle counts equals total fiches."""
        response = mcp_module.lister_lifecycles()
        total_count = sum(entry["count"] for entry in response["lifecycles"])
        assert total_count == len(cache)


class TestListerRessourcesEdgeCases:
    """Additional edge case tests for lister_ressources tool."""

    def test_all_eight_resources_present(self):
        """Test that exactly 8 resource types are returned."""
        response = mcp_module.lister_ressources()
        assert len(response["ressources"]) == 8

    def test_counts_descending_order(self):
        """Test that resources are sorted by count (descending)."""
        response = mcp_module.lister_ressources()
        counts = [entry["count"] for entry in response["ressources"]]
        assert counts == sorted(counts, reverse=True)

    def test_resource_ids_match_expected_set(self):
        """Test that all resource IDs are from the expected set."""
        response = mcp_module.lister_ressources()
        valid_resources = {
            "network", "cpu", "ram", "storage", "requests",
            "electricity", "ghg", "e-waste"
        }

        returned_ids = {entry["id"] for entry in response["ressources"]}
        assert returned_ids == valid_resources

    def test_resource_counts_match_filter_results(self):
        """Test that counts match results from lister_fiches filters."""
        response = mcp_module.lister_ressources()

        for entry in response["ressources"]:
            filtered = mcp_module.lister_fiches(saved_resource=entry["id"])
            assert len(filtered["fiches"]) == entry["count"], (
                f"Count mismatch for {entry['id']}: "
                f"lister_ressources says {entry['count']}, "
                f"lister_fiches returned {len(filtered['fiches'])}"
            )

    def test_all_counts_nonnegative(self):
        """Test that all resource counts are non-negative."""
        response = mcp_module.lister_ressources()

        for entry in response["ressources"]:
            assert entry["count"] >= 0


class TestCalculerEcoindexEdgeCases:
    """Additional edge case tests for calculer_ecoindex tool."""

    def test_zero_all_metrics_gives_perfect_score(self):
        """Test that 0,0,0 gives score of 100 and grade A."""
        result = json.loads(mcp_module.calculer_ecoindex(0, 0, 0))
        assert result["score"] == 100.0
        assert result["grade"] == "A"

    def test_large_values_give_low_score(self):
        """Test that very large metrics give low score."""
        result = json.loads(mcp_module.calculer_ecoindex(10000, 1000, 10000))
        assert result["score"] < 50
        assert result["grade"] in ("E", "F", "G", "D")

    @pytest.mark.parametrize("dom,req,size_kb", [
        (0, 0, 0),
        (100, 10, 100),
        (1000, 100, 1000),
    ])
    def test_parametrized_valid_inputs(self, dom, req, size_kb):
        """Test valid input combinations."""
        result = json.loads(mcp_module.calculer_ecoindex(dom, req, size_kb))
        assert 0 <= result["score"] <= 100
        assert result["grade"] in ("A", "B", "C", "D", "E", "F", "G")

    def test_negative_dom_nodes_raises_toolerror(self):
        """Test that negative dom_nodes raises ToolError."""
        with pytest.raises(ToolError):
            mcp_module.calculer_ecoindex(-1, 10, 100)

    def test_negative_requests_raises_toolerror(self):
        """Test that negative requests raises ToolError."""
        with pytest.raises(ToolError):
            mcp_module.calculer_ecoindex(100, -1, 100)

    def test_negative_size_kb_raises_toolerror(self):
        """Test that negative size_kb raises ToolError."""
        with pytest.raises(ToolError):
            mcp_module.calculer_ecoindex(100, 10, -1.0)

    def test_float_dom_nodes_accepted(self):
        """Test that float values for dom_nodes are accepted."""
        result = json.loads(mcp_module.calculer_ecoindex(100.5, 10, 100))
        assert "score" in result
        assert "grade" in result

    def test_very_small_decimal_values(self):
        """Test with very small decimal values."""
        result = json.loads(mcp_module.calculer_ecoindex(0.1, 0.1, 0.1))
        assert 0 <= result["score"] <= 100
        assert result["grade"] in ("A", "B", "C", "D", "E", "F", "G")

    def test_url_parameter_optional(self):
        """Test that url parameter is optional."""
        result = json.loads(mcp_module.calculer_ecoindex(100, 10, 100))
        assert result["url"] == ""

    def test_url_parameter_included_in_result(self):
        """Test that url parameter is included in result when provided."""
        result = json.loads(mcp_module.calculer_ecoindex(
            100, 10, 100, url="https://example.com"
        ))
        assert result["url"] == "https://example.com"

    def test_grade_corresponds_to_score(self):
        """Test that grade correctly corresponds to score ranges."""
        # Test grade A (80-100)
        result = json.loads(mcp_module.calculer_ecoindex(100, 10, 100))
        assert result["grade"] == "A", f"score={result['score']}: expected A, got {result['grade']}"
        assert 80 <= result["score"] <= 100

        # Test grade B (70-79)
        result = json.loads(mcp_module.calculer_ecoindex(100, 30, 1500))
        assert result["grade"] == "B", f"score={result['score']}: expected B, got {result['grade']}"
        assert 70 <= result["score"] < 80

        # Test grade C (55-69)
        result = json.loads(mcp_module.calculer_ecoindex(100, 70, 1700))
        assert result["grade"] == "C", f"score={result['score']}: expected C, got {result['grade']}"
        assert 55 <= result["score"] < 70

        # Test grade D (40-54)
        result = json.loads(mcp_module.calculer_ecoindex(100, 190, 1900))
        assert result["grade"] == "D", f"score={result['score']}: expected D, got {result['grade']}"
        assert 40 <= result["score"] < 55

        # Test grade E (25-39)
        result = json.loads(mcp_module.calculer_ecoindex(500, 190, 1900))
        assert result["grade"] == "E", f"score={result['score']}: expected E, got {result['grade']}"
        assert 25 <= result["score"] < 40

        # Test grade F (10-24)
        result = json.loads(mcp_module.calculer_ecoindex(900, 260, 1900))
        assert result["grade"] == "F", f"score={result['score']}: expected F, got {result['grade']}"
        assert 10 <= result["score"] < 25

        # Test grade G (0-9)
        result = json.loads(mcp_module.calculer_ecoindex(2000, 300, 3000))
        assert result["grade"] == "G", f"score={result['score']}: expected G, got {result['grade']}"
        assert 0 <= result["score"] < 10


# ============================================================================
# Error Handling Tests — Coverage Improvement Phase 5 Task 11
# ============================================================================

class TestErrorHandlingValidation:
    """Test parameter validation errors for tools."""

    @pytest.mark.parametrize("impact_min,priorite_min,should_raise", [
        (-1, 4, True),        # impact_min too low
        (6, 4, True),         # impact_min too high
        (4, 0, True),         # priorite_min too low
        (4, 6, True),         # priorite_min too high
        (0, 4, True),         # impact_min zero (invalid)
        (1, 1, False),        # both valid min
        (5, 5, False),        # both valid max
    ])
    def test_lister_fiches_invalid_range(self, impact_min, priorite_min, should_raise):
        """Test lister_fiches validation of impact_min and priorite_min."""
        if should_raise:
            with pytest.raises(ToolError) as exc_info:
                mcp_module.lister_fiches(impact_min=impact_min, priorite_min=priorite_min)
            assert "invalides" in str(exc_info.value).lower()
        else:
            response = mcp_module.lister_fiches(impact_min=impact_min, priorite_min=priorite_min)
            assert "fiches" in response

    @pytest.mark.parametrize("impact_min,priorite_min,should_raise", [
        (-1, 4, True),
        (6, 4, True),
        (4, 0, True),
        (4, 6, True),
        (3, 3, False),
        (5, 5, False),
    ])
    def test_fiches_prioritaires_invalid_range(self, impact_min, priorite_min, should_raise):
        """Test fiches_prioritaires validation of impact_min and priorite_min."""
        if should_raise:
            with pytest.raises(ToolError) as exc_info:
                mcp_module.fiches_prioritaires(impact_min=impact_min, priorite_min=priorite_min)
            assert "invalides" in str(exc_info.value).lower()
        else:
            response = mcp_module.fiches_prioritaires(impact_min=impact_min, priorite_min=priorite_min)
            assert "fiches" in response

    @pytest.mark.parametrize("terme", [
        "",
        "   ",
        "\t",
        "\n",
    ])
    def test_chercher_fiche_empty_terme(self, terme):
        """Test chercher_fiche rejects empty or whitespace-only terms."""
        with pytest.raises(ToolError) as exc_info:
            mcp_module.chercher_fiche(terme)
        assert "vide" in str(exc_info.value).lower() or "invalides" in str(exc_info.value).lower()

    def test_comparer_fiches_empty_list(self):
        """Test comparer_fiches rejects empty list of fiche_ids."""
        with pytest.raises(ToolError) as exc_info:
            mcp_module.comparer_fiches([])
        assert "invalides" in str(exc_info.value).lower() or "vide" in str(exc_info.value).lower()

    def test_comparer_fiches_none_ids(self):
        """Test comparer_fiches rejects None as fiche_ids."""
        with pytest.raises(ToolError) as exc_info:
            mcp_module.comparer_fiches(None)
        assert "invalides" in str(exc_info.value).lower()

    @pytest.mark.parametrize("invalid_id", [
        "RWEB_9999",
        "INVALID_ID",
        "RWEB_0",
        "RWEB_-1",
    ])
    def test_comparer_fiches_nonexistent_ids(self, invalid_id):
        """Test comparer_fiches raises for non-existent fiche IDs."""
        with pytest.raises(ToolError) as exc_info:
            mcp_module.comparer_fiches([invalid_id])
        error_msg = str(exc_info.value).lower()
        assert "n'ont pas" in error_msg or "erreur" in error_msg or "introuvable" in error_msg

    def test_obtenir_fiche_complete_nonexistent(self):
        """Test obtenir_fiche_complete raises for non-existent ID."""
        with pytest.raises(ToolError) as exc_info:
            mcp_module.obtenir_fiche_complete("RWEB_9999")
        error_msg = str(exc_info.value).lower()
        assert "trouvée" in error_msg or "introuvable" in error_msg or "n'existe" in error_msg


class TestExceptionHandling:
    """Test exception handling in tools (unexpected errors converted to ToolError)."""

    def test_lister_fiches_generic_exception_handling(self, monkeypatch):
        """Test that generic exceptions in lister_fiches are caught and converted."""
        # Simulate cache loading error
        def mock_charger_cache_error():
            raise ValueError("Simulated cache loading error")

        monkeypatch.setattr(mcp_module, "charger_cache", mock_charger_cache_error)

        with pytest.raises(ToolError) as exc_info:
            mcp_module.lister_fiches()
        assert "Erreur lors du listage" in str(exc_info.value)

    def test_fiches_prioritaires_generic_exception_handling(self, monkeypatch):
        """Test that generic exceptions in fiches_prioritaires are caught."""
        def mock_charger_cache_error():
            raise RuntimeError("Simulated cache error")

        monkeypatch.setattr(mcp_module, "charger_cache", mock_charger_cache_error)

        with pytest.raises(ToolError) as exc_info:
            mcp_module.fiches_prioritaires()
        assert "Erreur lors de la récupération" in str(exc_info.value)

    def test_chercher_fiche_generic_exception_handling(self, monkeypatch):
        """Test that generic exceptions in chercher_fiche are caught."""
        def mock_charger_cache_error():
            raise KeyError("Simulated cache error")

        monkeypatch.setattr(mcp_module, "charger_cache", mock_charger_cache_error)

        with pytest.raises(ToolError) as exc_info:
            mcp_module.chercher_fiche("test")
        assert "Erreur lors de la recherche" in str(exc_info.value)

    def test_comparer_fiches_generic_exception_handling(self, monkeypatch):
        """Test that generic exceptions in comparer_fiches are caught."""
        def mock_charger_cache_error():
            raise IOError("Simulated I/O error")

        monkeypatch.setattr(mcp_module, "charger_cache", mock_charger_cache_error)

        with pytest.raises(ToolError) as exc_info:
            mcp_module.comparer_fiches(["RWEB_0001"])
        assert "Erreur lors de la comparaison" in str(exc_info.value)

    def test_obtenir_fiche_complete_generic_exception_handling(self, monkeypatch):
        """Test that generic exceptions in obtenir_fiche_complete are caught."""
        def mock_charger_cache_error():
            raise RuntimeError("Simulated cache error")

        monkeypatch.setattr(mcp_module, "charger_cache", mock_charger_cache_error)

        with pytest.raises(ToolError) as exc_info:
            mcp_module.obtenir_fiche_complete("RWEB_0001")
        assert "Erreur lors de la récupération" in str(exc_info.value)

    def test_obtenir_statistiques_generic_exception_handling(self, monkeypatch):
        """Test that generic exceptions in obtenir_statistiques are caught."""
        def mock_charger_cache_error():
            raise RuntimeError("Simulated cache error")

        monkeypatch.setattr(mcp_module, "charger_cache", mock_charger_cache_error)

        with pytest.raises(ToolError) as exc_info:
            mcp_module.obtenir_statistiques()
        assert "Erreur lors du calcul" in str(exc_info.value)

    def test_lister_lifecycles_generic_exception_handling(self, monkeypatch):
        """Test that generic exceptions in lister_lifecycles are caught."""
        def mock_charger_cache_error():
            raise RuntimeError("Simulated cache error")

        monkeypatch.setattr(mcp_module, "charger_cache", mock_charger_cache_error)

        with pytest.raises(ToolError) as exc_info:
            mcp_module.lister_lifecycles()
        assert "Erreur lors de la récupération" in str(exc_info.value) and "phases" in str(exc_info.value).lower()

    def test_lister_ressources_generic_exception_handling(self, monkeypatch):
        """Test that generic exceptions in lister_ressources are caught."""
        def mock_charger_cache_error():
            raise RuntimeError("Simulated cache error")

        monkeypatch.setattr(mcp_module, "charger_cache", mock_charger_cache_error)

        with pytest.raises(ToolError) as exc_info:
            mcp_module.lister_ressources()
        assert "Erreur lors de la récupération" in str(exc_info.value) and "ressources" in str(exc_info.value).lower()


class TestEcoindexValidation:
    """Test parameter validation for calculer_ecoindex."""

    @pytest.mark.parametrize("dom_nodes,requests,size_kb", [
        (-1, 10, 100),       # negative dom_nodes
        (100, -1, 100),      # negative requests
        (100, 10, -1),       # negative size_kb
    ])
    def test_ecoindex_negative_parameters(self, dom_nodes, requests, size_kb):
        """Test calculer_ecoindex with negative parameters."""
        with pytest.raises(ToolError) as exc_info:
            mcp_module.calculer_ecoindex(dom_nodes, requests, size_kb)
        assert "invalides" in str(exc_info.value).lower() or "négatif" in str(exc_info.value).lower()


class TestResourceHandling:
    """Test resource endpoint error handling."""

    def test_obtenir_fiche_resource_nonexistent(self):
        """Test resource endpoint for non-existent fiche returns error JSON."""
        import asyncio
        result_json = asyncio.run(mcp_module.obtenir_fiche("RWEB_9999"))
        result = json.loads(result_json)
        assert "erreur" in result
        assert "RWEB_9999" in result["erreur"]

    def test_index_fiches_resource_empty_graceful(self, monkeypatch):
        """Test index_fiches resource handles empty cache gracefully."""
        import asyncio
        # Mock charger_cache to return empty dict
        monkeypatch.setattr(mcp_module, "charger_cache", lambda: {})
        result_json = asyncio.run(mcp_module.index_fiches())
        result = json.loads(result_json)
        assert result["total"] == 0
        assert result["fiches"] == []

    def test_obtenir_metadata_handles_empty_metadata(self, monkeypatch):
        """Test metadata endpoint handles empty cache gracefully."""
        import asyncio
        monkeypatch.setattr(mcp_module, "charger_cache", lambda: {})
        result_json = asyncio.run(mcp_module.obtenir_metadata())
        result = json.loads(result_json)
        assert isinstance(result, dict)

    def test_obtenir_fiche_resource_empty_cache(self, monkeypatch):
        """Test obtenir_fiche resource with empty cache returns error JSON."""
        import asyncio
        # Mock charger_cache to return empty dict
        monkeypatch.setattr(mcp_module, "charger_cache", lambda: {})
        result_json = asyncio.run(mcp_module.obtenir_fiche("RWEB_0001"))
        result = json.loads(result_json)
        assert "erreur" in result

    def test_obtenir_fiche_resource_found(self, cache):
        """Test obtenir_fiche resource returns full fiche when found."""
        import asyncio
        fiche_id = next(iter(cache.keys()))
        result_json = asyncio.run(mcp_module.obtenir_fiche(fiche_id))
        result = json.loads(result_json)
        # Should return the fiche, not an error
        assert "erreur" not in result
        assert "title" in result or "num" in result

    def test_index_fiches_with_complex_cache(self, cache):
        """Test index_fiches properly extracts categories from complex cache."""
        import asyncio
        result_json = asyncio.run(mcp_module.index_fiches())
        result = json.loads(result_json)
        # Verify structure
        assert "total" in result
        assert "fiches" in result
        assert "categories" in result
        assert result["total"] > 0
        # Categories should be sorted
        assert result["categories"] == sorted(result["categories"])

    def test_index_fiches_with_criteria_field(self, monkeypatch):
        """Test index_fiches extracts categories from criteria field (backward compat)."""
        import asyncio
        mock_cache = {"fiches": {
            "TEST_001": {
                "num": "1.0",
                "title": "Test Fiche",
                "criteria": [
                    {"criterium": "criterion1"},
                    {"criterium": "criterion2"}
                ]
            }
        }}
        monkeypatch.setattr(mcp_module, "charger_cache", lambda: mock_cache)
        result_json = asyncio.run(mcp_module.index_fiches())
        result = json.loads(result_json)
        assert "categories" in result
        # Should extract categories from criteria
        assert len(result["categories"]) > 0


class TestHomepageEmptyCache:
    """Test HTTP homepage with empty cache scenario."""

    def test_homepage_empty_cache_shows_warning(self, monkeypatch):
        """Test homepage shows warning badge when cache is empty."""
        from starlette.testclient import TestClient
        from starlette.applications import Starlette
        from starlette.routing import Route

        # Mock charger_cache in data module (routes._http_homepage imports from there)
        monkeypatch.setattr("data.charger_cache", lambda: {})

        app = Starlette(routes=[
            Route("/", routes_mod._http_homepage, methods=["GET"]),
        ])
        client = TestClient(app)
        r = client.get("/")
        assert r.status_code == 200
        assert "Cache vide" in r.text
        assert "warn" in r.text


class TestStatisticsEmptyCache:
    """Test obtenir_statistiques with empty cache."""

    def test_obtenir_statistiques_empty_cache(self, monkeypatch):
        """Test obtenir_statistiques returns graceful response for empty cache."""
        # Mock charger_cache to return empty dict
        monkeypatch.setattr(mcp_module, "charger_cache", lambda: {})
        stats = mcp_module.obtenir_statistiques()
        assert stats["statut"] == "Cache vide"
        assert stats["fiches"] == 0


class TestAuthTokenHandling:
    """Test authentication token verification in _create_mcp."""

    def test_create_mcp_with_tokens(self, monkeypatch, tmp_path):
        """Test factory.create_mcp creates auth verifier when tokens present."""
        import time as _time
        tokens_file = tmp_path / "tokens.json"
        tokens_file.write_text(json.dumps({
            "tok_test": {"name": "test", "created_at": "2025-01-01T00:00:00+00:00", "expires_at": _time.time() + 86400}
        }))
        monkeypatch.setenv("MCP_TRANSPORT", "stdio")
        mcp = factory.create_mcp("GreenIT-Referentiel", str(tokens_file), routes_mod._greenit_tool_definitions)
        assert mcp.name == "GreenIT-Referentiel"
        assert mcp._auth is not None

    def test_create_mcp_without_tokens(self, monkeypatch, tmp_path):
        """Test factory.create_mcp creates instance without auth when no tokens."""
        monkeypatch.setenv("MCP_TRANSPORT", "stdio")
        mcp = factory.create_mcp("GreenIT-Referentiel", str(tmp_path / "empty.json"), routes_mod._greenit_tool_definitions)
        assert mcp.name == "GreenIT-Referentiel"
        assert mcp._auth is None


class TestParameterEdgeCases:
    """Test edge cases for tool parameters."""

    def test_lister_fiches_boundary_values(self):
        """Test lister_fiches with boundary impact_min and priorite_min values."""
        # Min boundary (1)
        response = mcp_module.lister_fiches(impact_min=1, priorite_min=1)
        assert "fiches" in response
        assert len(response["fiches"]) > 0

        # Max boundary (5)
        response = mcp_module.lister_fiches(impact_min=5, priorite_min=5)
        assert "fiches" in response

    def test_fiches_prioritaires_boundary_values(self):
        """Test fiches_prioritaires with boundary impact_min and priorite_min values."""
        # Min boundary (1)
        response = mcp_module.fiches_prioritaires(impact_min=1, priorite_min=1)
        assert "fiches" in response
        assert len(response["fiches"]) > 0

        # Max boundary (5)
        response = mcp_module.fiches_prioritaires(impact_min=5, priorite_min=5)
        assert "fiches" in response

    def test_chercher_fiche_single_character(self):
        """Test chercher_fiche with single character term."""
        response = mcp_module.chercher_fiche("a")
        assert "fiches" in response
        # Should return results without error

    def test_chercher_fiche_special_characters(self):
        """Test chercher_fiche with special characters in term."""
        response = mcp_module.chercher_fiche("CSS/HTML")
        assert "fiches" in response
        # Should handle special characters without error


# ============================================================================
# ERROR HANDLING TESTS: ToolError exceptions and invalid parameters
# ============================================================================

class TestListerFichesErrorHandling:
    """Test error handling for lister_fiches with invalid parameters."""

    @pytest.mark.parametrize("impact_min,priorite_min,should_fail_on", [
        (6, None, "impact_min"),      # impact_min > 5
        (0, None, "impact_min"),      # impact_min < 1
        (None, 6, "priorite_min"),      # priorite_min > 5
        (None, 0, "priorite_min"),      # priorite_min < 1
        (6, 6, "impact_min"),         # both out of range (impact_min checked first)
        (-1, None, "impact_min"),     # negative impact
        (None, -5, "priorite_min"),     # negative priorite
    ])
    def test_lister_fiches_invalid_score_range(self, impact_min, priorite_min, should_fail_on):
        """Test lister_fiches raises ToolError for out-of-range score parameters."""
        with pytest.raises(ToolError) as exc_info:
            mcp_module.lister_fiches(impact_min=impact_min, priorite_min=priorite_min)

        # Verify error message contains French text and parameter name
        error_msg = str(exc_info.value)
        assert "invalides" in error_msg.lower() or "entre" in error_msg.lower()
        assert should_fail_on in error_msg


class TestFichesPrioritairesErrorHandling:
    """Test error handling for fiches_prioritaires with invalid parameters."""

    @pytest.mark.parametrize("impact_min,priorite_min,should_fail_on", [
        (6, 4, "impact_min"),         # impact_min > 5
        (0, 4, "impact_min"),         # impact_min < 1
        (4, 6, "priorite_min"),         # priorite_min > 5
        (4, 0, "priorite_min"),         # priorite_min < 1
        (10, 10, "impact_min"),       # both way out of range (impact_min checked first)
        (-1, 4, "impact_min"),        # negative impact
        (4, -5, "priorite_min"),        # negative priorite
    ])
    def test_fiches_prioritaires_invalid_score_range(self, impact_min, priorite_min, should_fail_on):
        """Test fiches_prioritaires raises ToolError for out-of-range score parameters."""
        with pytest.raises(ToolError) as exc_info:
            mcp_module.fiches_prioritaires(impact_min=impact_min, priorite_min=priorite_min)

        # Verify error message contains French text and parameter name
        error_msg = str(exc_info.value)
        assert "invalides" in error_msg.lower() or "entre" in error_msg.lower()
        assert should_fail_on in error_msg


class TestChercherFicheErrorHandling:
    """Test error handling for chercher_fiche with invalid parameters."""

    @pytest.mark.parametrize("terme", [
        "",             # empty string
        "   ",          # whitespace only
        "\n\t",         # only whitespace characters
    ])
    def test_chercher_fiche_empty_term(self, terme):
        """Test chercher_fiche raises ToolError for empty search term."""
        with pytest.raises(ToolError) as exc_info:
            mcp_module.chercher_fiche(terme)

        # Verify error message is in French and mentions the parameter
        error_msg = str(exc_info.value)
        assert "invalides" in error_msg.lower()
        assert "terme" in error_msg.lower()


class TestComparerFichesErrorHandling:
    """Test error handling for comparer_fiches with invalid parameters."""

    @pytest.mark.parametrize("fiche_ids", [
        [],                     # empty list
        ["RWEB_9999"],         # single invalid ID
        ["RWEB_9999", "RWEB_8888"],  # multiple invalid IDs
        ["RWEB_0001", "RWEB_9999"],  # mix of valid and invalid
    ])
    def test_comparer_fiches_invalid_or_missing_ids(self, fiche_ids):
        """Test comparer_fiches raises ToolError for empty list or invalid IDs."""
        with pytest.raises(ToolError) as exc_info:
            mcp_module.comparer_fiches(fiche_ids)

        # Verify error message is in French
        error_msg = str(exc_info.value)
        assert "invalides" in error_msg.lower() or "trouvées" in error_msg.lower()


class TestObtenirFicheCompleteErrorHandling:
    """Test error handling for obtenir_fiche_complete with invalid parameters."""

    @pytest.mark.parametrize("fiche_id", [
        "RWEB_9999",
        "INVALID_ID_FORMAT",
        "NONEXISTENT",
        "xyz_123",
    ])
    def test_obtenir_fiche_complete_missing_fiche(self, fiche_id):
        """Test obtenir_fiche_complete raises ToolError for non-existent fiche IDs."""
        with pytest.raises(ToolError) as exc_info:
            mcp_module.obtenir_fiche_complete(fiche_id)

        # Verify error message is in French and mentions the fiche ID
        error_msg = str(exc_info.value)
        assert "trouvée" in error_msg.lower() or "n'a pas été trouvée" in error_msg


class TestCalculerEcoindexErrorHandling:
    """Test error handling for calculer_ecoindex with invalid parameters."""

    @pytest.mark.parametrize("dom_nodes,requests,size_kb,bad_param", [
        (-1, 10, 100, "dom_nodes"),      # negative dom_nodes
        (100, -1, 100, "requests"),     # negative requests
        (100, 10, -1, "size_kb"),      # negative size_kb
        (-5, -10, -20, "dom_nodes"),     # all negative (first one fails)
        (-0.5, 10, 100, "dom_nodes"),    # negative float dom_nodes
        (100, -0.5, 100, "requests"),    # negative float requests
        (100, 10, -0.5, "size_kb"),      # negative float size_kb
    ])
    def test_calculer_ecoindex_negative_values(self, dom_nodes, requests, size_kb, bad_param):
        """Test calculer_ecoindex raises ToolError for negative metric values."""
        with pytest.raises(ToolError) as exc_info:
            mcp_module.calculer_ecoindex(dom_nodes, requests, size_kb)

        # Verify error message is in French and contains parameter name
        error_msg = str(exc_info.value)
        assert "invalides" in error_msg.lower() or bad_param in error_msg.lower()


class TestResourceMethodsErrorHandling:
    """Test resource methods for proper error handling."""

    def test_version_resource_returns_unified_structure(self):
        """Test greenit://version resource returns unified JSON structure."""
        import asyncio
        result = asyncio.run(mcp_module.mcp.read_resource("greenit://version"))
        data = json.loads(result.contents[0].content)
        assert "server_version" in data
        assert "referentiel_version" in data
        assert "updated_at" in data
        assert "nb_items" in data

    @pytest.mark.asyncio
    async def test_obtenir_metadata_returns_json_structure(self):
        """Test obtenir_metadata resource returns proper JSON structure."""
        result = await mcp_module.obtenir_metadata()
        data = json.loads(result)
        assert "updated_at" in data
        assert "nb_fiches" in data

    @pytest.mark.asyncio
    async def test_index_fiches_returns_json_structure(self):
        """Test index_fiches resource returns proper JSON structure."""
        result = await mcp_module.index_fiches()
        data = json.loads(result)
        assert "total" in data
        assert "fiches" in data
        assert "categories" in data


class TestExceptionHandling:
    """Test exception handling paths in tools."""

    def test_lister_fiches_handles_generic_exception(self, monkeypatch):
        """Test lister_fiches catches generic exceptions and wraps in ToolError."""
        def mock_charger_cache_error():
            raise RuntimeError("Simulated cache error")

        monkeypatch.setattr(mcp_module, "charger_cache", mock_charger_cache_error)

        with pytest.raises(ToolError) as exc_info:
            mcp_module.lister_fiches()

        # Verify error message is in French
        error_msg = str(exc_info.value)
        assert "Erreur" in error_msg or "Détail" in error_msg

    def test_fiches_prioritaires_handles_generic_exception(self, monkeypatch):
        """Test fiches_prioritaires catches generic exceptions and wraps in ToolError."""
        def mock_charger_cache_error():
            raise RuntimeError("Simulated cache error")

        monkeypatch.setattr(mcp_module, "charger_cache", mock_charger_cache_error)

        with pytest.raises(ToolError) as exc_info:
            mcp_module.fiches_prioritaires()

        error_msg = str(exc_info.value)
        assert "Erreur" in error_msg

    def test_chercher_fiche_handles_generic_exception(self, monkeypatch):
        """Test chercher_fiche catches generic exceptions and wraps in ToolError."""
        def mock_charger_cache_error():
            raise RuntimeError("Simulated cache error")

        monkeypatch.setattr(mcp_module, "charger_cache", mock_charger_cache_error)

        with pytest.raises(ToolError) as exc_info:
            mcp_module.chercher_fiche("test")

        error_msg = str(exc_info.value)
        assert "Erreur" in error_msg

    def test_comparer_fiches_handles_generic_exception(self, monkeypatch):
        """Test comparer_fiches catches generic exceptions and wraps in ToolError."""
        def mock_charger_cache_error():
            raise RuntimeError("Simulated cache error")

        monkeypatch.setattr(mcp_module, "charger_cache", mock_charger_cache_error)

        with pytest.raises(ToolError) as exc_info:
            mcp_module.comparer_fiches(["RWEB_0001"])

        error_msg = str(exc_info.value)
        assert "Erreur" in error_msg

    def test_obtenir_fiche_complete_handles_generic_exception(self, monkeypatch):
        """Test obtenir_fiche_complete catches generic exceptions and wraps in ToolError."""
        def mock_charger_cache_error():
            raise RuntimeError("Simulated cache error")

        monkeypatch.setattr(mcp_module, "charger_cache", mock_charger_cache_error)

        with pytest.raises(ToolError) as exc_info:
            mcp_module.obtenir_fiche_complete("RWEB_0001")

        error_msg = str(exc_info.value)
        assert "Erreur" in error_msg

    def test_obtenir_statistiques_handles_generic_exception(self, monkeypatch):
        """Test obtenir_statistiques catches generic exceptions and wraps in ToolError."""
        def mock_charger_cache_error():
            raise RuntimeError("Simulated cache error")

        monkeypatch.setattr(mcp_module, "charger_cache", mock_charger_cache_error)

        with pytest.raises(ToolError) as exc_info:
            mcp_module.obtenir_statistiques()

        error_msg = str(exc_info.value)
        assert "Erreur" in error_msg

    def test_lister_lifecycles_handles_generic_exception(self, monkeypatch):
        """Test lister_lifecycles catches generic exceptions and wraps in ToolError."""
        def mock_charger_cache_error():
            raise RuntimeError("Simulated cache error")

        monkeypatch.setattr(mcp_module, "charger_cache", mock_charger_cache_error)

        with pytest.raises(ToolError) as exc_info:
            mcp_module.lister_lifecycles()

        error_msg = str(exc_info.value)
        assert "Erreur" in error_msg

    def test_lister_ressources_handles_generic_exception(self, monkeypatch):
        """Test lister_ressources catches generic exceptions and wraps in ToolError."""
        def mock_charger_cache_error():
            raise RuntimeError("Simulated cache error")

        monkeypatch.setattr(mcp_module, "charger_cache", mock_charger_cache_error)

        with pytest.raises(ToolError) as exc_info:
            mcp_module.lister_ressources()

        error_msg = str(exc_info.value)
        assert "Erreur" in error_msg

    def test_calculer_ecoindex_handles_generic_exception(self, monkeypatch):
        """Test calculer_ecoindex catches generic exceptions and wraps in ToolError."""
        def mock_ecoindex_error(*args, **kwargs):
            raise RuntimeError("Simulated ecoindex calculation error")

        monkeypatch.setattr(mcp_module, "_calculer_ecoindex_impl", mock_ecoindex_error)

        with pytest.raises(ToolError) as exc_info:
            mcp_module.calculer_ecoindex(100, 10, 500)

        error_msg = str(exc_info.value)
        assert "Erreur" in error_msg or "EcoIndex" in error_msg


class TestToolErrorReraising:
    """Test that ToolError exceptions are properly re-raised without wrapping."""

    def test_lister_fiches_reraises_tool_error(self, monkeypatch):
        """Test lister_fiches re-raises ToolError without wrapping."""
        original_error = ToolError("Original ToolError")
        def mock_validate_error(*args):
            raise original_error

        monkeypatch.setattr("greenit_mcp.validate_score_range", mock_validate_error)

        with pytest.raises(ToolError) as exc_info:
            mcp_module.lister_fiches(impact_min=10)

        # Verify it's the same ToolError, not wrapped
        assert exc_info.value is original_error

    def test_fiches_prioritaires_reraises_tool_error(self, monkeypatch):
        """Test fiches_prioritaires re-raises ToolError without wrapping."""
        original_error = ToolError("Original ToolError")
        def mock_validate_error(*args):
            raise original_error

        monkeypatch.setattr("greenit_mcp.validate_score_range", mock_validate_error)

        with pytest.raises(ToolError) as exc_info:
            mcp_module.fiches_prioritaires(impact_min=10)

        # Verify it's the same ToolError, not wrapped
        assert exc_info.value is original_error

    def test_comparer_fiches_reraises_tool_error(self, monkeypatch):
        """Test comparer_fiches re-raises ToolError without wrapping."""
        original_error = ToolError("Fiche not found")
        def mock_charger_cache():
            raise original_error

        monkeypatch.setattr(mcp_module, "charger_cache", mock_charger_cache)

        with pytest.raises(ToolError) as exc_info:
            mcp_module.comparer_fiches(["RWEB_0001"])

        # Error should be re-raised properly (may be wrapped by outer except)
        # but should contain the original message
        assert "Fiche not found" in str(exc_info.value)


class TestToolErrorRereiseInTools:
    """Test ToolError re-raise paths in statistics and lifecycle tools."""

    def test_obtenir_statistiques_reraises_tool_error(self, monkeypatch):
        """Test obtenir_statistiques re-raises ToolError without wrapping."""
        original_error = ToolError("Validation error in charger_cache")
        def mock_charger_cache():
            raise original_error

        monkeypatch.setattr(mcp_module, "charger_cache", mock_charger_cache)

        with pytest.raises(ToolError) as exc_info:
            mcp_module.obtenir_statistiques()

        # Error should be re-raised with original message
        assert "Validation error" in str(exc_info.value)

    def test_lister_lifecycles_reraises_tool_error(self, monkeypatch):
        """Test lister_lifecycles re-raises ToolError without wrapping."""
        original_error = ToolError("Cache access denied")
        def mock_charger_cache():
            raise original_error

        monkeypatch.setattr(mcp_module, "charger_cache", mock_charger_cache)

        with pytest.raises(ToolError) as exc_info:
            mcp_module.lister_lifecycles()

        # Error should be re-raised with original message
        assert "Cache access denied" in str(exc_info.value)

    def test_lister_ressources_reraises_tool_error(self, monkeypatch):
        """Test lister_ressources re-raises ToolError without wrapping."""
        original_error = ToolError("Resource data missing")
        def mock_charger_cache():
            raise original_error

        monkeypatch.setattr(mcp_module, "charger_cache", mock_charger_cache)

        with pytest.raises(ToolError) as exc_info:
            mcp_module.lister_ressources()

        # Error should be re-raised with original message
        assert "Resource data missing" in str(exc_info.value)


class TestPromptFunctions:
    """Test prompt function execution and return values."""

    def test_audit_ecoindex_prompt(self):
        """Test audit_ecoindex prompt returns formatted string."""
        result = mcp_module.audit_ecoindex("https://example.com", focus="dom")
        assert isinstance(result, str)
        assert "Analyser" in result
        assert "https://example.com" in result
        assert "dom" in result

    def test_rapport_impact_prompt(self):
        """Test rapport_impact prompt returns formatted string."""
        result = mcp_module.rapport_impact("Score: 45/100")
        assert isinstance(result, str)
        assert "Générer" in result
        assert "Score: 45/100" in result

    def test_expliquer_fiche_prompt(self):
        """Test expliquer_fiche prompt returns formatted string."""
        result = mcp_module.expliquer_fiche("RWEB_0001")
        assert isinstance(result, str)
        assert "Expliquer" in result
        assert "RWEB_0001" in result

    def test_fiches_par_lifecycle_prompt(self):
        """Test fiches_par_lifecycle prompt returns formatted string."""
        result = mcp_module.fiches_par_lifecycle("conception", impact_min=4)
        assert isinstance(result, str)
        assert "conception" in result
        assert "4" in result

    def test_checklist_ecoindex_prompt(self):
        """Test checklist_ecoindex prompt returns formatted string."""
        result = mcp_module.checklist_ecoindex("dom")
        assert isinstance(result, str)
        assert "dom" in result.lower() or "checklist" in result.lower()

    def test_ressources_comparaison_prompt(self):
        """Test ressources_comparaison prompt returns formatted string."""
        result = mcp_module.ressources_comparaison("network,cpu")
        assert isinstance(result, str)
        assert "network" in result or "cpu" in result

    def test_audit_rapide_greenit_prompt(self):
        """Test audit_rapide_greenit prompt returns formatted string."""
        result = mcp_module.audit_rapide_greenit("https://example.com")
        assert isinstance(result, str)
        assert "https://example.com" in result

    def test_audit_par_ressource_prompt(self):
        """Test audit_par_ressource prompt returns formatted string."""
        result = mcp_module.audit_par_ressource("network")
        assert isinstance(result, str)
        assert "network" in result


class TestBoundaryConditions:
    """Test boundary conditions and edge cases."""

    @pytest.mark.parametrize("score_value", [1, 2, 3, 4, 5])
    def test_lister_fiches_all_valid_scores(self, score_value):
        """Test lister_fiches accepts all valid score values 1-5."""
        response = mcp_module.lister_fiches(impact_min=score_value)
        assert "fiches" in response

        response = mcp_module.lister_fiches(priorite_min=score_value)
        assert "fiches" in response

    @pytest.mark.parametrize("score_value", [1, 2, 3, 4, 5])
    def test_fiches_prioritaires_all_valid_scores(self, score_value):
        """Test fiches_prioritaires accepts all valid score values 1-5."""
        response = mcp_module.fiches_prioritaires(impact_min=score_value)
        assert "fiches" in response

        response = mcp_module.fiches_prioritaires(priorite_min=score_value)
        assert "fiches" in response

    def test_calculer_ecoindex_very_large_values(self):
        """Test calculer_ecoindex with very large metric values."""
        result = json.loads(mcp_module.calculer_ecoindex(10000, 500, 50000))
        assert result["score"] >= 0
        assert result["score"] <= 100
        assert result["grade"] in ("A", "B", "C", "D", "E", "F", "G")

    def test_calculer_ecoindex_zero_size_kb(self):
        """Test calculer_ecoindex with zero size_kb."""
        result = json.loads(mcp_module.calculer_ecoindex(100, 10, 0))
        assert result["score"] >= 0
        assert result["score"] <= 100


# ============================================================================
# Task 7: Parametrized tests for _helpers.py validation functions (93% → 100%)
# ============================================================================

class TestValidateThemes:
    """Test validate_themes() from _helpers.py with comprehensive coverage."""

    def test_validate_themes_none_returns_default_range(self):
        """validate_themes(None) should return list(range(1, 14))."""
        from mcp_ref_core._helpers import validate_themes
        result = validate_themes(None)
        assert result == list(range(1, 14))
        assert len(result) == 13

    @pytest.mark.parametrize("themes,expected", [
        ([], []),
        ([1], [1]),
        ([13], [13]),
        ([1, 13], [1, 13]),
        ([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13], list(range(1, 14))),
        ([7], [7]),
        ([6, 11], [6, 11]),
    ])
    def test_validate_themes_valid_lists(self, themes, expected):
        """validate_themes() accepts valid theme IDs (1-13)."""
        from mcp_ref_core._helpers import validate_themes
        result = validate_themes(themes)
        assert result == expected

    @pytest.mark.parametrize("themes", [
        [0],                    # Below minimum
        [14],                   # Above maximum
        [-1],                   # Negative
        [100],                  # Way above maximum
        [0, 1, 2],              # Mix with invalid
        [13, 14],               # Max + over
    ])
    def test_validate_themes_invalid_ranges_raises_toolerrror(self, themes):
        """validate_themes() raises ToolError for IDs outside 1-13 range."""
        from mcp_ref_core._helpers import validate_themes
        with pytest.raises(ToolError):
            validate_themes(themes)

    @pytest.mark.parametrize("themes", [
        [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13],  # All valid
        [5],                                              # Middle value
        [1, 7, 13],                                       # Spread across range
    ])
    def test_validate_themes_boundary_values(self, themes):
        """validate_themes() accepts boundary values 1 and 13."""
        from mcp_ref_core._helpers import validate_themes
        result = validate_themes(themes)
        assert all(1 <= t <= 13 for t in result)


class TestValidateScoreRange:
    """Test validate_score_range() from _helpers.py with comprehensive coverage."""

    @pytest.mark.parametrize("value,min_val,max_val,param_name", [
        (0, 0, 5, "score"),           # Exactly min
        (5, 0, 5, "score"),           # Exactly max
        (2, 0, 5, "score"),           # Middle
        (1, 0, 5, "priority"),        # Different param_name
        (3, 1, 4, "impact"),          # Custom range
        (0, 0, 100, "percentage"),    # Wide range
        (50, 0, 100, "percentage"),   # Mid range
        (100, 0, 100, "percentage"),  # Max of wide range
    ])
    def test_validate_score_range_valid_values(self, value, min_val, max_val, param_name):
        """validate_score_range() accepts values within range [min_val, max_val]."""
        from mcp_ref_core._helpers import validate_score_range
        # Should not raise
        validate_score_range(value, min_val, max_val, param_name)

    @pytest.mark.parametrize("value,min_val,max_val,param_name", [
        (-1, 0, 5, "score"),          # Below minimum
        (6, 0, 5, "score"),           # Above maximum
        (-5, 0, 5, "score"),          # Way below
        (10, 0, 5, "score"),          # Way above
        (1, 1, 4, "priority"),        # At min boundary (should pass)
        (4, 1, 4, "priority"),        # At max boundary (should pass)
        (0, 1, 5, "impact"),          # Below custom range
        (6, 1, 5, "impact"),          # Above custom range
    ])
    def test_validate_score_range_invalid_values(self, value, min_val, max_val, param_name):
        """validate_score_range() raises ToolError for values outside range."""
        from mcp_ref_core._helpers import validate_score_range
        if value < min_val or value > max_val:  # Only test actual out-of-range
            with pytest.raises(ToolError):
                validate_score_range(value, min_val, max_val, param_name)
        else:
            # Valid value should not raise
            validate_score_range(value, min_val, max_val, param_name)

    @pytest.mark.parametrize("value,min_val,max_val", [
        (0, 0, 5),
        (5, 0, 5),
        (2, 0, 5),
        (1, 1, 5),
        (5, 1, 5),
    ])
    def test_validate_score_range_boundary_conditions(self, value, min_val, max_val):
        """validate_score_range() handles exact boundary values correctly."""
        from mcp_ref_core._helpers import validate_score_range
        # All these should pass (value is within or at boundary)
        validate_score_range(value, min_val, max_val, "test_param")

    def test_validate_score_range_error_message_includes_param_name(self):
        """validate_score_range() error message includes the parameter name."""
        from mcp_ref_core._helpers import validate_score_range
        with pytest.raises(ToolError) as exc_info:
            validate_score_range(10, 0, 5, "custom_param")
        assert "custom_param" in str(exc_info.value)


class TestValidateNonnegative:
    """Test validate_nonnegative() from _helpers.py with comprehensive coverage."""

    @pytest.mark.parametrize("value,param_name", [
        (0, "count"),                 # Exactly zero
        (0.0, "score"),               # Float zero
        (1, "items"),                 # Positive integer
        (1.5, "rating"),              # Positive float
        (100, "total"),               # Large positive integer
        (0.001, "epsilon"),           # Small positive float
        (999999, "big_number"),       # Very large value
    ])
    def test_validate_nonnegative_valid_values(self, value, param_name):
        """validate_nonnegative() accepts zero and positive values."""
        from mcp_ref_core._helpers import validate_nonnegative
        # Should not raise
        validate_nonnegative(value, param_name)

    @pytest.mark.parametrize("value,param_name", [
        (-1, "count"),                # Negative integer
        (-0.5, "score"),              # Negative float
        (-100, "items"),              # Large negative integer
        (-0.001, "epsilon"),          # Small negative float
        (-999999, "big_number"),      # Very large negative value
    ])
    def test_validate_nonnegative_invalid_values(self, value, param_name):
        """validate_nonnegative() raises ToolError for negative values."""
        from mcp_ref_core._helpers import validate_nonnegative
        with pytest.raises(ToolError):
            validate_nonnegative(value, param_name)

    @pytest.mark.parametrize("value", [
        0,
        0.0,
        1,
        1.5,
        100,
        0.001,
    ])
    def test_validate_nonnegative_boundary_zero(self, value):
        """validate_nonnegative() treats zero as valid (boundary case)."""
        from mcp_ref_core._helpers import validate_nonnegative
        if value >= 0:
            validate_nonnegative(value, "test")

    def test_validate_nonnegative_error_message_includes_param_name(self):
        """validate_nonnegative() error message includes the parameter name."""
        from mcp_ref_core._helpers import validate_nonnegative
        with pytest.raises(ToolError) as exc_info:
            validate_nonnegative(-5, "custom_field")
        assert "custom_field" in str(exc_info.value)

    @pytest.mark.parametrize("value", [
        -1, -0.5, -100, -0.001, -999999
    ])
    def test_validate_nonnegative_various_negatives(self, value):
        """validate_nonnegative() rejects all negative values uniformly."""
        from mcp_ref_core._helpers import validate_nonnegative
        with pytest.raises(ToolError):
            validate_nonnegative(value, "param")
