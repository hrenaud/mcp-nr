import json
from pathlib import Path

_BASE_DIR = Path(__file__).parent
CACHE_FILE = _BASE_DIR / "rgaa_cache.json"
AUDIT_TYPES_FILE = _BASE_DIR / "audit_types.json"

_cache: dict | None = None
_audit_types_cache: dict | None = None


def charger_cache() -> dict:
    global _cache
    if _cache is None:
        with open(CACHE_FILE, encoding="utf-8") as f:
            _cache = json.load(f)
    return _cache


def charger_audit_types() -> dict:
    global _audit_types_cache
    if _audit_types_cache is None:
        with open(AUDIT_TYPES_FILE, encoding="utf-8") as f:
            _audit_types_cache = json.load(f)
    return _audit_types_cache
