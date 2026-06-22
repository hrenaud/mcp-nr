"""
Télécharge les données RGAA depuis GitHub et génère rgaa_cache.json.

Usage:
    python preparer_donnees.py --telecharger   # Fetch depuis GitHub
    python preparer_donnees.py --check         # Vérifie le cache existant
"""

import httpx
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

RGAA_CRITERES_URL = "https://raw.githubusercontent.com/DISIC/accessibilite.numerique.gouv.fr/main/RGAA/criteres.json"
RGAA_GLOSSAIRE_URL = "https://raw.githubusercontent.com/DISIC/accessibilite.numerique.gouv.fr/main/RGAA/glossaire.json"

CACHE_FILE = Path(__file__).parent / "rgaa_cache.json"

THEMES = {
    1: "Images",
    2: "Cadres",
    3: "Couleurs",
    4: "Multimédia",
    5: "Tableaux",
    6: "Liens",
    7: "Scripts",
    8: "Éléments obligatoires",
    9: "Structuration de l'information",
    10: "Présentation de l'information",
    11: "Formulaires",
    12: "Navigation",
    13: "Consultation",
}

# Thèmes pour lesquels une analyse automatique statique est possible
THEMES_AUTOMATISABLES = {1, 2, 5, 6, 8, 9, 11, 12}


def telecharger() -> None:
    print("Téléchargement des données RGAA...")
    try:
        with httpx.Client(timeout=30) as client:
            r_criteres = client.get(RGAA_CRITERES_URL)
            r_criteres.raise_for_status()
            r_glossaire = client.get(RGAA_GLOSSAIRE_URL)
            r_glossaire.raise_for_status()

        criteres_raw = r_criteres.json()
        glossaire_raw = r_glossaire.json()
    except httpx.HTTPError as e:
        print(f"Erreur réseau : {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"Erreur de parsing JSON : {e}", file=sys.stderr)
        sys.exit(1)

    criteres = _normaliser_criteres(criteres_raw)
    glossaire = _normaliser_glossaire(glossaire_raw)

    cache = {
        "meta": {
            "source": "DISIC/accessibilite.numerique.gouv.fr",
            "genere_le": datetime.now(timezone.utc).isoformat(),
            "nb_criteres": len(criteres),
            "nb_termes": len(glossaire),
        },
        "themes": THEMES,
        "themes_automatisables": sorted(THEMES_AUTOMATISABLES),
        "criteres": criteres,
        "glossaire": glossaire,
    }

    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)

    print(f"Cache généré : {CACHE_FILE}")
    print(f"  {len(criteres)} critères, {len(glossaire)} termes glossaire")


def _normaliser_criteres(raw: dict) -> dict:
    """
    Normalise le JSON GitHub en dict indexé par id (ex: "1.1").
    Structure GitHub : {"topics": [{"number": 1, "criteria": [{"criterium": {"number": 1, ...}}]}]}
    """
    result = {}
    for topic in raw.get("topics", []):
        theme_num = topic.get("number")
        if not theme_num:
            continue
        for item in topic.get("criteria", []):
            c = item.get("criterium", item)
            crit_num = c.get("number")
            if not crit_num:
                continue
            full_id = f"{theme_num}.{crit_num}"
            result[full_id] = {
                "id": full_id,
                "theme": theme_num,
                "titre": c.get("title", ""),
                "niveau": c.get("level", "A"),
                "automatisable": theme_num in THEMES_AUTOMATISABLES,
                "tests": c.get("tests", {}),
                "wcag": _extraire_wcag(c),
                "cas_particuliers": c.get("particularCases", []),
                "note_technique": c.get("technicalNotes", []),
            }
    return result


def _extraire_wcag(c: dict) -> list:
    refs = c.get("references", [])
    if not isinstance(refs, list):
        return []
    for ref in refs:
        if isinstance(ref, dict) and "wcag" in ref:
            wcag = ref["wcag"]
            if isinstance(wcag, list):
                return wcag
    return []


def _normaliser_glossaire(raw: dict) -> dict:
    """
    Normalise le glossaire en dict indexé par terme (minuscule).
    Structure GitHub : {"glossary": [{"title": "...", "body": "..."}]}
    """
    result = {}
    for item in raw.get("glossary", []):
        titre = item.get("title", "")
        if titre:
            result[titre.lower()] = {
                "terme": titre,
                "definition": item.get("body", ""),
                "exemples": item.get("examples", []),
            }
    return result


def check() -> None:
    if not CACHE_FILE.exists():
        print(f"Cache absent : {CACHE_FILE}")
        sys.exit(1)
    with open(CACHE_FILE, encoding="utf-8") as f:
        cache = json.load(f)
    meta = cache.get("meta", {})
    print(f"Cache OK — {meta.get('nb_criteres')} critères, généré le {meta.get('genere_le')}")


if __name__ == "__main__":
    if "--telecharger" in sys.argv:
        telecharger()
    elif "--check" in sys.argv:
        check()
    else:
        print(__doc__)
