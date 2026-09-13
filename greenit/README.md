# GreenIT MCP

> Partie du monorepo [mcp-nr](../). Build : `docker build -f greenit/Dockerfile .` depuis la racine.

Serveur MCP donnant accès au référentiel des 119 bonnes pratiques d'éco-conception web [GreenIT](https://rweb.greenit.fr/fr/fiches).

## Outils

| Outil                            | Description                                                                    |
| -------------------------------- | ------------------------------------------------------------------------------ |
| `greenit_lister_fiches`          | Liste toutes les fiches — filtrable par lifecycle, ressource, impact, priorité |
| `greenit_fiches_prioritaires`    | Fiches triées par score combiné impact × priorité                              |
| `greenit_chercher_fiche`         | Recherche textuelle avec scoring de pertinence                                 |
| `greenit_obtenir_fiche_complete` | Contenu complet d'une fiche                                                    |
| `greenit_comparer_fiches`        | Comparaison côte à côte de plusieurs fiches                                    |
| `greenit_obtenir_statistiques`   | Distributions et top 5 par score combiné                                       |
| `greenit_lister_lifecycles`      | Les 7 phases du cycle de vie avec nombre de fiches                             |
| `greenit_lister_ressources`      | Les 8 types de ressources sauvegardées avec nombre de fiches                   |
| `greenit_calculer_ecoindex`      | Renvoie score EcoIndex (0–100), grade (A–G), `greenhouse_gases_g` numérique (g CO2e) et `water_consumption_cl` numérique (cl), à partir de DOM/HTTP/poids |
| `greenit_obtenir_methodologie_ecoindex` | Retourne la seule méthode normalisée de collecte des trois métriques EcoIndex |

## Méthode normalisée EcoIndex

`greenit_obtenir_methodologie_ecoindex` est la seule méthode normalisée du MCP GreenIT pour alimenter `greenit_calculer_ecoindex`. Tous les appelants doivent l'utiliser afin que les scores soient comparables. Le calculateur ne collecte rien : il calcule uniquement à partir de `dom_nodes`, `requests` et `size_kb`.

La convention impose un contexte navigateur neuf à cache froid, un viewport de 1920 × 1080, trois secondes d'attente après le chargement, un défilement progressif jusqu'en bas, puis trois nouvelles secondes d'attente. Exécuter ensuite ce JavaScript dans la page, sans Lighthouse :

```js
() => {
  const countDomNodes = (root) => {
    let count = 0;

    for (const element of root.querySelectorAll("*")) {
      if (element.parentElement?.localName !== "svg") {
        count += 1;
      }
      if (element.shadowRoot) {
        count += countDomNodes(element.shadowRoot);
      }
    }

    return count;
  };

  const resources = performance.getEntriesByType("resource");
  const navigation = performance.getEntriesByType("navigation")[0];
  const networkEntries = navigation ? [navigation, ...resources] : resources;

  return {
    dom_nodes: document.body ? countDomNodes(document.body) : 0,
    requests: networkEntries.length,
    size_kb: networkEntries.reduce(
      (bytes, entry) => bytes + (entry.transferSize || 0),
      0
    ) / 1024
  };
}
```

`dom_nodes` compte les éléments descendants de `document.body`, sans compter `body`. Le parcours entre récursivement dans les `shadowRoot` ouverts et ne compte pas les enfants directs des éléments `<svg>`. Il continue à parcourir leurs descendants éventuels.

Les Shadow DOM fermés ne sont pas observables depuis la page. Le cache et les ressources cross-origin sans en-tête `Timing-Allow-Origin` peuvent aussi produire un `transferSize` nul. C'est pourquoi la méthode exige un contexte à cache froid et expose ces limites dans son résultat.

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
