import sys
import json
from pathlib import Path
import pytest
from unittest.mock import patch, MagicMock, mock_open
sys.path.insert(0, str(Path(__file__).parent.parent / "files"))

from data import (
    charger_cache, calculer_ecoindex, _compute_quantile,
    sauvegarder_cache,
    compter_fiches, compter_lifecycles, compter_ressources, calculer_taux_ecoindex_moyen,
    CACHE_FILE,
)


class TestData:
    def test_charger_cache_retourne_dict(self):
        cache = charger_cache()
        assert isinstance(cache, dict)

    def test_charger_cache_non_vide(self):
        cache = charger_cache()
        assert len(cache) > 0

    def test_charger_cache_cache_en_memoire(self):
        c1 = charger_cache()
        c2 = charger_cache()
        assert c1 is c2


class TestComputeQuantile:
    """Tests for _compute_quantile helper function."""

    def test_compute_quantile_value_at_start(self):
        """Test value at first quantile boundary."""
        quantiles = [0, 100, 200, 300]
        assert _compute_quantile(quantiles, 0) == 0.0

    def test_compute_quantile_value_at_exact_boundary(self):
        """Test value exactly at a quantile boundary."""
        quantiles = [0, 100, 200, 300]
        assert _compute_quantile(quantiles, 100) == 1.0

    def test_compute_quantile_value_between_boundaries(self):
        """Test value between two quantile boundaries (interpolation)."""
        quantiles = [0, 100, 200, 300]
        # Value 50 should interpolate to 0.5 (halfway between 0 and 100)
        result = _compute_quantile(quantiles, 50)
        assert abs(result - 0.5) < 0.01

    def test_compute_quantile_value_beyond_last_boundary(self):
        """Test value exceeding the last quantile boundary."""
        quantiles = [0, 100, 200, 300]
        # Value 500 should return len(quantiles) - 1 = 3
        assert _compute_quantile(quantiles, 500) == 3.0

    def test_compute_quantile_large_interpolation_range(self):
        """Test interpolation with a large gap between quantiles."""
        quantiles = [0, 1000, 2000]
        # Value 1500 should interpolate to 1.5 (halfway between index 1 and 2)
        result = _compute_quantile(quantiles, 1500)
        assert abs(result - 1.5) < 0.01

    def test_compute_quantile_small_interpolation_range(self):
        """Test interpolation with a small gap between quantiles."""
        quantiles = [0, 2, 4, 6]
        # Value 3 should interpolate to 1.5 (halfway between 2 and 4)
        result = _compute_quantile(quantiles, 3)
        assert abs(result - 1.5) < 0.01


