# GreenIT MCP Server

Serveur [MCP (Model Context Protocol)](https://modelcontextprotocol.io) donnant accès au référentiel des 119 bonnes pratiques d'écoconception web de [GreenIT](https://rweb.greenit.fr/fr/fiches) depuis Claude (Desktop, Code, ou tout client MCP).

## Fonctionnalités

- **9 outils MCP** : lister avec filtres, fiches prioritaires, chercher avec scoring, comparer, stats, calcul EcoIndex, et plus
- **3 ressources** : index, fiche individuelle, métadonnées
- **3 prompts** : analyser l'impact, générer un audit, comparer des pratiques
- **Deux modes de transport** : stdio (local) ou HTTP avec authentification par token Bearer
- **Gestion des tokens** : création avec nom et expiration, liste, révocation — stockage dans `tokens/tokens.json` (volume Docker, créé automatiquement)
- **Données embarquées** : 119 fiches GreenIT (RWEB_0001 → RWEB_0119), prêtes à l'emploi sans connexion externe

---

## Installation

### Prérequis

- **Python 3.13** (required for full compatibility with fastmcp 3.2.4+ and Playwright)
- **pip** (Python package manager, included with Python 3.13+)
- **Docker** and **docker-compose** (for containerized deployment)
- **Playwright browser binaries** (installed automatically by requirements.txt)

### Local Development Setup (optional, for running tests or development)

For local testing without Docker:

```bash
# 1. Clone the repository
git clone https://github.com/anthropics/mcp-greenit.git
cd mcp-greenit

# 2. Create a Python virtual environment
python3.13 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies (includes Playwright)
pip install -r requirements.txt

# 4. Install Playwright browsers (required for EcoIndex calculations)
python -m playwright install

# 5. Install development dependencies (for tests)
pip install -e ".[dev]"

# 6. Run tests to verify installation
python -m pytest tests/ -v
```

### Docker Image Build

For containerized deployment:

```bash
# 1. Build the Docker image (creates greenit-mcp image)
docker build -t greenit-mcp .

# 2. Verify the image was built successfully
docker images | grep greenit-mcp
```

---

## Getting Started

### Quick Start with Docker Compose (recommended for HTTP mode)

```bash
# 1. Start the server in HTTP mode (port 8000)
docker compose up -d

# 2. Verify the server is running
docker compose ps
# Expected output: greenit service with "Up" status and "healthy" health status

# 3. Check the server is healthy
curl http://localhost:8000/
# Expected output: HTML page with "OK" status and number of loaded practices

# 4. Generate an access token
docker run --rm -v $(pwd)/tokens:/app/tokens greenit-mcp \
  --generate-token --name "your-name"
# Save the generated token (starts with random characters)

# 5. Verify token works
curl -H "Authorization: Bearer <your-token>" \
  http://localhost:8000/mcp

# 6. View server logs (including health checks)
docker compose logs -f
```

### Local Development Mode (stdio — embedded in Claude)

For testing with Claude Desktop or Claude Code locally:

```bash
# 1. Build the image (one-time)
docker build -t greenit-mcp .

# 2. Start in stdio mode (reads from stdin, writes to stdout)
docker run --rm -i greenit-mcp

# This mode is used when configured in Claude Desktop config or Claude Code MCP settings
```

### Stopping the Server

```bash
# Stop docker compose service (keeps volumes)
docker compose down

# Stop and remove all traces (including tokens volume)
docker compose down -v
```

---

## Configuration

### Variables d'environnement

| Variable | Défaut | Description |
|----------|--------|-------------|
| `MCP_TRANSPORT` | `stdio` | Mode de transport : `stdio` ou `http` |
| `MCP_HOST` | `0.0.0.0` | Adresse d'écoute (mode `http`) |
| `MCP_PORT` | `8000` | Port d'écoute (mode `http`) |
| `MCP_BASE_URL` | _(auto)_ | URL publique du serveur, affichée dans la page d'accueil et le script d'installation. À définir dans `.env` si le serveur est derrière un reverse proxy (ex : `https://mcp.example.com`). |
| `MCP_TOKEN_REQUEST_URL` | _(vide)_ | URL du formulaire de demande de token, affichée sur la page d'accueil. |
| `ADMIN_TOKEN` | _(vide)_ | Token admin pour l'API de gestion des tokens (HTTP uniquement) |

### Gestion des tokens

Les tokens sont stockés dans `tokens/tokens.json`, dans un dossier monté comme volume Docker pour persister entre les redémarrages. Le dossier est créé automatiquement — aucune initialisation manuelle requise. Les tokens expirés sont automatiquement ignorés par le serveur.

#### Créer un token

```bash
# Durée par défaut : 365 jours
docker run --rm -v $(pwd)/tokens:/app/tokens greenit-mcp \
  --generate-token --name "Alice"

# Durée personnalisée
docker run --rm -v $(pwd)/tokens:/app/tokens greenit-mcp \
  --generate-token --name "Bob" --expires-days 90
```

Le dossier `tokens/` est créé automatiquement au premier appel — aucune initialisation requise.

#### Lister les tokens

```bash
docker run --rm -v $(pwd)/tokens:/app/tokens greenit-mcp \
  --list-tokens
```

Exemple de sortie :

```
ID            Nom                   Créé le       Expire le     Statut
----------------------------------------------------------------------
vpezBq_s      Alice                 2026-04-08    2027-04-08    actif
a1b2c3d4      Bob                   2026-01-01    2026-04-01    EXPIRÉ
```

#### Révoquer un token

```bash
docker run --rm -v $(pwd)/tokens:/app/tokens greenit-mcp \
  --revoke-token <token>
```

### API d'administration des tokens

En mode HTTP, si `ADMIN_TOKEN` est défini, les routes suivantes sont disponibles :

| Méthode | Route | Description |
|---------|-------|-------------|
| `GET` | `/admin/tokens` | Lister tous les tokens |
| `POST` | `/admin/tokens` | Créer un token |
| `GET` | `/admin/tokens/{id}` | Obtenir un token |
| `PATCH` | `/admin/tokens/{id}` | Modifier un token |
| `DELETE` | `/admin/tokens/{id}` | Révoquer un token |

Authentification : `Authorization: Bearer <ADMIN_TOKEN>`.

Exemple :

```bash
# Créer un token
curl -X POST http://localhost:8000/admin/tokens \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "Alice", "expires_days": 365}'

# Lister les tokens
curl http://localhost:8000/admin/tokens \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

#### Structure de tokens.json

```json
{
  "<token>": {
    "client_id": "vpezBq_s",
    "name": "Alice",
    "scopes": ["read"],
    "created_at": 1744000000.0,
    "expires_at": 1775536000.0
  }
}
```

---

## Intégration avec Claude

### Claude Desktop — mode stdio (local)

Éditer `~/.config/Claude/claude_desktop_config.json` (macOS/Linux) ou `%APPDATA%\Claude\claude_desktop_config.json` (Windows) :

```json
{
  "mcpServers": {
    "greenit": {
      "command": "docker",
      "args": ["run", "--rm", "-i", "greenit-mcp"]
    }
  }
}
```

### Claude Desktop — mode HTTP (réseau)

```json
{
  "mcpServers": {
    "greenit": {
      "url": "http://localhost:8000/mcp",
      "headers": {
        "Authorization": "Bearer <ton_token>"
      }
    }
  }
}
```

### Claude Code (CLI) — via script d'installation

Si le serveur est exposé en mode HTTP, utilisez le script d'installation :

```bash
# Installer pour tous les projets (scope user, défaut)
curl -sSL https://<votre-domaine>/install.sh | bash -s -- <TOKEN>

# Installer pour le projet courant uniquement (scope local, dans ~/.claude.json)
curl -sSL https://<votre-domaine>/install.sh | bash -s -- <TOKEN> --local

# Installer pour le projet courant, partageable via git (scope project, crée .mcp.json)
curl -sSL https://<votre-domaine>/install.sh | bash -s -- <TOKEN> --project

# Désinstaller
curl -sSL https://<votre-domaine>/install.sh | bash -s -- --uninstall
```

### Claude Code (CLI) — mode stdio local

```bash
# Ajouter le serveur MCP à la session courante
claude mcp add greenit -- docker run --rm -i greenit-mcp
```

---

## Outils disponibles

| Outil | Description | Paramètres |
|-------|-------------|------------|
| `lister_fiches` | Liste toutes les fiches ou filtre par lifecycle, ressource, impact, priorité | `lifecycle?`, `saved_resource?`, `impact_min?`, `priorite_min?` |
| `fiches_prioritaires` | Fiches triées par score ei+pi décroissant | `impact_min?` (défaut: 4), `priorite_min?` (défaut: 4) |
| `chercher_fiche` | Recherche par mot-clé avec scoring de pertinence | `terme` |
| `comparer_fiches` | Compare plusieurs fiches côte à côte | `fiche_ids` (liste d'IDs, ex: `["RWEB_0051","RWEB_0049"]`) |
| `obtenir_fiche_complete` | Contenu complet d'une fiche (description, validations, principes) | `fiche_id` (ex: `RWEB_0051`) |
| `obtenir_statistiques` | Stats du référentiel (distributions, top 5) | — |
| `lister_lifecycles` | Liste les 7 phases du cycle de vie avec leur nombre de fiches | — |
| `lister_ressources` | Liste les 8 types de ressources sauvegardées avec leur nombre de fiches | — |
| `calculer_ecoindex` | Calcule le score EcoIndex (0-100) et la note (A-G) à partir des métriques mesurées | `dom_nodes`, `requests`, `size_kb`, `url?` |

## Ressources disponibles

| Ressource | Description |
|-----------|-------------|
| `greenit://index` | Liste de toutes les fiches |
| `greenit://fiche/{fiche_id}` | Contenu d'une fiche spécifique |
| `greenit://metadata` | Métadonnées du référentiel |
| `greenit://version` | Version du serveur et des données |

## Endpoints HTTP (Phase 4)

### Accueil et santé (`GET /`)

L'endpoint `/` retourne la page d'accueil avec le statut du serveur et les liens rapides d'installation :

```bash
curl http://localhost:8000/
```

Retourne une page HTML interactive avec :
- Statut du cache GreenIT (nombre de fiches chargées)
- Commande d'installation rapide
- Lien vers la documentation complète

### Documentation interactive (`GET /guide`)

L'endpoint `/guide` supporte la négociation de contenu pour retourner la documentation aux outils en HTML ou JSON :

| Requête | Réponse | Usage |
| --- | --- | --- |
| `GET /guide` (défaut) | HTML | Documentation interactive des outils dans le navigateur |
| `GET /guide` + `Accept: text/html` | HTML | Documentation interactive (explicite) |
| `GET /guide` + `Accept: application/json` | JSON | Métadonnées des outils pour intégration programmatique |

**Exemple avec curl :**

```bash
# Récupérer en HTML (défaut)
curl http://localhost:8000/guide

# Récupérer en JSON
curl -H "Accept: application/json" http://localhost:8000/guide
```

**Structure JSON :**

```json
{
  "tools": [
    {
      "name": "lister_fiches",
      "description": "Liste toutes les fiches ou filtre...",
      "inputSchema": {
        "type": "object",
        "properties": {
          "lifecycle": {"type": "string"},
          "saved_resource": {"type": "string"},
          "impact_min": {"type": "integer"},
          "priorite_min": {"type": "integer"}
        }
      }
    },
    ...
  ]
}
```

### Script d'installation (`GET /install.sh`)

L'endpoint `/install.sh` fournit un script bash pour installer automatiquement le serveur MCP sur Claude Code, Cursor, ou VS Code :

```bash
curl -sSL http://localhost:8000/install.sh | bash -s -- <TOKEN>
```

### Santé du serveur (`GET /health`) — Phase 5

Endpoint de health check prévu pour Phase 5. Actuellement, utilisez `GET /` pour vérifier le statut du serveur.

### Exemples d'utilisation dans Claude

```
"Quelles sont les bonnes pratiques prioritaires du référentiel GreenIT ?"

"Cherche les fiches sur le lazy loading"

"Liste les fiches de la phase développement avec un impact environnemental >= 4"

"Donne-moi le détail complet de la fiche RWEB_0049"

"Compare les fiches RWEB_0049, RWEB_0051 et RWEB_0009"

"Donne moi les bonnes pratiques à appliquer pour réduire l'impact écologique du site greenit.fr"

"Utilise Playwright pour ouvrir https://greenit.fr (viewport 1920×1080), attendre 3 s, scroller
progressivement jusqu'en bas, attendre 3 s, puis mesurer les nœuds DOM, requêtes HTTP et poids
total. Calcule ensuite l'EcoIndex avec calculer_ecoindex."
```

---

## Architecture

**Phase 3 (modularisation) :** Le code a été refactorisé en modules avec une responsabilité unique pour une meilleure maintenabilité et testabilité.

### Structure du projet

```
.
├── Dockerfile
├── docker-compose.yml
├── release.sh
├── .dockerignore
├── README.md
├── CHANGELOG.md
├── files/
│   ├── greenit_mcp.py           # Serveur MCP principal (tools, prompts, resources, startup)
│   ├── data.py                  # Chargement du cache, accès fiches, calcul EcoIndex
│   ├── auth.py                  # Gestion des tokens (generate, list, revoke, verify)
│   ├── routes.py                # Routes HTTP publiques (/, /install.sh, /guide)
│   ├── _helpers.py              # Fonctions de validation partagées
│   ├── greenit_cache.json       # 119 fiches GreenIT (données embarquées)
│   ├── greenit_metadata.json    # Métadonnées (langues, versions)
│   └── preparer_donnees.py      # Script de mise à jour des données
└── tests/
    └── test_tools.py            # Tests pytest des outils MCP (207 tests)

tokens/                          # Créé automatiquement au premier --generate-token
└── tokens.json                  # Tokens (non embarqué dans l'image)
```

### Modules clés

- **greenit_mcp.py** : Orchestre le serveur MCP, exporte les outils et ressources
- **data.py** : Source unique pour le chargement du cache, l'accès aux fiches, le calcul EcoIndex et les statistiques
  - _Note Phase 3 :_ `ecoindex.py` fusionné dans ce module pour meilleure maintenabilité
- **auth.py** : Gestion des tokens (génération, listage, révocation, validation)
- **routes.py** : Gestionnaires des endpoints HTTP (/, /install.sh, /guide)
- **_helpers.py** : Fonctions partagées de validation (lifecycles, ressources, scores)

**Phase 4 complétée :**
- **GET /guide** : endpoint de documentation avec négociation de contenu
  - Accept: text/html → retourne une page HTML interactive
  - Accept: application/json → retourne les métadonnées des outils en JSON
- **207 tests** : couverture complète incluant endpoints HTTP et content negotiation

## Tests

**Phase 4 :** 207 tests passant (outils MCP, endpoints HTTP, négociation de contenu, validations).

```bash
# Localement (avec Python + fastmcp + httpx installés)
python -m pytest tests/ -v

# Via Docker
docker build -t greenit-mcp-test .
docker run --rm -v "$(pwd)/tests:/app/tests" --entrypoint python greenit-mcp-test -m pytest tests/ -v

# Vérifier le nombre de tests
python -m pytest tests/ --collect-only -q
```

## Docker Compose

For detailed quick-start instructions including token generation and verification, see the "Quick Start with Docker Compose" section above.

Additional commands:

```bash
# Rebuilder et redéployer une nouvelle version
docker compose down && docker compose build --no-cache && docker compose up -d

# Voir les logs
docker compose logs -f

# Arrêter le serveur
docker compose down
```

## Healthcheck

Le serveur expose un flag `--health` utilisé par le `HEALTHCHECK` Dockerfile et `docker-compose.yml` :

```bash
# Tester manuellement (exit 0 si OK, 1 si cache vide)
docker run --rm greenit-mcp --health
# Sortie: OK: 119 fiches chargées
```

## Release

```bash
# Créer une release (bumpe la version et crée un tag git)
./release.sh 1.1.0

# Pousser ensuite
git push && git push origin v1.1.0
```

### Structure d'une fiche

```json
{
  "num": "RWEB_0051",
  "title": "Utiliser le chargement paresseux",
  "shortDescription": "...",
  "description": "## Description\n\n...",
  "lifecycle": "3-developement",
  "environmental_impact": 5,
  "priority_implementation": 5,
  "saved_resources": ["cpu", "network", "requests"],
  "url": "https://rweb.greenit.fr/fr/fiches/0051"
}
```

Les champs `environmental_impact` et `priority_implementation` sont notés de 1 à 5.

---

## Mettre à jour les données

Les données sont embarquées dans l'image Docker. Pour les mettre à jour :

```bash
# Télécharger les données fraîches depuis l'API GreenIT
cd files/
python3 preparer_donnees.py --telecharger

# Rebuilder l'image
docker build -t greenit-mcp .
```

---

## Sécurité

- En mode `http`, toute requête sans token valide reçoit une réponse `401 Unauthorized`.
- Les tokens expirés sont automatiquement rejetés sans avoir à les supprimer.
- Les tokens sont générés avec `secrets.token_urlsafe(32)` (256 bits d'entropie).
- `tokens/tokens.json` n'est pas embarqué dans l'image Docker — il reste sur l'hôte via volume, créé automatiquement au premier appel.
- Les données GreenIT sont en lecture seule — le serveur ne modifie aucun fichier en production.
- Aucune donnée utilisateur n'est collectée ni transmise.
