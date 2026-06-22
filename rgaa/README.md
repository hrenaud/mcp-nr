# RGAA MCP

> Partie du monorepo [mcp-nr](../). Build : `docker build -f rgaa/Dockerfile .` depuis la racine.

Serveur MCP donnant accès au référentiel [RGAA 4.2.1](https://accessibilite.numerique.gouv.fr/methode/criteres-et-tests/) — 106 critères d'accessibilité numérique.

## Outils

| Outil                  | Description                                                             |
| ---------------------- | ----------------------------------------------------------------------- |
| `rgaa_lister_criteres` | Liste tous les critères — filtrable par thème ou niveau WCAG            |
| `rgaa_obtenir_critere` | Contenu complet d'un critère : tests, conditions, références WCAG       |
| `rgaa_chercher`        | Recherche par mot-clé dans les critères et le glossaire                 |
| `rgaa_glossaire`       | Définition d'un terme du glossaire RGAA                                 |
| `rgaa_statistiques`    | Distributions par thème et niveau WCAG                                  |
| `rgaa_checklist`       | Checklist de tests manuels avec outils recommandés                      |
| `rgaa_taux_conformite` | Calcule le taux de conformité à partir des résultats d'audit            |
| `rgaa_analyser`        | Analyse statique d'une URL — détecte les violations RGAA automatisables |
| `rgaa_types_audit`     | Liste les types d'audit (complet, rapide, complémentaire)               |
| `rgaa_criteres_audit`  | Critères enrichis pour un type d'audit donné                            |

## Tests

```bash
cd rgaa/files && pytest ../tests/ -v
```

## Structure

```
rgaa/
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
├── CHANGELOG.md
├── files/
│   └── rgaa_mcp.py             # Serveur MCP principal
├── tests/                      # ~227 tests (unitaires + Docker)
├── tokens/
│   └── .gitkeep               # Volume Docker (tokens.json non embarqué)
└── docs/
    └── GUIDE_DEVELOPPEMENT.md  # Outils avec exemples de prompts
```

→ Déploiement, tokens, nginx : [docs/DEPLOIEMENT.md](../docs/DEPLOIEMENT.md)  
→ Exemples d'usage avec prompts : [docs/GUIDE_DEVELOPPEMENT.md](docs/GUIDE_DEVELOPPEMENT.md)