class TestEcoIndexCalculation:
    """Tests for calculer_ecoindex function."""

    def test_ecoindex_minimum_inputs(self):
        """Test with minimum inputs (0, 0, 0) should return Grade A (best)."""
        result = calculer_ecoindex(0, 0, 0)
        assert isinstance(result, dict)
        assert "score" in result
        assert "grade" in result
        assert result["grade"] == "A"
        assert result["score"] == 100.0

    def test_ecoindex_maximum_inputs(self):
        """Test with maximum inputs should return Grade G (worst)."""
        result = calculer_ecoindex(594601, 3920, 223212.26)
        assert isinstance(result, dict)
        assert result["grade"] == "G"
        assert result["score"] == 0.0

    def test_ecoindex_score_is_clamped_min(self):
        """Test that score never goes below 0."""
        # Very high values should still have score >= 0
        result = calculer_ecoindex(1000000, 1000000, 1000000.0)
        assert result["score"] >= 0.0
        assert result["score"] <= 100.0

    def test_ecoindex_score_is_clamped_max(self):
        """Test that score never exceeds 100."""
        result = calculer_ecoindex(0, 0, 0)
        assert result["score"] <= 100.0
        assert result["score"] >= 0.0

    def test_ecoindex_score_rounding(self):
        """Test that score is rounded to 2 decimal places."""
        result = calculer_ecoindex(100, 25, 200.0)
        assert isinstance(result["score"], float)
        # Check it's rounded to at most 2 decimal places
        decimal_places = len(str(result["score"]).split('.')[-1]) if '.' in str(result["score"]) else 0
        assert decimal_places <= 2

    @pytest.mark.parametrize("grade,dom,requests,size_kb,min_score,max_score", [
        ("A", 50, 40, 900.0, 80.01, 100.0),
        ("B", 150, 40, 4900.0, 70.01, 80.0),
        ("C", 250, 100, 2100.0, 55.01, 70.0),
        ("D", 450, 310, 100.0, 40.01, 55.0),
        ("E", 950, 190, 1700.0, 25.01, 40.0),
        ("F", 1450, 340, 3700.0, 10.01, 25.0),
        ("G", 1950, 250, 4900.0, 0.0, 10.0),
    ])
    def test_ecoindex_grade_boundaries(self, grade, dom, requests, size_kb, min_score, max_score):
        """Test each grade transition boundary with realistic inputs."""
        result = calculer_ecoindex(dom, requests, size_kb)
        assert min_score < result["score"] <= max_score, f"Expected score in ({min_score}, {max_score}], got {result['score']}"
        assert result["grade"] == grade, f"Expected grade {grade}, got {result['grade']}"

    def test_ecoindex_return_structure(self):
        """Test that return value has correct structure."""
        result = calculer_ecoindex(200, 50, 400.0)
        assert isinstance(result, dict)
        assert len(result) == 2
        assert "score" in result
        assert "grade" in result
        assert isinstance(result["score"], float)
        assert isinstance(result["grade"], str)
        assert result["grade"] in ["A", "B", "C", "D", "E", "F", "G"]

    def test_ecoindex_realistic_good_page(self):
        """Test with realistic good page metrics."""
        # A typical good page: 500 DOM nodes, 30 requests, 800 KB
        result = calculer_ecoindex(500, 30, 800.0)
        assert result["grade"] in ["A", "B", "C"]  # Should be decent
        assert result["score"] > 40

    def test_ecoindex_realistic_bad_page(self):
        """Test with realistic bad page metrics."""
        # A typical bad page: 3000 DOM nodes, 150 requests, 5000 KB
        result = calculer_ecoindex(3000, 150, 5000.0)
        assert result["grade"] in ["D", "E", "F", "G"]  # Should be poor
        assert result["score"] < 60

    def test_ecoindex_medium_values(self):
        """Test with medium-range inputs."""
        result = calculer_ecoindex(400, 50, 1000.0)
        assert isinstance(result["score"], float)
        assert 0 <= result["score"] <= 100
        assert result["grade"] in ["A", "B", "C", "D", "E", "F", "G"]


class TestCacheIOErrors:
    """Tests for cache loading and saving with I/O failures."""

    def test_charger_cache_file_not_found_exception(self):
        """Test cache loading when file doesn't exist (no exception)."""
        # With Path.exists() returning False, should return empty dict
        with patch('data.Path') as mock_path_class:
            mock_path_inst = MagicMock()
            mock_path_inst.exists.return_value = False
            mock_path_class.return_value = mock_path_inst

            # Reset global cache to force reload
            import data
            data._cache = None

            cache = charger_cache()
            assert cache == {}

    def test_charger_cache_corrupted_json(self):
        """Test cache loading when JSON is corrupted."""
        import data

        with patch('builtins.open', mock_open(read_data='{"invalid json')):
            with patch('data.Path') as mock_path_class:
                mock_path_inst = MagicMock()
                mock_path_inst.exists.return_value = True
                mock_path_class.return_value = mock_path_inst

                data._cache = None
                with patch('data.logger') as mock_logger:
                    cache = charger_cache()
                    assert cache == {}
                    mock_logger.error.assert_called()

    def test_charger_cache_permission_error(self):
        """Test cache loading when file read permission denied."""
        import data

        with patch('builtins.open', side_effect=PermissionError("Permission denied")):
            with patch('data.Path') as mock_path_class:
                mock_path_inst = MagicMock()
                mock_path_inst.exists.return_value = True
                mock_path_class.return_value = mock_path_inst

                data._cache = None
                with patch('data.logger') as mock_logger:
                    cache = charger_cache()
                    assert cache == {}
                    mock_logger.error.assert_called()

    def test_sauvegarder_cache_write_success(self):
        """Test successful cache save."""
        import data

        with patch('builtins.open', mock_open()):
            result = sauvegarder_cache({"test": "data"})
            assert result is True

    def test_sauvegarder_cache_write_failure_permission(self):
        """Test cache save with permission error."""
        import data

        with patch('builtins.open', side_effect=PermissionError("Read-only file system")):
            with patch('data.logger') as mock_logger:
                result = sauvegarder_cache({"test": "data"})
                assert result is False
                mock_logger.error.assert_called()

    def test_sauvegarder_cache_write_failure_io_error(self):
        """Test cache save with I/O error."""
        import data

        with patch('builtins.open', side_effect=IOError("Disk full")):
            with patch('data.logger') as mock_logger:
                result = sauvegarder_cache({"test": "data"})
                assert result is False
                mock_logger.error.assert_called()

    def test_sauvegarder_cache_write_failure_oserror(self):
        """Test cache save with OS error."""
        import data

        with patch('builtins.open', side_effect=OSError("Path too long")):
            with patch('data.logger') as mock_logger:
                result = sauvegarder_cache({"test": "data"})
                assert result is False
                mock_logger.error.assert_called()


