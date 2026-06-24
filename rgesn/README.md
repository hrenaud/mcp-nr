# RGESN MCP Server

> Faisant partie du monorepo [mcp-nr](../). Pour builder, utiliser `docker build -f rgesn/Dockerfile .` depuis la racine du monorepo.

Serveur [MCP (Model Context Protocol)](https://modelcontextprotocol.io) donnant accès au [RGESN](https://ecoresponsable.numerique.gouv.fr/publications/referentiel-general-ecoconception/) (Référentiel Général d'Écoconception de Services Numériques) depuis Claude (Desktop, Code, ou tout client MCP).

Outils disponibles : `rgesn_lister_criteres`, `rgesn_obtenir_critere`, `rgesn_chercher`, `rgesn_statistiques`, `rgesn_taux_conformite`, `rgesn_checklist`, `rgesn_criteres_prioritaires`.

## Démarrage rapide

### Docker Compose (mode HTTP)

```bash
# Depuis la racine du monorepo
docker compose -f rgesn/docker-compose.yml up -d

# Générer un token d'accès
docker run --rm -v $(pwd)/rgesn/tokens:/app/tokens rgesn-mcp \
  --generate-token --name "votre-nom"

# Vérifier
curl http://localhost:8002/
```

### Mode stdio (local)

```bash
docker build -f rgesn/Dockerfile -t rgesn-mcp .
docker run --rm -i rgesn-mcp
```

## Configuration

| Variable                | Défaut    | Description                                      |
| ----------------------- | --------- | ------------------------------------------------ |
| `MCP_TRANSPORT`         | `stdio`   | Mode de transport : `stdio` ou `http`            |
| `MCP_HOST`              | `0.0.0.0` | Adresse d'écoute (mode `http`)                   |
| `MCP_PORT`              | `8000`    | Port interne (exposé en 8002 via docker-compose) |
| `MCP_BASE_URL`          | _(auto)_  | URL publique si derrière un reverse proxy        |
| `MCP_TOKEN_REQUEST_URL` | _(vide)_  | URL du formulaire de demande de token            |
| `ADMIN_TOKEN`           | _(vide)_  | Token admin pour l'API de gestion des tokens     |

## Intégration avec Claude

### Claude Desktop — mode stdio

```json
{
  "mcpServers": {
    "rgesn": {
      "command": "docker",
      "args": ["run", "--rm", "-i", "rgesn-mcp"]
    }
  }
}
```

### Claude Code (CLI) — mode stdio local

```bash
claude mcp add rgesn -- docker run --rm -i rgesn-mcp
```

## Structure

```
rgesn/
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
├── CHANGELOG.md
├── files/
│   ├── rgesn_mcp.py          # Serveur MCP principal (7 outils, 9 prompts)
│   ├── data.py               # Chargeur de cache singleton
│   ├── rgesn_cache.json      # 78 critères RGESN 2024
│   └── preparer_donnees.py   # Script de préparation des données depuis le PDF
├── tests/
│   ├── test_rgesn.py         # Tests fonctionnels
│   └── test_smoke.py         # Tests smoke
└── tokens/
    └── .gitkeep              # Volume Docker (tokens.json non embarqué)
```

## Tests

```bash
# Depuis la racine du monorepo
pip install -e core/
pip install fastmcp httpx pytest pytest-asyncio
cd rgesn/files && pytest ../tests/ -v
```

## Données

Le cache contient les 78 critères RGESN 2024 avec leurs métadonnées complètes. Les champs `objectif`, `mise_en_oeuvre` et `moyen_de_controle` sont renseignés pour l'ensemble des 9 thèmes (données extraites du [PDF officiel ARCEP](https://www.arcep.fr/uploads/tx_gspublication/referentiel_general_ecoconception_des_services_numeriques_version_2024.pdf)).

## Calcul du taux de conformité

Le taux est pondéré par priorité : `[Σ(C×poids) / Σ(applicables×poids)] × 100`

| Priorité    | Poids |
| ----------- | ----- |
| Prioritaire | 1.5   |
| Recommandé  | 1.25  |
| Modéré      | 1.0   |

Les critères NA sont exclus du calcul.
