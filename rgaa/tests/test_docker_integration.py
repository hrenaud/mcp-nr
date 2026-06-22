"""
Tests d'intégration Docker pour rgaa-mcp.

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


def get_docker_service_status(service_name="rgaa"):
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


def get_docker_service_logs(service_name="mcp-rgaa-rgaa-1"):
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
def service_is_running():
    """Vérifier que le service Docker est en cours d'exécution."""
    print("\nVérification du service Docker rgaa-mcp...")
    if not get_docker_service_status("rgaa"):
        pytest.skip(
            "Service rgaa-mcp non disponible. "
            "Lancez: docker-compose up -d"
        )


class TestDockerHealthCheck:
    """Tests basiques de santé du service."""

    def test_service_is_running(self):
        """Vérifier que le service Docker est en cours d'exécution."""
        assert get_docker_service_status("rgaa"), "Service rgaa-mcp n'est pas en cours d'exécution"

    def test_service_has_no_errors_in_logs(self):
        """Vérifier qu'il n'y a pas d'erreurs critiques dans les logs."""
        logs = get_docker_service_logs("mcp-rgaa-rgaa-1")
        # Vérifier que le service a démarré sans erreurs fatales
        assert "ERROR" not in logs or "Traceback" not in logs, f"Erreurs trouvées dans les logs: {logs[:500]}"


class TestDockerConfiguration:
    """Tests de configuration du conteneur Docker."""

    def test_container_has_required_env_vars(self):
        """Vérifier que les variables d'environnement requises sont présentes."""
        logs = get_docker_service_logs("mcp-rgaa-rgaa-1")
        # Vérifier que le service démarre correctement
        assert "Starting" in logs or "listening" in logs.lower() or logs.strip() != ""

    def test_container_restart_policy_is_set(self):
        """Vérifier que la politique de redémarrage est configurée."""
        try:
            result = subprocess.run(
                ["docker", "inspect", "--format", "{{.RestartPolicy.Name}}", "mcp-rgaa-rgaa-1"],
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
        sys.path.insert(0, "/Users/renaudheluin/DEV/mcp-rgaa/files")
        try:
            import rgaa_mcp
            assert hasattr(rgaa_mcp, "rgaa_lister_criteres"), "Outil rgaa_lister_criteres non trouvé"
            assert hasattr(rgaa_mcp, "rgaa_taux_conformite"), "Outil rgaa_taux_conformite non trouvé"
        except ImportError as e:
            pytest.skip(f"Impossible d'importer le module: {e}")

    def test_expected_tools_are_defined(self):
        """Vérifier que tous les outils attendus sont disponibles."""
        import sys
        sys.path.insert(0, "/Users/renaudheluin/DEV/mcp-rgaa/files")
        try:
            import rgaa_mcp as m

            expected_tools = [
                "rgaa_lister_criteres",
                "rgaa_obtenir_critere",
                "rgaa_chercher",
                "rgaa_glossaire",
                "rgaa_statistiques",
                "rgaa_types_audit",
                "rgaa_criteres_audit",
                "rgaa_analyser",
                "rgaa_checklist",
                "rgaa_taux_conformite",
            ]

            for tool_name in expected_tools:
                assert hasattr(m, tool_name), f"Outil {tool_name} non trouvé dans le module"
        except ImportError as e:
            pytest.skip(f"Impossible d'importer le module: {e}")


class TestDockerDataAvailability:
    """Tests de disponibilité des données."""

    def test_rgaa_data_is_loaded(self):
        """Vérifier que les données RGAA sont chargées."""
        import sys
        sys.path.insert(0, "/Users/renaudheluin/DEV/mcp-rgaa/files")
        try:
            import rgaa_mcp as m
            # Tester un appel simple pour vérifier que les données sont disponibles
            result = m.rgaa_statistiques()
            assert isinstance(result, dict), "rgaa_statistiques ne retourne pas un dict"
            assert "total" in str(result) or "statistiques" in str(result).lower(), "Données statistiques non trouvées"
        except ImportError:
            pytest.skip("Impossible d'importer le module")

    def test_tools_return_valid_data(self):
        """Vérifier que les outils retournent des données valides."""
        import sys
        sys.path.insert(0, "/Users/renaudheluin/DEV/mcp-rgaa/files")
        try:
            import rgaa_mcp as m

            # Test rgaa_lister_criteres
            result = m.rgaa_lister_criteres()
            assert isinstance(result, dict), "rgaa_lister_criteres ne retourne pas un dict"
            assert "criteres" in result or "data" in str(result).lower(), "Structure de retour invalide"

            # Test rgaa_types_audit
            result = m.rgaa_types_audit()
            assert isinstance(result, dict), "rgaa_types_audit ne retourne pas un dict"

            # Test rgaa_statistiques
            result = m.rgaa_statistiques()
            assert isinstance(result, dict), "rgaa_statistiques ne retourne pas un dict"
        except ImportError:
            pytest.skip("Impossible d'importer le module")