class TestCounterEdgeCases:
    """Tests for counter functions with empty cache."""

    def test_compter_fiches_empty_cache(self):
        """Test counting fiches with empty cache."""
        import data

        with patch('data.charger_cache', return_value={}):
            count = compter_fiches()
            assert count == 0

    def test_compter_fiches_non_empty(self):
        """Test counting fiches with populated cache."""
        import data

        test_cache = {"fiches": {
            "fiche1": {"title": "Fiche 1"},
            "fiche2": {"title": "Fiche 2"},
            "fiche3": {"title": "Fiche 3"},
        }}
        with patch('data.charger_cache', return_value=test_cache):
            count = compter_fiches()
            assert count == 3

    def test_compter_lifecycles_empty_cache(self):
        """Test counting lifecycles with empty cache."""
        import data

        with patch('data.charger_cache', return_value={}):
            count = compter_lifecycles()
            assert count == 0

    def test_compter_lifecycles_single_lifecycle(self):
        """Test counting lifecycles with single unique value."""
        import data

        test_cache = {"fiches": {
            "fiche1": {"lifecycle": "design"},
            "fiche2": {"lifecycle": "design"},
        }}
        with patch('data.charger_cache', return_value=test_cache):
            count = compter_lifecycles()
            assert count == 1

    def test_compter_lifecycles_multiple_lifecycles(self):
        """Test counting lifecycles with multiple unique values."""
        import data

        test_cache = {"fiches": {
            "fiche1": {"lifecycle": "design"},
            "fiche2": {"lifecycle": "development"},
            "fiche3": {"lifecycle": "deployment"},
        }}
        with patch('data.charger_cache', return_value=test_cache):
            count = compter_lifecycles()
            assert count == 3

    def test_compter_lifecycles_missing_lifecycle(self):
        """Test counting lifecycles when some fiches lack lifecycle field."""
        import data

        test_cache = {"fiches": {
            "fiche1": {"lifecycle": "design"},
            "fiche2": {"title": "No lifecycle"},
        }}
        with patch('data.charger_cache', return_value=test_cache):
            count = compter_lifecycles()
            assert count == 1

    def test_compter_ressources_empty_cache(self):
        """Test counting resources with empty cache."""
        import data

        with patch('data.charger_cache', return_value={}):
            count = compter_ressources()
            assert count == 0

    def test_compter_ressources_single_resource(self):
        """Test counting resources with single unique resource."""
        import data

        test_cache = {"fiches": {
            "fiche1": {"saved_resources": ["cpu"]},
            "fiche2": {"saved_resources": ["cpu"]},
        }}
        with patch('data.charger_cache', return_value=test_cache):
            count = compter_ressources()
            assert count == 1

    def test_compter_ressources_multiple_resources(self):
        """Test counting resources with multiple unique types."""
        import data

        test_cache = {"fiches": {
            "fiche1": {"saved_resources": ["cpu", "memory"]},
            "fiche2": {"saved_resources": ["network"]},
            "fiche3": {"saved_resources": ["cpu"]},
        }}
        with patch('data.charger_cache', return_value=test_cache):
            count = compter_ressources()
            assert count == 3

    def test_compter_ressources_missing_field(self):
        """Test counting resources when field is missing."""
        import data

        test_cache = {"fiches": {
            "fiche1": {"saved_resources": ["cpu"]},
            "fiche2": {"title": "No resources"},
        }}
        with patch('data.charger_cache', return_value=test_cache):
            count = compter_ressources()
            assert count == 1

    def test_compter_ressources_empty_resource_list(self):
        """Test counting resources when resource list is empty."""
        import data

        test_cache = {"fiches": {
            "fiche1": {"saved_resources": []},
            "fiche2": {"saved_resources": ["cpu"]},
        }}
        with patch('data.charger_cache', return_value=test_cache):
            count = compter_ressources()
            assert count == 1


