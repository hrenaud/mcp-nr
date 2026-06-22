"""
Script de préparation des données RGESN.

Usage :
  python preparer_donnees.py

Met à jour rgesn_cache.json en complétant les champs
objectif/mise_en_oeuvre/moyen_de_controle à partir du PDF RGESN 2024.

Le PDF officiel est disponible ici :
https://www.arcep.fr/uploads/tx_gspublication/referentiel_general_ecoconception_des_services_numeriques_version_2024.pdf

État actuel :
  - Thème 1 (Stratégie) : données complètes
  - Thèmes 2-9 : question + métadonnées uniquement (objectif/mise_en_oeuvre/moyen_de_controle vides)
"""

import json
from pathlib import Path

CACHE_FILE = Path(__file__).parent / "rgesn_cache.json"


def charger() -> dict:
    with open(CACHE_FILE, encoding="utf-8") as f:
        return json.load(f)


def sauvegarder(data: dict) -> None:
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Cache mis à jour : {CACHE_FILE}")


def mettre_a_jour_critere(data: dict, critere_id: str, **champs) -> None:
    if critere_id not in data["criteres"]:
        raise KeyError(f"Critère '{critere_id}' introuvable")
    data["criteres"][critere_id].update(champs)


if __name__ == "__main__":
    data = charger()
    nb_vides = sum(
        1 for c in data["criteres"].values()
        if not c.get("objectif")
    )
    total = len(data["criteres"])
    complets = total - nb_vides
    print(f"RGESN cache : {total} critères ({complets} complets, {nb_vides} à compléter)")
    print("Pour compléter, appeler mettre_a_jour_critere() dans ce script avec les données du PDF.")
