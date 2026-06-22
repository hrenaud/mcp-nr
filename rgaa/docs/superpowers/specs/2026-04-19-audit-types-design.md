# Design : Types d'audit RGAA

**Date :** 2026-04-19  
**Statut :** Validé

## Contexte

Il existe 3 types d'audit d'accessibilité RGAA :

- **Audit complet** — 106 critères, seul type répondant à l'obligation légale de conformité
- **Audit rapide** — 25 critères essentiels niveau A (source : design.numerique.gouv.fr/outils/audit-rapide/)
- **Audit complémentaire** — 25 critères complémentaires (source : design.numerique.gouv.fr/outils/audit-complementaire/)

Cette feature expose ces 3 types via des outils et prompts MCP.

## Fichier de données

**`files/audit_types.json`** — fichier dédié (approche C choisie)

```json
{
  "complet": {
    "nom": "Audit complet RGAA",
    "description": "Audite tous les critères RGAA 4.2.1. Seul type répondant à l'obligation légale de conformité.",
    "conforme_obligation": true,
    "criteres": null
  },
  "rapide": {
    "nom": "Audit rapide RGAA",
    "description": "25 critères essentiels de niveau A. Diagnostic rapide, ne suffit pas pour l'obligation légale.",
    "conforme_obligation": false,
    "criteres": ["1.1","3.1","4.1","4.10","5.3","5.7","6.1","6.2","7.1","7.3","8.3","8.4","8.5","9.1","10.3","10.6","10.7","11.1","11.2","11.5","11.6","11.9","11.10","12.8","12.9"]
  },
  "complementaire": {
    "nom": "Audit complémentaire RGAA",
    "description": "25 critères complémentaires couvrant images, médias, tableaux, consultation. Complète l'audit rapide.",
    "conforme_obligation": false,
    "criteres": ["1.3","1.5","1.6","1.7","4.2","4.4","4.8","4.9","5.4","5.6","7.2","8.2","8.6","8.10","10.2","10.8","10.9","10.10","13.1","13.3","13.4","13.5","13.6","13.7","13.8"]
  }
}
```

`criteres: null` pour le complet → liste chargée dynamiquement depuis `rgaa_cache.json`.

## Outils MCP (2 nouveaux)

### `rgaa_types_audit()`

Aucun paramètre. Retourne les 3 types d'audit avec : type (slug), nom, description, `conforme_obligation` (bool), `nb_criteres` (int).

**Cas d'usage :** permettre à Claude de comprendre quel type d'audit choisir et si l'obligation légale est couverte.

### `rgaa_criteres_audit(type: "complet" | "rapide" | "complementaire")`

Retourne la liste enrichie des critères du type demandé (id, theme, titre) via `rgaa_cache.json`.

**Cas d'usage :** obtenir la liste de travail pour un audit d'un type donné, à passer ensuite à `rgaa_checklist`.

## Prompts MCP (3 nouveaux)

### `audit_par_type(url, type)` — générique

Guide un audit complet selon le type. Étapes :
1. Appelle `rgaa_types_audit()` pour valider le type et signaler si l'obligation légale est couverte
2. Appelle `rgaa_criteres_audit(type)` pour la liste de critères
3. Appelle `rgaa_analyser(url)` pour les violations automatiques
4. Appelle `rgaa_checklist` sur les critères du type pour les tests manuels
5. Synthèse avec mention explicite de la conformité légale

### `audit_rapide(url)` — raccourci

Précise d'emblée : 25 critères niveau A, ne couvre pas l'obligation légale. Délègue à `audit_par_type(url, "rapide")`.

### `audit_complementaire(url)` — raccourci

Précise d'emblée : 25 critères complémentaires, à combiner avec l'audit rapide. Délègue à `audit_par_type(url, "complementaire")`.

> L'audit complet reste couvert par le prompt existant `audit_page`. Pas de doublon.

## Documentation (3 fichiers à mettre à jour)

### `rgaa_mcp.py` — `TOOLS_DESCRIPTION`

Ajouter les 2 nouveaux outils à la liste `TOOLS_DESCRIPTION` (utilisée par la route HTTP `/guide`) :

```python
("rgaa_types_audit", "Liste les 3 types d'audit RGAA et indique lequel répond à l'obligation légale"),
("rgaa_criteres_audit", "Retourne la liste des critères pour un type d'audit donné (complet, rapide, complémentaire)"),
```

La section HTML de `_http_guide` devra aussi inclure une section dédiée aux types d'audit avec tableau des 3 types (nom, nb critères, conforme obligation légale).

### `README.md`

Ajouter les 2 nouveaux outils dans le tableau "Outils disponibles". Ajouter les 3 nouveaux prompts dans la section équivalente si elle existe.

### `docs/GUIDE_DEVELOPPEMENT.md`

Ajouter une section "Types d'audit" avec :
- Explication des 3 types et leur périmètre
- Exemples de prompts naturels pour chaque type
- Note sur l'obligation légale

## Ce qui ne change pas

- Structure existante de `rgaa_mcp.py` — conventions, patterns inchangés
- `rgaa_cache.json` — données RGAA non modifiées
- Prompts existants — aucune modification
