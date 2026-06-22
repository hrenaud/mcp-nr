# GreenIT MCP

> Partie du monorepo [mcp-nr](../). Build : `docker build -f greenit/Dockerfile .` depuis la racine.

Serveur MCP donnant accès au référentiel des 119 bonnes pratiques d'éco-conception web [GreenIT](https://rweb.greenit.fr/fr/fiches).

## Outils

| Outil                    | Description                                                                    |
| ------------------------ | ------------------------------------------------------------------------------ |
| `lister_fiches`          | Liste toutes les fiches — filtrable par lifecycle, ressource, impact, priorité |
| `fiches_prioritaires`    | Fiches triées par score combiné impact × priorité                              |
| `chercher_fiche`         | Recherche textuelle avec scoring de pertinence                                 |
| `obtenir_fiche_complete` | Contenu complet d'une fiche                                                    |
| `comparer_fiches`        | Comparaison côte à côte de plusieurs fiches                                    |
| `obtenir_statistiques`   | Distributions et top 5 par score combiné                                       |
| `lister_lifecycles`      | Les 7 phases du cycle de vie avec nombre de fiches                             |
| `lister_ressources`      | Les 8 types de ressources sauvegardées avec nombre de fiches                   |
| `calculer_ecoindex`      | Score EcoIndex (0–100, grade A–G) à partir de 3 métriques DOM/HTTP/poids       |

## Ressources

| Ressource              | Description                                    |
| ---------------------- | ---------------------------------------------- |
| `greenit://version`    | Version du serveur et des données              |
| `greenit://index`      | Index de toutes les fiches                     |
| `greenit://fiche/{id}` | Contenu complet d'une fiche (ex : `RWEB_0051`) |
| `greenit://metadata`   | Métadonnées du référentiel                     |

## Tests

```bash
cd greenit/files && pytest ../tests/ -v
```

## Structure

```
greenit/
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
├── CHANGELOG.md
├── files/
│   └── greenit_mcp.py          # Serveur MCP principal
├── tests/                      # ~191 tests (unitaires + Docker)
├── tokens/
│   └── .gitkeep               # Volume Docker (tokens.json non embarqué)
└── docs/
    └── GUIDE_DEVELOPPEMENT.md  # Outils avec exemples de prompts
```

→ Déploiement, tokens, nginx : [docs/DEPLOIEMENT.md](../docs/DEPLOIEMENT.md)  
→ Exemples d'usage avec prompts : [docs/GUIDE_DEVELOPPEMENT.md](docs/GUIDE_DEVELOPPEMENT.md)
