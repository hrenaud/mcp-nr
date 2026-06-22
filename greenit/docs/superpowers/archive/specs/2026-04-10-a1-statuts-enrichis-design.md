# A1 — Statuts enrichis dans auditer_url

**Date:** 2026-04-10
**Statut:** Approuvé

## Contexte

Actuellement, `auditer_url` retourne une liste de fiches "applicables" sans aucun verdict. L'agent IA ne sait pas si une bonne pratique est respectée, non respectée, ou non applicable. Ce spec enrichit chaque fiche du rapport avec un statut d'audit, sa règle de validation, et la valeur maximale autorisée (`maxValue`). Quand la métrique crawlée est disponible, le statut est assigné automatiquement.

## Problème de cache (bug à corriger en premier)

Le parser MDX maison dans `preparer_donnees_final.py` (ligne 172-174) traite les éléments de liste comme des strings simples. Pour les fiches, `validations` est un tableau d'objets YAML :

```yaml
validations:
  - rule: de requêtes HTTP
    maxValue: '40'
```

Le parser capture `"rule: de requêtes HTTP"` comme string et ignore `maxValue: '40'` (indentation 4 espaces non couverte). Résultat : le cache perd `maxValue` sur toutes les fiches.

**Fix :** détecter les éléments de liste qui contiennent `key: value` (objets imbriqués) et les accumuler correctement. Régénérer `greenit_cache.json` après correction.

## Statuts possibles

| Statut | Signification |
|--------|--------------|
| `Conforme` | La valeur mesurée est ≤ maxValue |
| `Non-conforme` | La valeur mesurée dépasse maxValue |
| `Non-applicable` | La bonne pratique ne s'applique pas à ce contexte |
| `Indéterminé` | La métrique n'est pas automatiquement mesurable |
| `Non-testé` | Pas de maxValue ou métrique non disponible dans le crawl |

## Structure de fiche enrichie

`map_metrics_to_fiches` dans `audit_url.py` enrichit chaque fiche :

```json
{
  "id": "RWEB_0047",
  "titre": "Limiter le nombre de requêtes HTTP",
  "environmental_impact": 4,
  "priority_implementation": 4,
  "url": "https://rweb.greenit.fr/fr/fiches/0047",
  "validation_rule": "de requêtes HTTP",
  "max_value": "40",
  "statut": "Conforme"
}
```

### Extraction de `validation_rule`

Source : `fiche["validations"][0]` (objet après correction du cache).

- Champ `rule` de l'objet → `validation_rule`
- Si absent ou vide → `null`

### Extraction de `max_value`

Source : `fiche["validations"][0]["maxValue"]` après correction du cache.

- Si absent → `null`

## Auto-validation

Quand une fiche a un `max_value` numérique ET que la métrique crawlée correspondante est disponible, le statut est assigné automatiquement.

### Table de mapping fiche → métrique crawlée

| Fiche | Règle | maxValue | Métrique crawlée |
|-------|-------|----------|------------------|
| RWEB_0047 | requêtes HTTP | 40 | `requests` |
| RWEB_0032 | polices téléchargées | 2 | `len(fonts)` |

Pour toutes les autres fiches : `statut: "Non-testé"` (maxValue absent ou métrique non disponible dans le crawl).

### Logique d'assignation

```
si max_value est numérique ET métrique disponible:
    si métrique <= max_value → "Conforme"
    sinon → "Non-conforme"
sinon:
    "Non-testé"
```

Les `maxValue` de type plage (`"3 et 10"`) restent affichées mais ne déclenchent pas d'auto-validation (statut `"Non-testé"`).

## Légende dans le rapport

Le rapport (JSON et markdown) inclut un bloc `statuts_possibles` en tête.

**JSON :**
```json
{
  "statuts_possibles": {
    "Conforme": "La valeur mesurée respecte la limite définie",
    "Non-conforme": "La valeur mesurée dépasse la limite définie",
    "Non-applicable": "La bonne pratique ne s'applique pas à ce contexte",
    "Indéterminé": "Impossible de déterminer sans inspection manuelle",
    "Non-testé": "Pas de valeur limite définie ou métrique non mesurée"
  }
}
```

**Markdown :** tableau équivalent en tête de rapport.

## Fichiers modifiés

- `files/preparer_donnees_final.py` — parser les objets `{rule, maxValue}` dans les listes YAML imbriquées
- `files/greenit_cache.json` — régénéré après correction du parser
- `files/checklist.py` (nouveau) — `map_metrics_to_fiches` enrichie (ajout de `validation_rule`, `max_value`, `statut`) + mapping fiche→métrique pour auto-validation
- `tests/test_tools.py` — tests de parsing, auto-validation, structure du rapport

## Tests

- Le parser MDX extrait correctement `{rule, maxValue}` depuis un frontmatter avec objet imbriqué
- `map_metrics_to_fiches` retourne `validation_rule` et `max_value` sur chaque fiche
- RWEB_0047 avec `requests=35` → `statut: "Conforme"` ; avec `requests=50` → `statut: "Non-conforme"`
- RWEB_0032 avec `fonts=["Arial"]` → `statut: "Conforme"` ; avec 3 polices → `statut: "Non-conforme"`
- Fiche sans maxValue → `statut: "Non-testé"`, `max_value: null`
- Le rapport JSON contient le bloc `statuts_possibles`
- Le rapport markdown contient la légende des statuts
