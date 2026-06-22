# C1 — Lister les dimensions du référentiel

**Date:** 2026-04-10
**Statut:** Approuvé

## Contexte

Le MCP greenit expose déjà `lister_fiches` avec un filtre `lifecycle`, mais aucun outil ne liste les valeurs acceptées pour ces filtres. Un agent IA ne peut pas savoir quelles valeurs utiliser sans les deviner. Ce spec décrit deux outils qui exposent les dimensions textuelles du référentiel avec leurs labels enrichis et le nombre de fiches associées.

## Périmètre

Deux dimensions textuelles existent dans les données (`greenit_cache.json`) :

- **lifecycle** — 7 phases du cycle de vie
- **saved_resources** — 7 types de ressources sauvegardées

Les dimensions `scope` et `tiers` présentes dans `i18n/ui.ts` n'existent pas dans les données du cache — elles sont exclues.

## Outils

### `lister_lifecycles`

Retourne les phases du cycle de vie dans l'ordre numérique (déterminé par le préfixe de l'`id`).

**Retour :**
```json
[
  { "id": "1-specification", "label": "Spécification", "count": 4 },
  { "id": "2-concept",       "label": "Conception",    "count": 25 },
  { "id": "3-developement",  "label": "Développement", "count": 43 },
  { "id": "4-production",    "label": "Production",    "count": 27 },
  { "id": "5-utilization",   "label": "Utilisation",   "count": 16 },
  { "id": "6-support",       "label": "Support",       "count": 2  },
  { "id": "7-retirement",    "label": "Fin de vie",    "count": 2  }
]
```

Les `id` retournés sont directement utilisables comme valeur du filtre `lifecycle` dans `lister_fiches`.

### `lister_ressources`

Retourne les types de ressources sauvegardées, triés par count décroissant (les plus représentées en premier).

**Retour :**
```json
[
  { "id": "network",      "label": "Réseau",                              "count": 76 },
  { "id": "cpu",          "label": "Processeur",                          "count": 70 },
  { "id": "ram",          "label": "Mémoire vive",                        "count": 45 },
  { "id": "storage",      "label": "Stockage",                            "count": 37 },
  { "id": "requests",     "label": "Requêtes",                            "count": 34 },
  { "id": "electricity",  "label": "Consommation électrique",             "count": 3  },
  { "id": "ghg",          "label": "Émissions de gaz à effet de serre",   "count": 2  },
  { "id": "e-waste",      "label": "Déchets électroniques",               "count": 2  }
]
```

## Implémentation

### Labels

Les labels sont codés en dur dans le serveur, extraits de `i18n/ui.ts` (cnumr/best-practices). Pas de fetch externe au runtime.

Les labels **ne contiennent pas de numéro** — l'ordre est porté par le préfixe numérique de l'`id` pour `lifecycle`, et par le count pour `saved_resources`.

### Counts

Calculés au démarrage depuis les données en cache (`greenit_cache.json`), comme pour les autres outils existants.

### Filtre saved_resource dans lister_fiches

Vérifier si `lister_fiches` supporte déjà un filtre `saved_resource`. Si non, l'ajouter pour que les `id` retournés par `lister_ressources` soient directement utilisables comme filtres.

## Tests

- `lister_lifecycles` retourne exactement 7 entrées
- Les labels correspondent aux valeurs de l'i18n (sans numéro)
- Les counts correspondent aux données du cache
- `lister_ressources` retourne exactement 8 entrées, triées par count décroissant
- Les `id` de lifecycle sont compatibles avec le filtre `lifecycle` de `lister_fiches`
