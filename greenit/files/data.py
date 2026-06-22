import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger("greenit-mcp")

_BASE_DIR = Path(__file__).parent
CACHE_FILE = str(_BASE_DIR / "greenit_cache.json")
METADATA_FILE = str(_BASE_DIR / "greenit_metadata.json")

_cache: Optional[dict] = None
_metadata: Optional[dict] = None


def charger_cache() -> dict:
    global _cache
    if _cache is None:
        if Path(CACHE_FILE).exists():
            try:
                with open(CACHE_FILE, "r", encoding="utf-8") as f:
                    _cache = json.load(f)
            except Exception as e:
                logger.error("Erreur lors du chargement du cache: %s", e)
                _cache = {}
        else:
            _cache = {}
    return _cache


def charger_metadata() -> dict:
    global _metadata
    if _metadata is None:
        if Path(METADATA_FILE).exists():
            try:
                with open(METADATA_FILE, "r", encoding="utf-8") as f:
                    _metadata = json.load(f)
            except Exception as e:
                logger.error("Erreur lors du chargement des métadonnées: %s", e)
                _metadata = {"languages": ["fr"], "versions": ["latest"]}
        else:
            _metadata = {"languages": ["fr"], "versions": ["latest"]}
    return _metadata


def sauvegarder_cache(data: dict) -> bool:
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.error("Erreur lors de la sauvegarde du cache: %s", e)
        return False


def sauvegarder_metadata(data: dict) -> bool:
    try:
        with open(METADATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.error("Erreur lors de la sauvegarde des métadonnées: %s", e)
        return False


# EcoIndex calculation (merged from ecoindex.py)
_QUANTILES_DOM = [
    0, 47, 75, 159, 233, 298, 358, 417, 476, 537, 603, 674,
    753, 843, 949, 1076, 1237, 1459, 1801, 2479, 594601,
]
_QUANTILES_REQ = [
    0, 2, 15, 25, 34, 42, 49, 56, 63, 70, 78, 86, 95,
    105, 117, 130, 147, 170, 205, 281, 3920,
]
_QUANTILES_SIZE = [
    0, 1.37, 144.7, 319.53, 479.46, 631.97, 783.38, 937.91,
    1098.62, 1265.47, 1448.32, 1648.27, 1876.08, 2142.06,
    2465.37, 2866.31, 3401.59, 4155.73, 5400.08, 8037.54, 223212.26,
]
_GRADES = [
    {"value": 80, "grade": "A"},
    {"value": 70, "grade": "B"},
    {"value": 55, "grade": "C"},
    {"value": 40, "grade": "D"},
    {"value": 25, "grade": "E"},
    {"value": 10, "grade": "F"},
    {"value": 0,  "grade": "G"},
]


def _compute_quantile(quantiles: list, value: float) -> float:
    for i in range(1, len(quantiles)):
        if value < quantiles[i]:
            return (i - 1) + (value - quantiles[i - 1]) / (quantiles[i] - quantiles[i - 1])
    return float(len(quantiles) - 1)


def calculer_ecoindex(dom: int, requests: int, size_kb: float) -> dict:
    """Calcule le score EcoIndex (0–100) et le grade (A–G)."""
    q_dom  = _compute_quantile(_QUANTILES_DOM, dom)
    q_req  = _compute_quantile(_QUANTILES_REQ, requests)
    q_size = _compute_quantile(_QUANTILES_SIZE, size_kb)
    score  = 100 - 5 * (3 * q_dom + 2 * q_req + q_size) / 6
    score  = max(0.0, min(100.0, score))
    grade  = "G"
    for g in _GRADES:
        if score > g["value"]:
            grade = g["grade"]
            break
    return {"score": round(score, 2), "grade": grade}


def compter_fiches() -> int:
    """Count total number of fiches in greenit_cache.json.

    Returns the length of the fiches dictionary. Returns 0 if cache is empty.
    """
    cache = charger_cache()
    return len(cache)


def compter_lifecycles() -> int:
    """Count total number of unique lifecycle phases.

    Iterates through all fiches and collects unique 'lifecycle' values.
    Returns 0 if no fiches exist.
    """
    cache = charger_cache()
    lifecycles = set()
    for fiche in cache.values():
        lc = fiche.get("lifecycle")
        if lc:
            lifecycles.add(lc)
    return len(lifecycles)


def compter_ressources() -> int:
    """Count total number of unique saved resource types.

    Iterates through all fiches and collects unique values from 'saved_resources' field.
    Returns 0 if no fiches exist.
    """
    cache = charger_cache()
    ressources = set()
    for fiche in cache.values():
        for r in fiche.get("saved_resources", []):
            ressources.add(r)
    return len(ressources)


def calculer_taux_ecoindex_moyen() -> float:
    """Calculate average environmental impact score from all fiches.

    Computes the mean of 'environmental_impact' (1-5 scale) across all fiches in cache.
    This represents the average impact level of the recommendations.
    Returns 0.0 if no fiches exist.
    """
    cache = charger_cache()
    if not cache:
        return 0.0
    total_impact = sum(f.get("environmental_impact", 0.0) for f in cache.values() if isinstance(f, dict))
    return round(total_impact / len(cache), 2)
