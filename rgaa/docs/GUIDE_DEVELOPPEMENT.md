# Guide développeur — MCP RGAA

Documentation pour les développeurs qui maintiennent ce MCP dans le monorepo `mcp-nr`.

---

## Structure des fichiers

```
rgaa/
├── files/
│   ├── rgaa_mcp.py           # Outils, ressources et prompts MCP
│   ├── data.py               # Chargement du cache
│   ├── analyseur.py          # Analyse statique HTML (BeautifulSoup)
│   ├── preparer_donnees.py   # Mise à jour des données depuis GitHub
│   ├── audit_types.json      # Définitions des types d'audit (complet/rapide/complémentaire)
│   └── rgaa_cache.json       # Cache statique (source de vérité)
├── tests/
│   ├── test_tools.py              # Tests unitaires des 10 outils MCP
│   ├── test_routes_http.py        # Tests des routes HTTP (/, /guide, admin)
│   ├── test_admin_api.py          # Tests de l'API d'administration des tokens
│   ├── test_analyseur.py          # Tests de l'analyse statique HTML
│   ├── test_conformite.py         # Tests du calcul du taux de conformité
│   ├── test_referentiel.py        # Tests des données du référentiel
│   ├── test_auth.py               # Tests d'authentification
│   ├── test_integration_annotations.py
│   ├── test_prompts.py            # Tests des prompts MCP
│   ├── test_docker_integration.py
│   └── test_architecture_parity.py  # Vérifie la parité avec le core
└── docs/
    └── GUIDE_DEVELOPPEMENT.md  (ce fichier)
```

---

## Lancer les tests

```bash
cd rgaa/files && pytest ../tests/ -v
```

Tests ciblés :

```bash
pytest ../tests/test_tools.py -v        # outils MCP uniquement
pytest ../tests/test_analyseur.py -v    # analyse statique HTML
pytest ../tests/test_routes_http.py -v  # routes HTTP
```

---

## Mettre à jour les données

Le cache `rgaa_cache.json` est généré depuis les fichiers JSON du dépôt GitHub officiel DISIC.

```bash
cd rgaa/files
python preparer_donnees.py --telecharger   # Fetch depuis GitHub DISIC
python preparer_donnees.py --check         # Vérifie le cache existant
```

Sources :

- Critères : `https://raw.githubusercontent.com/DISIC/accessibilite.numerique.gouv.fr/main/RGAA/criteres.json`
- Glossaire : `https://raw.githubusercontent.com/DISIC/accessibilite.numerique.gouv.fr/main/RGAA/glossaire.json`

Structure du cache :

```json
{
  "meta": { "version": "4.2.1", "updated_at": "..." },
  "criteres": {
    "1.1": {
      "id": "1.1",
      "titre": "...",
      "theme": "1",
      "theme_nom": "Images",
      "niveau_wcag": "A",
      "tests": ["1.1.1 : ..."],
      "references": { "wcag": ["1.1.1 Non-text Content"] }
    }
  },
  "glossaire": {
    "terme": { "terme": "...", "definition": "...", "exemples": [...] }
  }
}
```

---

## Analyseur statique HTML

`analyseur.py` implémente une analyse BeautifulSoup sur les thèmes automatisables (~57% des critères). Il est appelé par l'outil `rgaa_analyser`.

Les thèmes couverts : Images (1.1), Cadres (2.1), Tableaux (5.1, 5.7), Liens (6.1), Éléments obligatoires (8.3, 8.5, 8.6), Structuration (9.1, 9.2), Formulaires (11.1), Navigation (12.11).

Pour ajouter une règle d'analyse : modifier `analyseur.py` et ajouter les tests dans `test_analyseur.py`.

---

## Types d'audit

`audit_types.json` définit les trois types d'audit : `complet` (106 critères), `rapide` (25 critères niveau A essentiels), `complementaire` (25 critères approfondissement). Seul `complet` répond à l'obligation légale RGAA.

Pour modifier la liste des critères d'un type d'audit, éditer directement `audit_types.json`.

---

## Ajouter un outil MCP

1. Déclarer les métadonnées dans `_rgaa_tool_definitions()` (utilisé par la route `/guide`) :

```python
def _rgaa_tool_definitions() -> list[dict]:
    return [
        # ... outils existants ...
        {
            "name": "rgaa_mon_outil",
            "description": "Description courte.",
            "params": [
                {"name": "param1", "type": "str", "desc": "Description.", "required": True},
            ],
        },
    ]
```

2. Implémenter l'outil avec le décorateur `@mcp.tool()` dans `rgaa_mcp.py` :

```python
@mcp.tool(
    description="Description longue de l'outil.",
    annotations=ToolAnnotations(title="Titre lisible"),
)
def rgaa_mon_outil(param1: str) -> dict:
    criteres = charger_cache().get("criteres", {})
    # ... logique ...
    return {"resultat": ...}
```

3. Écrire le test TDD dans `tests/test_tools.py` avant l'implémentation.

4. Mettre à jour `README.md` avec la description de l'outil.

---

## Variables injectées dans `routes.py`

Ces variables sont injectées via `_routes_mod` en début de `rgaa_mcp.py` :

| Variable                           | Valeur actuelle                                  |
| ---------------------------------- | ------------------------------------------------ |
| `_routes_mod._VERSION`             | `VERSION` (ex. `"2.0.2"`)                        |
| `_routes_mod._REFERENTIEL_VERSION` | version lue dans le cache JSON                   |
| `_routes_mod._MCP_NAME`            | `"RGAA MCP"`                                     |
| `_routes_mod._MCP_ID`              | `"rgaa"`                                         |
| `_routes_mod._ITEMS_KEY`           | `"criteres"`                                     |
| `_routes_mod._LOGO`                | `"♿"`                                           |
| `_routes_mod._ACCENT`              | `"#2563eb"`                                      |
| `_routes_mod._TAGLINE`             | `"Référentiel d'accessibilité des services web"` |
| `_rgaa_tool_definitions`           | passé à `factory.create_mcp()`                   |
| `_rgaa_guide_extra_sections`       | passé à `factory.create_mcp()`                   |

---

## Ressources MCP déclarées

| URI                            | Description                 |
| ------------------------------ | --------------------------- |
| `rgaa://version`               | Version du MCP (via core)   |
| `rgaa://criteres/{critere_id}` | Critère complet par ID      |
| `rgaa://index`                 | Index de tous les critères  |
| `rgaa://metadata`              | Métadonnées et statistiques |

---

## Release

Voir les instructions dans `CLAUDE.md` (à la racine du monorepo) : mettre à jour `CHANGELOG.md`, puis `./release.sh <version>` depuis la racine, puis `git push && git push origin v<version>`.
