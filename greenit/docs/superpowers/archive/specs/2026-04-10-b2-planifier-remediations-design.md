# B2 — `planifier_remediations`

**Date:** 2026-04-10
**Statut:** Approuvé

## Contexte et workflow

Le workflow d'audit GreenIT est en 3 étapes :

1. **`auditer_url`** — crawl initial, rapport avec statuts auto-assignés
2. Corrections manuelles par l'utilisateur
3. **`planifier_remediations(rapport)`** — re-crawl de vérification + plan de remédiation pour ce qui reste

Ce spec couvre l'étape 3 : `planifier_remediations` prend le rapport de l'étape 1, re-crawle automatiquement les pages listées dans `rapport["pages"]` pour vérifier les corrections applicables en front-end. Ce qui ne peut pas être testé en front reste à validation manuelle.

## Input

Chemin vers le fichier JSON produit par `auditer_url` ou par un appel précédent de `planifier_remediations` (voir spec D1). L'outil lit le fichier depuis le disque et extrait les fiches depuis `rapport["audit_complet"]` et les URLs depuis `rapport["pages"][*]["url"]`.

## Paramètres

| Paramètre | Type | Défaut | Description |
|-----------|------|--------|-------------|
| `rapport_path` | string (chemin) | requis | Chemin vers le fichier JSON produit par `auditer_url` ou `planifier_remediations` |
| `output_dir` | string | `"."` | Répertoire de sortie pour les fichiers générés |
| `inclure_toutes` | bool | `false` | Si `true`, inclut les 115 fiches (Conforme → `deja_conforme`, Non-testé → `a_tester`) |

## Corrections manuelles dans le JSON

Entre l'audit initial et l'appel à `planifier_remediations`, l'utilisateur peut modifier le fichier JSON produit par `auditer_url` pour enregistrer ses corrections — notamment celles non testables en front-end (back-end, infrastructure, contenu).

**Seul champ à modifier :** `audit_complet[*].statut`

Valeurs acceptables : `"Conforme"`, `"Non-conforme"`, `"Non-applicable"`, `"Indéterminé"`, `"Non-testé"`

L'utilisateur passe ensuite le chemin de ce fichier (éventuellement renommé ou déplacé) via `rapport_path`.

## Vérification des corrections

L'outil extrait les URLs depuis `rapport["pages"][*]["url"]` et re-crawle exactement ces mêmes URLs. Les `validation_rule` et `max_value` sont lus depuis les fiches du rapport fourni — pas d'accès au cache nécessaire.

**Règle de priorité pour chaque fiche :**

- Fiche **auto-testable** (`max_value` + métrique crawlée disponible) → le résultat du re-crawl **prend le dessus** sur le statut manuel :
  - Métrique ≤ max_value → `statut: "Conforme"`, `correction_verifiee: true`
  - Métrique > max_value → `statut: "Non-conforme"`, `correction_verifiee: false`
- Fiche **non-testable en front** (pas de `max_value` ou métrique non disponible) → le statut du JSON est **respecté tel quel**, `correction_verifiee: null`

Ainsi, une correction back-end déclarée `"Conforme"` manuellement est comptée dans le score sans re-crawl.

## Score de priorisation

```
score = environmental_impact * 2 - priority_implementation
```

Favorise les fiches à fort impact environnemental et faible effort d'implémentation. Les fiches Non-conforme et Indéterminé sont triées par score décroissant, puis réparties en 3 phases par tercile.

## Structure de retour

