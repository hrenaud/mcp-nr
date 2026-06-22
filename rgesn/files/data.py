import json
from pathlib import Path

_BASE_DIR = Path(__file__).parent
CACHE_FILE = _BASE_DIR / "rgesn_cache.json"

_cache: dict | None = None


def charger_cache() -> dict:
    global _cache
    if _cache is None:
        with open(CACHE_FILE, encoding="utf-8") as f:
            _cache = json.load(f)
    return _cache
