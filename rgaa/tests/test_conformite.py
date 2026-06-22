import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "files"))

import pytest
import rgaa_mcp as m
from fastmcp.exceptions import ToolError


class TestTauxConformite:
    def test_calcul_simple(self):
        resultats = {"1.1": "C", "1.2": "NC", "1.3": "NA"}
        r = m.rgaa_taux_conformite(resultats)
        assert r["nb_conformes"] == 1
        assert r["nb_non_conformes"] == 1
        assert r["nb_non_applicables"] == 1
        assert r["criteres_evalues"] == 2
        assert r["taux"] == 50.0

    def test_taux_100(self):
        resultats = {"1.1": "C", "1.2": "C", "2.1": "NA"}
        r = m.rgaa_taux_conformite(resultats)
        assert r["taux"] == 100.0

    def test_taux_0(self):
        resultats = {"1.1": "NC", "1.2": "NC"}
        r = m.rgaa_taux_conformite(resultats)
        assert r["taux"] == 0.0

    def test_tous_na(self):
        """Verify that all NA results are flagged (no testable criteria)."""
        resultats = {"1.1": "NA", "1.2": "NA"}
        # When all criteria are NA, there are no evaluable criteria
        # This may either return 0 taux or raise an error depending on implementation
        r = m.rgaa_taux_conformite(resultats)
        # Should return valid result with 0 evaluated criteria
        assert r["criteres_evalues"] == 0

    def test_valeur_invalide(self):
        """Verify invalid statut raises ToolError."""
        resultats = {"1.1": "INVALID"}
        with pytest.raises(ToolError) as exc_info:
            m.rgaa_taux_conformite(resultats)
        assert "invalides" in str(exc_info.value).lower() or "INVALID" in str(exc_info.value)

    def test_arrondi(self):
        resultats = {str(i): ("C" if i % 3 == 0 else "NC") for i in range(1, 4)}
        r = m.rgaa_taux_conformite(resultats)
        assert isinstance(r["taux"], float)
