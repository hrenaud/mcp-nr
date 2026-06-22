# RGESN MCP Server

> Faisant partie du monorepo [mcp-nr](../). Pour builder, utiliser `docker build -f rgesn/Dockerfile .` depuis la racine du monorepo.

Serveur [MCP (Model Context Protocol)](https://modelcontextprotocol.io) donnant accès au [RGESN](https://ecoresponsable.numerique.gouv.fr/publications/referentiel-general-ecoconception/) (Référentiel Général d'Écoconception de Services Numériques) depuis Claude (Desktop, Code, ou tout client MCP).

> **État actuel : scaffold — outils RGESN à implémenter.**

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
│   └── rgesn_mcp.py          # Serveur MCP principal (scaffold)
├── tests/
│   └── test_smoke.py         # Tests smoke (2 tests)
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

## Développement

Ce scaffold est prêt à recevoir les outils RGESN. Le pattern à suivre est identique à `rgaa/` :

1. Ajouter les données RGESN dans `files/`
2. Définir `_rgesn_tool_definitions()` dans `rgesn_mcp.py`
3. Implémenter les outils avec `@mcp.tool()`
4. Ajouter les tests dans `tests/`
