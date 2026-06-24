# Guide développeur — MCP GreenIT

Documentation pour les développeurs qui maintiennent ce MCP dans le monorepo `mcp-nr`.

---

## Structure des fichiers

```
greenit/
├── files/
│   ├── greenit_mcp.py        # Outils, ressources et prompts MCP
│   ├── data.py               # Chargement du cache + calcul EcoIndex
│   ├── preparer_donnees.py   # Mise à jour des données depuis l'API
│   └── greenit_cache.json    # Cache statique (source de vérité)
├── tests/
│   ├── test_tools.py          # Tests unitaires des 9 outils MCP
│   ├── test_routes_http.py    # Tests des routes HTTP (/, /guide, admin)
│   ├── test_admin_api.py      # Tests de l'API d'administration des tokens
│   ├── test_data.py           # Tests du calcul EcoIndex et du cache
│   ├── test_ecoindex.py       # Tests de précision du calcul EcoIndex
│   ├── test_prompts.py        # Tests des prompts MCP
│   ├── test_metadata.py       # Tests de la ressource metadata
│   ├── test_helpers.py        # Tests des helpers de validation
│   ├── test_docker_integration.py
│   └── test_architecture_parity.py  # Vérifie la parité avec le core
└── docs/
    └── GUIDE_DEVELOPPEMENT.md  (ce fichier)
```

---

## Lancer les tests

```bash
cd greenit/files && pytest ../tests/ -v
```

Tests ciblés :

```bash
pytest ../tests/test_tools.py -v        # outils MCP uniquement
pytest ../tests/test_data.py -v         # cache + EcoIndex
pytest ../tests/test_routes_http.py -v  # routes HTTP
```

---

## Mettre à jour les données

Le cache `greenit_cache.json` est la source de vérité. Il est généré depuis l'API officielle GreenIT.

```bash
cd greenit/files
python preparer_donnees.py --telecharger   # Télécharge depuis rweb.greenit.fr/api
python preparer_donnees.py --check         # Vérifie le cache existant
```

Source API : `https://rweb.greenit.fr/api/fiches?lang=fr&version=latest`

Structure du cache :

```json
{
  "meta": { "version": "...", "updated_at": "..." },
  "fiches": {
    "RWEB_0001": {
      "num": "RWEB_0001",
      "title": "...",
      "lifecycle": "3-developement",
      "environmental_impact": 3,
      "priority_implementation": 4,
      "saved_resources": ["cpu", "network"],
      "shortDescription": "...",
      "description": "...",
      "validations": [...]
    }
  }
}
```

---

## Ajouter un outil MCP

1. Déclarer les métadonnées dans `_greenit_tool_definitions()` (utilisé par la route `/guide`) :

```python
def _greenit_tool_definitions() -> list[dict]:
    return [
        # ... outils existants ...
        {
            "name": "greenit_mon_outil",
            "description": "Description courte.",
            "params": [
                {"name": "param1", "type": "str", "desc": "Description.", "required": True},
            ],
        },
    ]
```

2. Implémenter l'outil avec le décorateur `@mcp.tool()` dans `greenit_mcp.py` :

```python
@mcp.tool(
    description="Description longue de l'outil.",
    annotations=ToolAnnotations(title="Titre lisible"),
)
def greenit_mon_outil(param1: str) -> dict:
    fiches = charger_cache().get("fiches", {})
    # ... logique ...
    return {"resultat": ...}
```

3. Écrire le test TDD dans `tests/test_tools.py` avant l'implémentation.

4. Mettre à jour `README.md` avec la description de l'outil.

---

## Calcul EcoIndex

La logique de calcul est dans `data.py` (fonction `calculer_ecoindex`). Elle implémente l'algorithme officiel EcoIndex avec quantiles pour 3 métriques : nœuds DOM, requêtes HTTP, poids en Ko.

L'outil `greenit_calculer_ecoindex` ne navigue pas sur le web — il reçoit les 3 métriques déjà mesurées. C'est Claude (via Playwright) qui mesure la page avant d'appeler l'outil.

---

## Variables injectées dans `routes.py`

Ces variables sont injectées en début de `greenit_mcp.py`, après l'import de `routes` :

| Variable                       | Valeur actuelle                          |
| ------------------------------ | ---------------------------------------- |
| `routes._VERSION`              | `VERSION` (ex. `"2.0.2"`)                |
| `routes._REFERENTIEL_VERSION`  | version lue dans le cache JSON           |
| `routes._MCP_NAME`             | `"GreenIT MCP"`                          |
| `routes._MCP_ID`               | `"greenit"`                              |
| `routes._ITEMS_KEY`            | `"fiches"`                               |
| `routes._LOGO`                 | `"🌱"`                                   |
| `routes._ACCENT`               | `"#22c55e"`                              |
| `routes._TAGLINE`              | `"Bonnes pratiques d'écoconception web"` |
| `routes._get_tool_definitions` | `_greenit_tool_definitions`              |
| `routes._guide_extra_sections` | `_greenit_guide_extra_sections`          |

Modifier ces variables change le comportement des routes partagées (homepage, guide, install.sh).

---

## Ressources MCP déclarées

| URI                          | Description                 |
| ---------------------------- | --------------------------- |
| `greenit://version`          | Version du MCP (via core)   |
| `greenit://fiche/{fiche_id}` | Fiche complète par ID       |
| `greenit://index`            | Index de toutes les fiches  |
| `greenit://metadata`         | Métadonnées et statistiques |

---

## Release

Voir les instructions dans `CLAUDE.md` (à la racine du monorepo) : mettre à jour `CHANGELOG.md`, puis `./release.sh <version>` depuis la racine, puis `git push && git push origin v<version>`.
