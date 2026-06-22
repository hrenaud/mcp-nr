# B1 — `obtenir_checklist_audit`

**Date:** 2026-04-10
**Statut:** Approuvé

## Contexte

`auditer_url` crawle une URL et enrichit automatiquement les statuts de fiches. Mais avant de lancer un crawl, l'utilisateur peut vouloir obtenir la checklist complète des 115 fiches pour la remplir manuellement. Ce spec crée `obtenir_checklist_audit` — un outil MCP qui génère cette checklist vierge — et extrait la logique de construction dans une fonction interne partagée avec `auditer_url`.

## Architecture

Une fonction interne `_build_checklist(cache) -> dict` centralise la construction de la checklist. Elle est appelée par :

- `obtenir_checklist_audit` — retourne la checklist vierge directement
- `auditer_url` — utilise la checklist comme base, puis surcharge les statuts avec les auto-validations (A1) et calcule le score (A2)

Ce pattern suit l'existant (`_crawl`, `_build_report`).

## Outil MCP : `obtenir_checklist_audit`

Aucun paramètre. Retourne les 115 fiches avec `statut: "Non-testé"`.

### Structure de retour

```json
{
  "total": 115,
  "statuts_possibles": {
    "Conforme": "La valeur mesurée respecte la limite définie",
    "Non-conforme": "La valeur mesurée dépasse la limite définie",
    "Non-applicable": "La bonne pratique ne s'applique pas à ce contexte",
    "Indéterminé": "Impossible de déterminer sans inspection manuelle",
    "Non-testé": "Pas de valeur limite définie ou métrique non mesurée"
  },
  "fiches": [
    {
      "id": "RWEB_0047",
      "titre": "Limiter le nombre de requêtes HTTP",
      "lifecycle": "3-developement",
      "url": "https://rweb.greenit.fr/fr/fiches/0047",
      "validation_rule": "de requêtes HTTP",
      "max_value": "40",
      "valeur_mesuree": null,
      "statut": "Non-testé",
      "environmental_impact": 4,
      "priority_implementation": 4
    }
  ]
}
```

### Tri

Par `environmental_impact` décroissant — les fiches à fort impact en premier pour guider l'ordre des tests manuels.

## Fonction interne `_build_checklist`

```python
def _build_checklist(cache: dict) -> dict:
    """
    Build the base audit checklist from all 115 fiches.
    All fiches default to statut='Non-testé'.
    Used by obtenir_checklist_audit and auditer_url.
    """
```

Retourne le dict complet (total + statuts_possibles + fiches triées).

`auditer_url` appelle `_build_checklist`, puis itère sur `fiches` pour surcharger `statut` et `valeur_mesuree` là où les métriques crawlées permettent une auto-validation.

## Dépendances

- Dépend de A1 : `validation_rule` et `max_value` doivent être disponibles dans le cache
- `auditer_url` dépend de B1 pour sa section `audit_complet` (remplace la construction ad hoc de A2)

## Fichiers modifiés

- `files/checklist.py` (nouveau) — contient `_build_checklist` + `map_metrics_to_fiches` enrichie (logique A1 incluse)
- `files/audit_url.py` — conserve uniquement le crawl (`crawl`, `compute_ecoindex`, `detect_tracking`) ; importe `_build_checklist` depuis `checklist.py`
- `files/report.py` (nouveau) — contient `build_report` ; importe `_build_checklist` depuis `checklist.py`
- `files/greenit_mcp_final.py` — ajout de l'outil MCP `obtenir_checklist_audit` ; importe depuis `checklist.py` et `report.py`
- `tests/test_tools.py` — tests de `_build_checklist` et de l'outil MCP

## Tests

- `_build_checklist` retourne exactement 115 fiches
- Toutes les fiches ont `statut: "Non-testé"` et `valeur_mesuree: null`
- Triées par `environmental_impact` décroissant
- `obtenir_checklist_audit` retourne le même résultat que `_build_checklist`
- `auditer_url` utilise `_build_checklist` (pas de duplication de logique)
- Les statuts auto-validés dans `auditer_url` surchargent correctement les `"Non-testé"` de base
