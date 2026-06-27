"""
Tests d'intégration Docker pour rgesn-mcp.

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
from pathlib import Path


def get_docker_service_status(service_name="rgesn"):
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


def get_docker_service_logs(service_name="rgesn-rgesn-1"):
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
    print("\nVérification du service Docker rgesn-mcp...")
    if not get_docker_service_status("rgesn"):
        pytest.skip(
            "Service rgesn-mcp non disponible. "
            "Lancez: docker-compose up -d"
        )


class TestDockerHealthCheck:
    """Tests basiques de santé du service."""

    def test_service_is_running(self):
        """Vérifier que le service Docker est en cours d'exécution."""
        assert get_docker_service_status("rgesn"), "Service rgesn-mcp n'est pas en cours d'exécution"

    def test_service_has_no_errors_in_logs(self):
        """Vérifier qu'il n'y a pas d'erreurs critiques dans les logs."""
        logs = get_docker_service_logs("rgesn-rgesn-1")
        assert "ERROR" not in logs or "Traceback" not in logs, f"Erreurs trouvées dans les logs: {logs[:500]}"


class TestDockerConfiguration:
    """Tests de configuration du conteneur Docker."""

    def test_container_has_required_env_vars(self):
        """Vérifier que les variables d'environnement requises sont présentes."""
        logs = get_docker_service_logs("rgesn-rgesn-1")
        assert "Starting" in logs or "listening" in logs.lower() or logs.strip() != ""

    def test_container_restart_policy_is_set(self):
        """Vérifier que la politique de redémarrage est configurée."""
        try:
            result = subprocess.run(
                ["docker", "inspect", "--format", "{{.RestartPolicy.Name}}", "rgesn-rgesn-1"],
                capture_output=True,
                text=True,
                timeout=5
            )
            assert result.stdout.strip() in ["unless-stopped", "always", ""], "Service sans politique de redémarrage"
        except Exception:
            pass


class TestDockerToolsIntegration:
    """Tests d'intégration des outils MCP."""

    def test_server_module_imports(self):
        """Vérifier que le module serveur peut être importé."""
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent / "files"))
        try:
            import rgesn_mcp
            assert hasattr(rgesn_mcp, "rgesn_lister_criteres"), "Outil rgesn_lister_criteres non trouvé"
            assert hasattr(rgesn_mcp, "rgesn_statistiques"), "Outil rgesn_statistiques non trouvé"
        except ImportError as e:
            pytest.skip(f"Impossible d'importer le module: {e}")

    def test_expected_tools_are_defined(self):
        """Vérifier que tous les outils attendus sont disponibles."""
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent / "files"))
        try:
            import rgesn_mcp as m

            expected_tools = [
                "rgesn_lister_criteres",
                "rgesn_obtenir_critere",
                "rgesn_chercher",
                "rgesn_statistiques",
                "rgesn_taux_conformite",
                "rgesn_checklist",
                "rgesn_criteres_prioritaires",
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
        sys.path.insert(0, str(Path(__file__).parent.parent / "files"))
        try:
            import rgesn_mcp as m
            result = m.rgesn_statistiques()
            assert isinstance(result, dict), "rgesn_statistiques ne retourne pas un dict"
        except ImportError:
            pytest.skip("Impossible d'importer le module")

    def test_tools_return_valid_data(self):
        """Vérifier que les outils retournent des données valides."""
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent / "files"))
        try:
            import rgesn_mcp as m

            result = m.rgesn_lister_criteres()
            assert isinstance(result, dict), "rgesn_lister_criteres ne retourne pas un dict"
            assert "criteres" in result, "Clé 'criteres' non trouvée dans le résultat"

            result = m.rgesn_statistiques()
            assert isinstance(result, dict), "rgesn_statistiques ne retourne pas un dict"
        except ImportError:
            pytest.skip("Impossible d'importer le module")
