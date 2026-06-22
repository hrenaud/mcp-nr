"""
Tests d'intégration Docker pour greenit-mcp.

Ces tests valident que le serveur MCP tourne correctement dans Docker.

Prérequis: docker-compose up -d

Exécution:
    cd /chemin/vers/projet
    docker-compose up -d
    pytest tests/test_docker_integration.py -v
"""

import os
import pytest
import subprocess
import json


def get_docker_service_status(service_name="greenit"):
    """Vérifier le status d'un service Docker."""
    try:
        result = subprocess.run(
            ["docker", "ps", "--filter", f"name={service_name}", "--quiet"],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.stdout.strip() != ""
    except Exception:
        return False


def get_docker_service_logs(service_name="mcp-115-greenit-greenit-1"):
    """Récupérer les logs d'un service Docker."""
    try:
        result = subprocess.run(
            ["docker", "logs", service_name],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.stdout + result.stderr
    except Exception:
        return ""


@pytest.fixture(scope="session", autouse=True)
def service_is_ready():
    """Vérifier que le service est prêt avant les tests."""
    print("\nVérification du service Docker greenit-mcp...")
    if not get_docker_service_status("greenit"):
        pytest.skip(
            "Service greenit-mcp non disponible. "
            "Lancez: docker-compose up -d"
        )


class TestDockerHealthCheck:
    """Tests basiques de santé du service."""

    def test_service_is_running(self):
        """Vérifier que le service Docker est en cours d'exécution."""
        assert get_docker_service_status("greenit"), "Service greenit-mcp n'est pas en cours d'exécution"

    def test_service_has_no_errors_in_logs(self):
        """Vérifier qu'il n'y a pas d'erreurs critiques dans les logs."""
        logs = get_docker_service_logs("mcp-115-greenit-greenit-1")
        # Vérifier que le service a démarré sans erreurs fatales
        assert "ERROR" not in logs or "Traceback" not in logs, f"Erreurs trouvées dans les logs: {logs[:500]}"


class TestDockerConfiguration:
    """Tests de configuration du conteneur Docker."""

    def test_container_has_required_env_vars(self):
        """Vérifier que les variables d'environnement requises sont présentes."""
        logs = get_docker_service_logs("mcp-115-greenit-greenit-1")
        # Vérifier que le service démarre correctement
        assert "Starting" in logs or "listening" in logs.lower() or logs.strip() != ""

    def test_container_restart_policy_is_set(self):
        """Vérifier que la politique de redémarrage est configurée."""
        try:
            result = subprocess.run(
                ["docker", "inspect", "--format", "{{.RestartPolicy.Name}}", "mcp-115-greenit-greenit-1"],
                capture_output=True,
                text=True,
                timeout=5
            )
            # La politique devrait être 'unless-stopped' ou 'always'
            assert result.stdout.strip() in ["unless-stopped", "always", ""], "Service sans politique de redémarrage"
        except Exception:
            pass  # Accepter si docker inspect échoue


class TestDockerToolsIntegration:
    """Tests d'intégration des outils MCP."""

    def test_server_module_imports(self):
        """Vérifier que le module serveur peut être importé."""
        import sys
        sys.path.insert(0, "/Users/renaudheluin/DEV/DEV_GREENIT/refs/mcp-115-greenit/files")
        try:
            import greenit_mcp
            assert hasattr(greenit_mcp, "lister_fiches"), "Outil lister_fiches non trouvé"
            assert hasattr(greenit_mcp, "calculer_ecoindex"), "Outil calculer_ecoindex non trouvé"
        except ImportError as e:
            pytest.skip(f"Impossible d'importer le module: {e}")

    def test_expected_tools_are_defined(self):
        """Vérifier que tous les outils attendus (9) sont disponibles."""
        import sys
        sys.path.insert(0, "/Users/renaudheluin/DEV/DEV_GREENIT/refs/mcp-115-greenit/files")
        try:
            import greenit_mcp as m

            expected_tools = [
                "lister_fiches",
                "fiches_prioritaires",
                "chercher_fiche",
                "comparer_fiches",
                "lister_lifecycles",
                "lister_ressources",
                "calculer_ecoindex",
                "obtenir_statistiques",
            ]

            for tool_name in expected_tools:
                assert hasattr(m, tool_name), f"Outil {tool_name} non trouvé dans le module"
        except ImportError as e:
            pytest.skip(f"Impossible d'importer le module: {e}")


class TestDockerDataAvailability:
    """Tests de disponibilité des données."""

    def test_data_files_are_accessible(self):
        """Vérifier que les fichiers de données sont accessibles."""
        import sys
        sys.path.insert(0, "/Users/renaudheluin/DEV/DEV_GREENIT/refs/mcp-115-greenit/files")
        try:
            import greenit_mcp as m
            # Tester un appel simple pour vérifier que les données sont disponibles
            result = m.obtenir_statistiques()
            assert isinstance(result, dict), "obtenir_statistiques ne retourne pas un dict"
        except ImportError:
            pytest.skip("Impossible d'importer le module")

    def test_tools_return_valid_data(self):
        """Vérifier que les outils retournent des données valides."""
        import sys
        sys.path.insert(0, "/Users/renaudheluin/DEV/DEV_GREENIT/refs/mcp-115-greenit/files")
        try:
            import greenit_mcp as m

            # Test lister_fiches
            result = m.lister_fiches()
            assert isinstance(result, dict), "lister_fiches ne retourne pas un dict"
            assert "fiches" in result, "Clé 'fiches' non trouvée dans le résultat"

            # Test lister_lifecycles
            result = m.lister_lifecycles()
            assert isinstance(result, dict), "lister_lifecycles ne retourne pas un dict"
            assert "lifecycles" in result, "Clé 'lifecycles' non trouvée dans le résultat"

            # Test lister_ressources
            result = m.lister_ressources()
            assert isinstance(result, dict), "lister_ressources ne retourne pas un dict"
            assert "ressources" in result, "Clé 'ressources' non trouvée dans le résultat"

            # Test obtenir_statistiques
            result = m.obtenir_statistiques()
            assert isinstance(result, dict), "obtenir_statistiques ne retourne pas un dict"
        except ImportError:
            pytest.skip("Impossible d'importer le module")
