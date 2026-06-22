# A2 — Score de conformité aux 115 BP GreenIT

**Date:** 2026-04-10
**Statut:** Approuvé

## Contexte

`auditer_url` produit un EcoIndex par page mais aucun score de conformité aux fiches du référentiel. Ce spec ajoute un score global de conformité et transforme le rapport en checklist d'audit complet couvrant les 115 fiches — permettant à l'utilisateur de tester et valider manuellement dans un second temps.

## Dépendances

- A2 dépend de A1 : les statuts et `maxValue` doivent être disponibles dans le cache et dans `map_metrics_to_fiches` avant d'implémenter A2.
- A2 dépend de B1 : la section `audit_complet` est construite via `_build_checklist` (définie dans B1). `auditer_url` appelle `_build_checklist` pour obtenir la base des 115 fiches, puis surcharge les statuts avec les auto-validations avant de calculer le score.

## Score de conformité

Calculé sur l'ensemble des 115 fiches du cache, indépendamment de celles matchées par le crawl.

```json
{
  "score_conformite": {
    "score_pct": 12.2,
    "conforme": 14,
    "non_conforme": 8,
    "non_applicable": 3,
    "indetermine": 5,
    "non_teste": 85,
    "total": 115
  }
}
```

`score_pct = round(conforme / 115 * 100, 1)`

`total` est toujours 115. Les fiches non matchées par le crawl ont `statut: "Non-testé"` et comptent dans `non_teste`.

## Section `audit_complet`

Le rapport inclut une section `audit_complet` listant les 115 fiches. C'est la vue exhaustive qui sert de checklist d'audit — l'utilisateur peut y renseigner les statuts manuellement pour les fiches non auto-validées.

### Structure de chaque fiche

```json
{
  "id": "RWEB_0047",
  "titre": "Limiter le nombre de requêtes HTTP",
  "lifecycle": "3-developement",
  "url": "https://rweb.greenit.fr/fr/fiches/0047",
  "validation_rule": "de requêtes HTTP",
  "max_value": "40",
  "valeur_mesuree": 35,
  "statut": "Conforme",
  "environmental_impact": 4,
  "priority_implementation": 4
}
```

- `valeur_mesuree` — renseignée si auto-validée (A1), `null` sinon
- `statut` — auto-assigné si possible, `"Non-testé"` par défaut
- `environmental_impact` et `priority_implementation` — valeurs du référentiel (1-5), pour guider la priorisation manuelle

### Tri des 115 fiches

1. `Non-conforme` en premier (action immédiate)
2. `Conforme`
3. `Indéterminé`
4. `Non-testé` — triés par `environmental_impact` décroissant (pour guider l'ordre des tests manuels)

## Coexistence avec `recommandations`

La section `recommandations` existante (top 10 fiches par occurrences) est conservée pour la vue rapide. `audit_complet` est complémentaire : vue exhaustive pour l'audit manuel.

## Format markdown

En markdown, `audit_complet` est rendu sous forme de tableau :

```
## Audit complet — 115 fiches

| ID | Titre | Lifecycle | Statut | Valeur mesurée | Max | Impact | Priorité |
|----|-------|-----------|--------|---------------|-----|--------|---------|
| RWEB_0047 | Limiter le nombre de requêtes HTTP | Développement | Conforme | 35 | 40 | 4 | 4 |
| RWEB_0009 | Éviter les animations JS/CSS | Développement | Non-testé | — | 2 | 3 | 3 |
...
```

## Persistance (D1)

`auditer_url` dans `greenit_mcp_final.py` accepte un paramètre `output_dir: str = "."` et écrit dans `{output_dir}/{YYYY-MM-DD}/` :

- `greenit-audit-{domaine}.json` — rapport JSON complet (structure ci-dessus)
- `greenit-audit-{domaine}.md` — rapport markdown
- `greenit-audit-{domaine}.html` — rapport HTML autonome (CSS embarqué)

`build_report` retourne toujours un dict JSON. L'écriture disque est la responsabilité de `auditer_url`, pas de `build_report`.

## Fichiers modifiés

- `files/report.py` (nouveau) — `build_report` : utilise `_build_checklist` (B1/`checklist.py`) pour `audit_complet`, puis calcule le score ; retourne un dict JSON. Contient aussi `render_html(data) -> str`
- `files/greenit_mcp_final.py` — `auditer_url` : ajout de `output_dir`, écriture JSON + markdown + HTML sur disque (D1)
- `tests/test_tools.py` — tests du score, de la structure `audit_complet`, et de l'écriture disque

## Tests

- `score_pct = round(conforme / 115 * 100, 1)`
- `total` toujours = 115
- `audit_complet` contient exactement 115 entrées
- Les fiches non matchées ont `statut: "Non-testé"` et `valeur_mesuree: null`
- Tri : Non-conforme avant Conforme avant Indéterminé avant Non-testé
- Les Non-testés sont triés par `environmental_impact` décroissant
- `environmental_impact` et `priority_implementation` présents sur toutes les fiches
- `auditer_url` avec `output_dir` crée `.json`, `.md` et `.html` dans `{output_dir}/{date}/`
