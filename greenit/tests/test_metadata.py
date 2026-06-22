"""
Tests for the metadata resource and helper functions.
Follows TDD approach: tests first, then implementation.
"""
import sys
import json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "files"))

from data import (
    compter_fiches,
    compter_lifecycles,
    compter_ressources,
    calculer_taux_ecoindex_moyen,
)


def test_compter_fiches_returns_int():
    """Helper: compter_fiches should return an integer."""
    result = compter_fiches()
    assert isinstance(result, int)
    assert result >= 0


def test_compter_lifecycles_returns_int():
    """Helper: compter_lifecycles should return an integer."""
    result = compter_lifecycles()
    assert isinstance(result, int)
    assert result >= 0


def test_compter_ressources_returns_int():
    """Helper: compter_ressources should return an integer."""
    result = compter_ressources()
    assert isinstance(result, int)
    assert result >= 0


def test_calculer_taux_ecoindex_moyen_returns_float():
    """Helper: calculer_taux_ecoindex_moyen should return a float in [0.0, 100.0]."""
    result = calculer_taux_ecoindex_moyen()
    assert isinstance(result, float)
    assert 0.0 <= result <= 100.0


def test_compter_fiches_consistency():
    """Helper: compter_fiches should return consistent results."""
    result1 = compter_fiches()
    result2 = compter_fiches()
    assert result1 == result2


def test_compter_lifecycles_consistency():
    """Helper: compter_lifecycles should return consistent results."""
    result1 = compter_lifecycles()
    result2 = compter_lifecycles()
    assert result1 == result2


def test_compter_ressources_consistency():
    """Helper: compter_ressources should return consistent results."""
    result1 = compter_ressources()
    result2 = compter_ressources()
    assert result1 == result2


def test_calculer_taux_ecoindex_moyen_consistency():
    """Helper: calculer_taux_ecoindex_moyen should return consistent results."""
    result1 = calculer_taux_ecoindex_moyen()
    result2 = calculer_taux_ecoindex_moyen()
    assert result1 == result2


def test_calculer_taux_ecoindex_moyen_with_real_cache():
    """Validate calculation returns meaningful value based on actual cache data."""
    from data import charger_cache

    cache = charger_cache()
    fiches = cache

    if fiches:  # Only test if cache has data
        result = calculer_taux_ecoindex_moyen()
        # Verify: result should be in 1-5 range (environmental_impact scale)
        # and should not be 0.0 if fiches have non-zero impact values
        assert isinstance(result, float)
        assert 0.0 <= result <= 5.0, f"Expected result in [0.0, 5.0], got {result}"

        # Calculate expected average manually for verification
        impacts = [f.get("environmental_impact", 0.0) for f in fiches.values() if isinstance(f, dict)]
        if impacts:
            expected = round(sum(impacts) / len(impacts), 2)
            assert result == expected, f"Expected {expected}, got {result}"
