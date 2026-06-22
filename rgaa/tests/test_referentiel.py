# tests/test_referentiel.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "files"))

import pytest
import rgaa_mcp as m
from fastmcp.exceptions import ToolError


class TestListerCriteres:
    def test_tous_les_criteres(self):
        result = m.rgaa_lister_criteres()
        assert result["total"] == 106
        assert len(result["criteres"]) == 106

    def test_filtrer_par_theme(self):
        result = m.rgaa_lister_criteres(theme=1)
        assert result["total"] > 0
        assert all(c["theme"] == 1 for c in result["criteres"])

    def test_theme_inexistant(self):
        """Verify that invalid themes raise ToolError."""
        with pytest.raises(ToolError) as exc_info:
            m.rgaa_lister_criteres(theme=99)
        assert "invalide" in str(exc_info.value).lower() or "99" in str(exc_info.value)


class TestObtenir:
    def test_critere_valide(self):
        result = m.rgaa_obtenir_critere("1.1")
        assert result["id"] == "1.1"
        assert result["theme"] == 1
        assert "titre" in result
        assert "tests" in result
        assert "wcag" in result

    def test_critere_inexistant(self):
        """Verify that invalid criteria IDs raise ToolError."""
        with pytest.raises(ToolError) as exc_info:
            m.rgaa_obtenir_critere("99.99")
        assert "99.99" in str(exc_info.value) or "n'existe pas" in str(exc_info.value).lower()


class TestChercher:
    def test_chercher_dans_criteres(self):
        result = m.rgaa_chercher(query="image", scope=["criteres"])
        assert len(result["criteres"]) > 0
        assert result["termes_glossaire"] == []

    def test_chercher_dans_glossaire(self):
        result = m.rgaa_chercher(query="alternative", scope=["glossaire"])
        assert len(result["termes_glossaire"]) > 0

    def test_chercher_partout(self):
        result = m.rgaa_chercher(query="image")
        assert len(result["criteres"]) > 0


class TestGlossaire:
    def test_terme_existant(self):
        result = m.rgaa_glossaire(terme="image")
        assert "terme" in result or "erreur" in result

    def test_terme_inexistant(self):
        """Verify that nonexistent glossary terms raise ToolError."""
        with pytest.raises(ToolError) as exc_info:
            m.rgaa_glossaire(terme="zxqwerty123")
        assert "zxqwerty123" in str(exc_info.value) or "n'existe pas" in str(exc_info.value).lower()


class TestStatistiques:
    def test_structure(self):
        result = m.rgaa_statistiques()
        assert "total_criteres" in result
        assert result["total_criteres"] == 106
        assert "par_theme" in result
        assert "automatisables" in result
        assert "manuels" in result