class TestEcoIndexAverageEdgeCases:
    """Tests for EcoIndex average calculation with edge cases."""

    def test_calculer_taux_ecoindex_moyen_empty_cache(self):
        """Test average EcoIndex with empty cache."""
        import data

        with patch('data.charger_cache', return_value={}):
            avg = calculer_taux_ecoindex_moyen()
            assert avg == 0.0

    def test_calculer_taux_ecoindex_moyen_single_fiche(self):
        """Test average EcoIndex with single fiche."""
        import data

        test_cache = {"fiches": {"fiche1": {"environmental_impact": 3.5}}}
        with patch('data.charger_cache', return_value=test_cache):
            avg = calculer_taux_ecoindex_moyen()
            assert avg == 3.5

    def test_calculer_taux_ecoindex_moyen_multiple_fiches(self):
        """Test average EcoIndex with multiple fiches."""
        import data

        test_cache = {"fiches": {
            "fiche1": {"environmental_impact": 2.0},
            "fiche2": {"environmental_impact": 4.0},
            "fiche3": {"environmental_impact": 3.0},
        }}
        with patch('data.charger_cache', return_value=test_cache):
            avg = calculer_taux_ecoindex_moyen()
            assert avg == 3.0

    def test_calculer_taux_ecoindex_moyen_missing_impact_field(self):
        """Test average EcoIndex when impact field is missing."""
        import data

        test_cache = {"fiches": {
            "fiche1": {"environmental_impact": 3.0},
            "fiche2": {"title": "No impact"},
        }}
        with patch('data.charger_cache', return_value=test_cache):
            avg = calculer_taux_ecoindex_moyen()
            # Average of [3.0, 0.0] = 1.5
            assert avg == 1.5

    def test_calculer_taux_ecoindex_moyen_zero_impact(self):
        """Test average EcoIndex with zero values."""
        import data

        test_cache = {"fiches": {
            "fiche1": {"environmental_impact": 0.0},
            "fiche2": {"environmental_impact": 0.0},
        }}
        with patch('data.charger_cache', return_value=test_cache):
            avg = calculer_taux_ecoindex_moyen()
            assert avg == 0.0

    def test_calculer_taux_ecoindex_moyen_max_impact(self):
        """Test average EcoIndex with maximum values."""
        import data

        test_cache = {"fiches": {
            "fiche1": {"environmental_impact": 5.0},
            "fiche2": {"environmental_impact": 5.0},
        }}
        with patch('data.charger_cache', return_value=test_cache):
            avg = calculer_taux_ecoindex_moyen()
            assert avg == 5.0

    def test_calculer_taux_ecoindex_moyen_rounding(self):
        """Test that average EcoIndex is rounded to 2 decimals."""
        import data

        test_cache = {"fiches": {
            "fiche1": {"environmental_impact": 1.111},
            "fiche2": {"environmental_impact": 2.222},
        }}
        with patch('data.charger_cache', return_value=test_cache):
            avg = calculer_taux_ecoindex_moyen()
            # (1.111 + 2.222) / 2 = 1.6665 -> rounds to 1.67
            assert avg == 1.67



class TestComputeQuantileBoundaries:
    """Additional boundary tests for _compute_quantile."""

    def test_compute_quantile_exact_max_quantile(self):
        """Test when value exactly equals maximum quantile."""
        quantiles = [0, 100, 200, 300]
        result = _compute_quantile(quantiles, 300)
        assert result == 3.0

    def test_compute_quantile_just_above_max(self):
        """Test when value is just above maximum quantile."""
        quantiles = [0, 100, 200, 300]
        result = _compute_quantile(quantiles, 301)
        assert result == 3.0

    def test_compute_quantile_far_above_max(self):
        """Test when value is far above maximum quantile."""
        quantiles = [0, 100, 200, 300]
        result = _compute_quantile(quantiles, 1000)
        assert result == 3.0

    def test_compute_quantile_negative_value(self):
        """Test with negative input value (edge case)."""
        quantiles = [0, 100, 200, 300]
        # Should interpolate to negative when value < first quantile
        result = _compute_quantile(quantiles, -50)
        # -50 to 0 out of 0 to 100 range = -0.5
        assert result == -0.5

    def test_compute_quantile_float_values(self):
        """Test with floating point quantile values."""
        quantiles = [0.0, 100.5, 200.7, 300.2]
        result = _compute_quantile(quantiles, 150.6)
        # Should interpolate between 100.5 and 200.7
        assert 1.0 < result < 2.0


def test_charger_cache_concurrent():
    """#16 — accès concurrent : tous les threads partagent le même objet cache."""
    import threading
    import data
    data._cache = None
    results = []

    def w():
        results.append(data.charger_cache())

    ts = [threading.Thread(target=w) for _ in range(8)]
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    first = results[0]
    assert all(r is first for r in results)
