# RGAA MCP Server

> Faisant partie du monorepo [mcp-nr](../). Pour builder, utiliser `docker build -f rgaa/Dockerfile .` depuis la racine du monorepo.

Serveur [MCP (Model Context Protocol)](https://modelcontextprotocol.io) donnant accès au référentiel [RGAA 4.2.1](https://accessibilite.numerique.gouv.fr/methode/criteres-et-tests/) (Référentiel Général d'Amélioration de l'Accessibilité) depuis Claude (Desktop, Code, ou tout client MCP).

## Fonctionnalités

- **10 outils MCP** : lister, rechercher, analyser du HTML, générer des checklists, calculer le taux de conformité, et plus
- **4 ressources** : version, index, métadonnées, critère individuel
- **Deux modes de transport** : stdio (local) ou HTTP avec authentification par token Bearer
- **Gestion des tokens** : création avec nom et expiration, liste, révocation — stockage dans `tokens/tokens.json` (volume Docker, créé automatiquement)
- **Données embarquées** : 106 critères RGAA 4.2.1, prêts à l'emploi sans connexion externe
- **Analyse statique HTML** : détection de violations sur les thèmes images, cadres, tableaux, liens, obligatoire, structure, formulaires, navigation

---

## Installation

### Prérequis

- **Python 3.13** (required for full compatibility with fastmcp 3.2.4+)
- **pip** (Python package manager, included with Python 3.13+)
- **Docker** and **docker-compose** (for containerized deployment)

### Local Development Setup (optional, for running tests or development)

For local testing without Docker:

```bash
# 1. Clone the repository
git clone https://github.com/anthropics/mcp-rgaa.git
cd mcp-rgaa

# 2. Create a Python virtual environment
python3.13 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Install development dependencies (for tests)
pip install -e ".[dev]"

# 5. Run tests to verify installation
python -m pytest tests/ -v
```

### Docker Image Build

For containerized deployment:

```bash
# 1. Build the Docker image (creates rgaa-mcp image)
docker build -f rgaa/Dockerfile -t rgaa-mcp .

# 2. Verify the image was built successfully
docker images | grep rgaa-mcp
```

---

## Getting Started

### Quick Start with Docker Compose (recommended for HTTP mode)

```bash
# 1. Start the server in HTTP mode (port 8001)
docker compose up -d

# 2. Verify the server is running
docker compose ps
# Expected output: rgaa service with "Up" status

# 3. Check the server is healthy
curl http://localhost:8001/
# Expected output: HTML page with "OK" status and number of loaded criteria

# 4. Generate an access token
docker run --rm -v $(pwd)/tokens:/app/tokens rgaa-mcp \
  --generate-token --name "your-name"
# Save the generated token (starts with random characters)

# 5. Verify token works
curl -H "Authorization: Bearer <your-token>" \
  http://localhost:8001/mcp

# 6. View server logs
docker compose logs -f
```

### Local Development Mode (stdio — embedded in Claude)

For testing with Claude Desktop or Claude Code locally:

```bash
# 1. Build the image (one-time)
docker build -f rgaa/Dockerfile -t rgaa-mcp .

# 2. Start in stdio mode (reads from stdin, writes to stdout)
docker run --rm -i rgaa-mcp

# This mode is used when configured in Claude Desktop config or Claude Code MCP settings
```

### Stopping the Server

```bash
# Stop docker compose service
docker compose down

# Stop and remove all traces (including volumes)
docker compose down -v
```

---

## Configuration

### Variables d'environnement

| Variable                | Défaut    | Description                                                                                       |
| ----------------------- | --------- | ------------------------------------------------------------------------------------------------- |
| `MCP_TRANSPORT`         | `stdio`   | Mode de transport : `stdio` ou `http`                                                             |
| `MCP_HOST`              | `0.0.0.0` | Adresse d'écoute (mode `http`)                                                                    |
| `MCP_PORT`              | `8000`    | Port d'écoute (mode `http`)                                                                       |
| `MCP_BASE_URL`          | _(auto)_  | URL publique du serveur. À définir si derrière un reverse proxy (ex : `https://mcp.example.com`). |
| `MCP_TOKEN_REQUEST_URL` | _(vide)_  | URL du formulaire de demande de token, affichée sur la page d'accueil.                            |
| `ADMIN_TOKEN`           | _(vide)_  | Token admin pour l'API de gestion des tokens (HTTP uniquement ; vide = API désactivée)            |

### Gestion des tokens

Les tokens sont stockés dans `tokens/tokens.json`, dans un dossier monté comme volume Docker pour persister entre les redémarrages. Le dossier est créé automatiquement — aucune initialisation manuelle requise. Les tokens expirés sont automatiquement ignorés par le serveur.

#### Créer un token

```bash
# Durée par défaut : 365 jours
docker run --rm -v $(pwd)/tokens:/app/tokens rgaa-mcp \
  --generate-token --name "Alice"

# Durée personnalisée
docker run --rm -v $(pwd)/tokens:/app/tokens rgaa-mcp \
  --generate-token --name "Bob" --expires-days 90
```

#### Lister les tokens

```bash
docker run --rm -v $(pwd)/tokens:/app/tokens rgaa-mcp \
  --list-tokens
```

Exemple de sortie :

```
ID            Nom                   Créé le       Expire le     Statut
----------------------------------------------------------------------
vpezBq_s      Alice                 2026-04-18    2027-04-18    actif
a1b2c3d4      Bob                   2026-01-01    2026-04-01    EXPIRÉ
```

#### Révoquer un token

```bash
docker run --rm -v $(pwd)/tokens:/app/tokens rgaa-mcp \
  --revoke-token <token>
```

---

## Gestion des tokens via API (HTTP)

En mode HTTP, si `ADMIN_TOKEN` est défini, les endpoints `/admin/tokens` sont disponibles.

**Lister les tokens :**

```bash
curl -H "Authorization: Bearer $ADMIN_TOKEN" http://localhost:8001/admin/tokens
```

**Créer un token :**

```bash
curl -X POST -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "Alice", "expires_days": 365}' \
  http://localhost:8001/admin/tokens
```

**Modifier un token (renommer ou prolonger) :**

```bash
curl -X PATCH -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"expires_days": 180}' \
  http://localhost:8001/admin/tokens/<id>
```

**Révoquer un token :**

```bash
curl -X DELETE -H "Authorization: Bearer $ADMIN_TOKEN" \
  http://localhost:8001/admin/tokens/<id>
```

> **Note :** si le serveur démarre sans token existant, l'auth MCP n'est pas activée. Les tokens créés via l'API admin prennent effet immédiatement si le serveur a démarré avec des tokens existants ; autrement, un redémarrage est requis.

---

## Intégration avec Claude

### Claude Desktop — mode stdio (local)

Éditer `~/.config/Claude/claude_desktop_config.json` (macOS/Linux) ou `%APPDATA%\Claude\claude_desktop_config.json` (Windows) :

```json
{
  "mcpServers": {
    "rgaa": {
      "command": "docker",
      "args": ["run", "--rm", "-i", "rgaa-mcp"]
    }
  }
}
```

### Claude Desktop — mode HTTP (réseau)

```json
{
  "mcpServers": {
    "rgaa": {
      "url": "http://localhost:8001/mcp",
      "headers": {
        "Authorization": "Bearer <ton_token>"
      }
    }
  }
}
```

### Claude Code (CLI) — mode stdio local

```bash
claude mcp add rgaa -- docker run --rm -i rgaa-mcp
```

### Claude Code (CLI) — via script d'installation

Si le serveur est exposé en mode HTTP :

```bash
# Installer pour tous les projets (scope user, défaut)
curl -sSL https://<votre-domaine>/install.sh | bash -s -- <TOKEN>

# Installer pour le projet courant uniquement
curl -sSL https://<votre-domaine>/install.sh | bash -s -- <TOKEN> --local

# Installer pour le projet courant, partageable via git
curl -sSL https://<votre-domaine>/install.sh | bash -s -- <TOKEN> --project

# Désinstaller
curl -sSL https://<votre-domaine>/install.sh | bash -s -- --uninstall
```

---

## Outils disponibles

### Vue d'ensemble

**10 outils MCP** pour interroger le référentiel, analyser des pages, générer des checklists et calculer la conformité.

| Outil                  | Description                                                                         | Paramètres                                        |
| ---------------------- | ----------------------------------------------------------------------------------- | ------------------------------------------------- | -------- | ----------------- |
| `rgaa_lister_criteres` | Liste tous les critères RGAA avec filtres optionnels (thème, niveau WCAG)           | `theme?: int`, `niveau_wcag?: "A"\|"AA"\|"AAA"`   |
| `rgaa_obtenir_critere` | Récupère le contenu complet d'un critère (tests, conditions, références WCAG)       | `id: str` (ex: `"1.1"`)                           |
| `rgaa_chercher`        | Recherche par mot-clé dans les critères et/ou le glossaire RGAA                     | `query: str`, `scope?: ["criteres", "glossaire"]` |
| `rgaa_glossaire`       | Retourne la définition d'un terme du glossaire avec correspondance approchante      | `terme: str`                                      |
| `rgaa_statistiques`    | Retourne les statistiques du référentiel (répartition par thème, niveau WCAG)       | —                                                 |
| `rgaa_analyser`        | Analyse statique d'une URL et détecte les violations RGAA (8 thèmes automatisables) | `url: str`, `themes?: list[int]`                  |
| `rgaa_checklist`       | Génère une checklist de tests manuels avec outils recommandés                       | `themes?: list[int]`, `criteres?: list[str]`      |
| `rgaa_taux_conformite` | Calcule le taux de conformité officiel RGAA (C/(C+NC)×100) à partir d'un audit      | `resultats: dict` {`id: "C"                       | "NC"     | "NA"`}            |
| `rgaa_types_audit`     | Liste les 3 types d'audit (complet, rapide, complémentaire) et leurs statuts légaux | —                                                 |
| `rgaa_criteres_audit`  | Retourne la liste des critères pour un type d'audit spécifique                      | `type: "complet"                                  | "rapide" | "complementaire"` |

## Ressources disponibles

| Ressource                      | Description                                                               |
| ------------------------------ | ------------------------------------------------------------------------- |
| `rgaa://version`               | Version du serveur et des données                                         |
| `rgaa://index`                 | Index léger de tous les critères (id, titre, niveau)                      |
| `rgaa://criteres/{critere_id}` | Contenu complet d'un critère spécifique                                   |
| `rgaa://metadata`              | Métadonnées du référentiel (langues, source, nb critères, automatisables) |

## Endpoints HTTP (Phase 4)

### Accueil et santé (`GET /`)

L'endpoint `/` retourne la page d'accueil avec le statut du serveur et les liens rapides d'installation :

```bash
curl http://localhost:8001/
```

Retourne une page HTML interactive avec :

- Statut du cache RGAA (nombre de critères chargés)
- Commande d'installation rapide
- Lien vers la documentation complète

### Documentation interactive (`GET /guide`)

L'endpoint `/guide` supporte la négociation de contenu pour retourner la documentation aux outils en HTML ou JSON :

| Requête                                   | Réponse | Usage                                                   |
| ----------------------------------------- | ------- | ------------------------------------------------------- |
| `GET /guide` (défaut)                     | HTML    | Documentation interactive des outils dans le navigateur |
| `GET /guide` + `Accept: text/html`        | HTML    | Documentation interactive (explicite)                   |
| `GET /guide` + `Accept: application/json` | JSON    | Métadonnées des outils pour intégration programmatique  |

**Exemple avec curl :**

```bash
# Récupérer en HTML (défaut)
curl http://localhost:8001/guide

# Récupérer en JSON
curl -H "Accept: application/json" http://localhost:8001/guide
```

**Structure JSON :**

```json
{
  "tools": [
    {
      "name": "rgaa_lister_criteres",
      "description": "Liste tous les critères RGAA...",
      "inputSchema": {
        "type": "object",
        "properties": {
          "theme": {"type": "integer"},
          "niveau_wcag": {"type": "string", "enum": ["A", "AA", "AAA"]}
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
curl -sSL http://localhost:8001/install.sh | bash -s -- <TOKEN>
```

### Santé du serveur (`GET /health`) — Phase 5

Endpoint de health check prévu pour Phase 5. Actuellement, utilisez `GET /` pour vérifier le statut du serveur.

### Exemples d'utilisation dans Claude

#### Recherche et consultation

```
"Liste tous les critères du thème 1 (Images)"
→ rgaa_lister_criteres(theme=1)

"Obtiens le détail complet du critère 1.1"
→ rgaa_obtenir_critere(id="1.1")

"Cherche les critères sur le contraste des couleurs"
→ rgaa_chercher(query="contraste")

"Qu'est-ce que la 'restitution' dans le glossaire RGAA ?"
→ rgaa_glossaire(terme="restitution")

"Combien de critères RGAA existent ? Comment sont-ils répartis ?"
→ rgaa_statistiques()
```

#### Audit et conformité

```
"Analyse l'accessibilité de https://example.com"
→ rgaa_analyser(url="https://example.com")

"Analyse l'accessibilité de https://example.com pour les thèmes 1 (Images) et 2 (Cadres)"
→ rgaa_analyser(url="https://example.com", themes=[1, 2])

"Génère une checklist de tests manuels pour le thème 6 (Formulaires)"
→ rgaa_checklist(themes=[6])

"Sur 42 critères applicables, 30 sont conformes et 12 non conformes. Quel est le taux ?"
→ rgaa_taux_conformite(resultats={...})
```

#### Types d'audit

```
"Quels types d'audit RGAA existent et lequel est légalement obligatoire ?"
→ rgaa_types_audit()

"Donne-moi la liste des critères de l'audit rapide RGAA"
→ rgaa_criteres_audit(type="rapide")

"Donne-moi la liste des critères de l'audit complet RGAA"
→ rgaa_criteres_audit(type="complet")
```

---

## Structure du projet

### Architecture modulaire (Phase 3)

Le projet suit une architecture modulaire avec séparation des responsabilités :

```
.
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
├── README.md
├── CHANGELOG.md
├── TODO.md
├── files/
│   ├── rgaa_mcp.py              # Serveur MCP principal (10 outils, 4 ressources, startup)
│   ├── data.py                  # Chargement cache RGAA, accès critères/glossaire/thèmes
│   ├── _helpers.py              # Validation (themes, ranges) — réutilisable dans les outils
│   ├── auth.py                  # Gestion tokens (generate, list, revoke, verify)
│   ├── routes.py                # Routes HTTP publiques (/, /install.sh, /guide)
│   ├── analyseur.py             # Analyseur statique HTML (8 thèmes automatisables)
│   ├── rgaa_cache.json          # 106 critères RGAA 4.2.1 (données embarquées)
│   ├── audit_types.json         # Définition des 3 types d'audit
│   └── preparer_donnees.py      # Script de mise à jour depuis RGAA officiel
└── tests/                       # Suite de tests pytest complète (253 tests)
    ├── test_tools.py            # Tests des 10 outils MCP
    ├── test_analyseur.py        # Tests de l'analyseur HTML
    ├── test_referentiel.py      # Tests du référentiel et recherche
    └── test_conformite.py       # Tests du calcul de conformité

tokens/                          # Créé automatiquement au premier --generate-token
└── tokens.json                  # Tokens persistants (volume Docker, non embarqué)
```

**Points clés de Phase 3 :**

- `_helpers.py` : validation centralisée réutilisée par les outils
- `auth.py` : gestion complète des tokens (CLI + API)
- `routes.py` : routes HTTP publiques isolées (/, /install.sh, /guide)
- `data.py` : chargement/accès au cache RGAA
- **Architecture modulaire** : séparation des responsabilités pour meilleure maintenabilité

**Phase 4 complétée :**

- **GET /** : homepage avec statut du serveur et liens rapides
- **GET /guide** : endpoint de documentation avec négociation de contenu
  - Accept: text/html → retourne une page HTML interactive
  - Accept: application/json → retourne les métadonnées des outils en JSON
- **GET /install.sh** : script d'installation multi-clients (Claude Code, Cursor, VS Code)
- **253 tests** : couverture complète incluant endpoints HTTP et content negotiation

## Tests

**Phase 4 :** 253 tests passant (outils MCP, analyseur, référentiel, conformité, endpoints HTTP, négociation de contenu).

```bash
# Localement (avec Python + fastmcp installés)
pip install -e ".[dev]"
python -m pytest tests/ -v

# Via Docker
docker build -f rgaa/Dockerfile -t rgaa-mcp-test .
docker run --rm -v "$(pwd)/tests:/app/tests" --entrypoint python rgaa-mcp-test -m pytest tests/ -v

# Vérifier le nombre de tests
python -m pytest tests/ --collect-only -q
```

## Docker Compose

For detailed quick-start instructions including token generation and verification, see the "Quick Start with Docker Compose" section above.

Additional commands:

```bash
# Rebuilder et redéployer avec nouvelle version
docker compose down && docker compose build --no-cache && docker compose up -d

# Voir les logs
docker compose logs -f

# Arrêter le serveur
docker compose down
```

## Healthcheck

```bash
# Tester manuellement (exit 0 si OK, 1 si cache vide)
docker run --rm rgaa-mcp --health
# Sortie: OK: 106 critères chargés
```

## Release

```bash
# Créer une release (bumpe la version et crée un tag git)
./release.sh 1.2.0

# Pousser ensuite
git push && git push origin v1.2.0
```

---

## Mettre à jour les données

Les données sont embarquées dans l'image Docker. Pour les mettre à jour :

```bash
# Télécharger les données fraîches depuis le dépôt RGAA officiel
cd files/
python3 preparer_donnees.py --telecharger

# Rebuilder l'image
docker build -f rgaa/Dockerfile -t rgaa-mcp .
```

---

## Sécurité

- En mode `http`, toute requête sans token valide reçoit une réponse `401 Unauthorized`.
- Les tokens expirés sont automatiquement rejetés sans avoir à les supprimer.
- Les tokens sont générés avec `secrets.token_urlsafe(32)` (256 bits d'entropie).
- `tokens/tokens.json` n'est pas embarqué dans l'image Docker — il reste sur l'hôte via volume.
- Les données RGAA sont en lecture seule — le serveur ne modifie aucun fichier en production.
- Aucune donnée utilisateur n'est collectée ni transmise.