```json
{
  "pages_verifiees": ["https://example.com", "https://example.com/about"],
  // URLs extraites de rapport["pages"][*]["url"]
  "score_original": {
    "score_pct": 12.2,
    "conforme": 14,
    "total": 115
  },
  "score_apres_verification": {
    "score_pct": 18.3,
    "conforme": 21,
    "total": 115
  },
  "corrections_verifiees": {
    "corrigees": 7,
    "encore_non_conformes": 3,
    "non_testables_en_front": 13
  },
  "total_a_remedier": 16,
  "phases": [
    {
      "phase": 1,
      "label": "Court terme",
      "delta": {
        "fiches_a_corriger": 6,
        "score_apres": 23.5,
        "gain_pct": 5.2
      },
      "fiches": [
        {
          "id": "RWEB_0047",
          "titre": "Limiter le nombre de requêtes HTTP",
          "lifecycle": "3-developement",
          "url": "https://rweb.greenit.fr/fr/fiches/0047",
          "statut": "Non-conforme",
          "environmental_impact": 4,
          "priority_implementation": 2,
          "score": 6,
          "valeur_mesuree": 65,
          "max_value": "40",
          "correction_verifiee": false
        }
      ]
    },
    { "phase": 2, "label": "Moyen terme", "delta": {...}, "fiches": [...] },
    { "phase": 3, "label": "Long terme", "delta": {...}, "fiches": [...] }
  ],
  "rapport_mis_a_jour": {
    "pages": ["https://example.com", "https://example.com/about"],
    "score_conformite": {
      "score_pct": 18.3,
      "conforme": 21,
      "non_conforme": 4,
      "non_applicable": 3,
      "indetermine": 5,
      "non_teste": 82,
      "total": 115
    },
    "audit_complet": [
      {
        "id": "RWEB_0047",
        "titre": "Limiter le nombre de requêtes HTTP",
        "lifecycle": "3-developement",
        "url": "https://rweb.greenit.fr/fr/fiches/0047",
        "validation_rule": "de requêtes HTTP",
        "max_value": "40",
        "valeur_mesuree": 65,
        "statut": "Non-conforme",
        "environmental_impact": 4,
        "priority_implementation": 2
      }
    ]
  }
}
```

`score_original` est absent si `rapport["pages"]` est vide (pas de pages à re-crawler).

## Workflow itératif

`rapport_mis_a_jour` permet de boucler sans perte d'information :

1. `auditer_url` → rapport initial
2. Corrections manuelles
3. `planifier_remediations(rapport)` → plan + `rapport_mis_a_jour` avec statuts vérifiés
4. Nouvelles corrections
5. `planifier_remediations(rapport_mis_a_jour)` → nouveau plan avec delta mis à jour
6. Répéter jusqu'à satisfaction

Le `rapport_mis_a_jour` est structurellement compatible avec le rapport produit par `auditer_url` : il contient les mêmes champs (`pages`, `score_conformite`, `audit_complet`). L'utilisateur peut le sauvegarder et le re-fournir à l'appel suivant.

### Avec `inclure_toutes: true`

```json
{
  "deja_conforme": [
    { "id": "RWEB_0032", "titre": "...", "environmental_impact": 3, "priority_implementation": 2, "correction_verifiee": true }
  ],
  "a_tester": [
    { "id": "RWEB_0009", "titre": "...", "environmental_impact": 3, "max_value": "2", "correction_verifiee": null }
  ]
}
```

## Calcul du delta (cumulatif)

`score_apres` est cumulatif depuis le score post-vérification (ou score original si pas d'URL).

```
score_base = score_apres_verification
score_apres_phase_N = (conforme_base + Σ fiches_à_corriger_phases_1..N) / 115 * 100
gain_pct_phase_N = score_apres_phase_N - score_apres_phase_N-1
```

Les fiches Indéterminé comptent dans `fiches_à_corriger` (hypothèse optimiste).

## Fichiers modifiés

- `files/greenit_mcp_final.py` — ajout de l'outil MCP `planifier_remediations` ; lecture depuis `rapport_path`, écriture JSON + markdown + HTML sur disque (D1)
- `files/checklist.py` — réutilisation de la logique d'auto-validation (A1) pour la vérification post-corrections
- `tests/test_tools.py` — tests du plan, de la vérification, du delta

## Tests

- `rapport_path` est lu depuis le disque (JSON valide, peut être renommé ou déplacé par l'utilisateur)
- Fiche non-testable avec statut modifié manuellement en `"Conforme"` dans le JSON → compté dans le score, `correction_verifiee: null`
- Fiche auto-testable avec statut modifié manuellement → le re-crawl prend le dessus sur le statut manuel
- URLs extraites de `rapport["pages"][*]["url"]`, re-crawlées dans le même ordre que l'audit initial
- Fiche avec `max_value` + métrique disponible : `correction_verifiee` est `true` ou `false`
- Fiche sans `max_value` ou métrique indisponible : `correction_verifiee: null`
- `score = environmental_impact * 2 - priority_implementation`
- 3 phases par tercile, fiches triées par score décroissant
- `score_apres` cumulatif depuis le score post-vérification
- `inclure_toutes=true` ajoute `deja_conforme` et `a_tester`
- Trois fichiers écrits sur disque dans `output_dir` : `.json`, `.md` et `.html`
- `rapport_mis_a_jour` inclus dans le JSON de sortie, utilisable comme `rapport_path` au cycle suivant
