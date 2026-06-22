import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "files"))

from data import calculer_ecoindex


class TestEcoIndex:
    def test_score_max_vide(self):
        result = calculer_ecoindex(0, 0, 0.0)
        assert result["score"] == 100.0
        assert result["grade"] == "A"

    def test_score_min_tres_lourd(self):
        result = calculer_ecoindex(594601, 3920, 223212.26)
        assert result["score"] == 0.0
        assert result["grade"] == "G"

    def test_score_intermediaire(self):
        result = calculer_ecoindex(450, 38, 280.0)
        data = result
        assert 0.0 <= data["score"] <= 100.0
        assert data["grade"] in ("A", "B", "C", "D", "E", "F", "G")

    def test_retourne_dict_score_grade(self):
        result = calculer_ecoindex(100, 20, 150.0)
        assert "score" in result
        assert "grade" in result
        assert isinstance(result["score"], float)
        assert isinstance(result["grade"], str)

    def test_grade_a_above_80(self):
        result = calculer_ecoindex(0, 0, 0.0)
        assert result["grade"] == "A"
        assert result["score"] > 80

    def test_score_clamp_0_100(self):
        result = calculer_ecoindex(999999, 999999, 999999.0)
        assert result["score"] == 0.0
