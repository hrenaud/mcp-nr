# Guide de déploiement — MCP Numérique Responsable

Ce guide s'adresse aux développeurs, architectes et DevOps qui déploient les MCPs sur un serveur partagé.

## Architecture

Trois services Docker indépendants, chacun exposant un serveur MCP en mode HTTP :

| Service | Port externe | Référentiel                  |
| ------- | ------------ | ---------------------------- |
| greenit | 8000         | GreenIT 119 bonnes pratiques |
| rgaa    | 8001         | RGAA 4.2.1 — 106 critères    |
| rgesn   | 8002         | RGESN 2024 — 78 critères     |

Chaque service gère ses propres tokens dans un volume Docker dédié.

## Déploiement

### Prérequis

- Docker Engine 24+ et Docker Compose v2
- Ports 8000, 8001, 8002 disponibles (ou adapter dans les docker-compose.yml)
- Cloner ce dépôt sur le serveur

### Construire et lancer les services

Les Dockerfiles se buildent **depuis la racine du monorepo** :

```bash
# Build des trois images
docker build -f greenit/Dockerfile -t greenit-mcp .
docker build -f rgaa/Dockerfile    -t rgaa-mcp .
docker build -f rgesn/Dockerfile   -t rgesn-mcp .

# Lancer chaque service (chacun a son propre docker-compose.yml)
docker compose -f greenit/docker-compose.yml up -d
docker compose -f rgaa/docker-compose.yml    up -d
docker compose -f rgesn/docker-compose.yml   up -d
```

En développement local, un script raccourci est disponible à la racine :

```bash
./local-build.sh   # build + up greenit et rgaa
```

Pour lancer les trois en une commande, créez un `docker-compose.override.yml` à la racine ou utilisez un orchestrateur.

### Vérification

```bash
curl http://localhost:8000/   # greenit — page d'accueil
curl http://localhost:8001/   # rgaa
curl http://localhost:8002/   # rgesn
```

## Variables d'environnement

À configurer dans le `docker-compose.yml` de chaque service ou via un fichier `.env` :

| Variable                | Défaut    | Description                                                                 |
| ----------------------- | --------- | --------------------------------------------------------------------------- |
| `MCP_TRANSPORT`         | `stdio`   | `http` pour le mode serveur                                                 |
| `MCP_HOST`              | `0.0.0.0` | Adresse d'écoute interne                                                    |
| `MCP_PORT`              | `8000`    | Port interne (doit correspondre au mapping Docker)                          |
| `MCP_BASE_URL`          | auto      | URL publique si derrière un reverse proxy — critique pour les liens générés |
| `MCP_TOKEN_REQUEST_URL` | vide      | URL du formulaire de demande de token (affiché sur la page d'accueil)       |
| `ADMIN_TOKEN`           | vide      | Token admin pour l'API de gestion des tokens (voir ci-dessous)              |

**Auth HTTP :** l'authentification est automatique. Si le fichier `tokens/tokens.json` contient des tokens valides, l'accès HTTP est protégé par un token Bearer. Si le fichier est vide ou inexistant, l'accès est ouvert. Il n'existe pas de contrôle explicite pour forcer ou désactiver l'auth indépendamment des tokens.

**Exemple** pour rgaa derrière un reverse proxy :

```yaml
environment:
  MCP_TRANSPORT: http
  MCP_BASE_URL: https://mcp.example.com/rgaa
  MCP_TOKEN_REQUEST_URL: https://forms.example.com/demande-acces
  ADMIN_TOKEN: un-secret-tres-long-a-generer
```

## Gestion des tokens

L'authentification repose sur des Bearer tokens. Les tokens sont stockés dans le volume Docker de chaque service (`tokens/tokens.json`), jamais dans l'image.

### Générer un token initial (CLI)

```bash
# Pour greenit
docker run --rm -v greenit_tokens:/app/tokens greenit-mcp \
  --generate-token --name "alice"

# Pour rgaa
docker run --rm -v rgaa_tokens:/app/tokens rgaa-mcp \
  --generate-token --name "alice"
```

La commande affiche le token à transmettre à l'utilisateur. Il ne peut pas être récupéré ensuite.

### API admin (mode HTTP uniquement)

Si `ADMIN_TOKEN` est défini, une API REST de gestion des tokens est disponible.

**Lister les tokens actifs :**

```bash
curl -H "Authorization: Bearer $ADMIN_TOKEN" http://localhost:8001/admin/tokens
```

**Créer un token :**

```bash
curl -X POST http://localhost:8001/admin/tokens \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "alice", "expires_days": 365}'
```

Réponse :

```json
{
  "id": "abc123...",
  "token": "le-token-a-transmettre-a-lutilisateur",
  "name": "alice",
  "expires_at": "2027-06-22T..."
}
```

**Révoquer un token :**

```bash
curl -X DELETE http://localhost:8001/admin/tokens/<id> \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

**Endpoints disponibles :**

| Méthode  | Endpoint             | Action                     |
| -------- | -------------------- | -------------------------- |
| `GET`    | `/admin/tokens`      | Lister tous les tokens     |
| `POST`   | `/admin/tokens`      | Créer un token             |
| `GET`    | `/admin/tokens/<id>` | Détail d'un token          |
| `PATCH`  | `/admin/tokens/<id>` | Modifier (nom, expiration) |
| `DELETE` | `/admin/tokens/<id>` | Révoquer                   |

L'API renvoie 503 si `ADMIN_TOKEN` n'est pas défini, 401 si le token admin est incorrect.

## Reverse proxy (HTTPS)

Les trois services sont prêts pour une auto-découverte via labels Docker par **Caddy** ou **Traefik**.

Voir [REVERSE_PROXY.md](REVERSE_PROXY.md) pour le guide complet : réseau partagé, docker-compose du proxy, TLS Let's Encrypt, et test local.

Définir `MCP_BASE_URL` avec l'URL publique finale de chaque service pour que les liens générés dans `/guide` et `/install.sh` soient corrects.

## Health checks

Chaque service expose un health check via le flag `--health` :

```bash
docker run --rm greenit-mcp --health
# {"status": "ok", "version": "2.5.1"}
```

Les `docker-compose.yml` individuels incluent déjà un `healthcheck` configuré.

## Mode stdio — usage local sans serveur

Pour un usage individuel sur poste, Claude peut lancer les MCPs directement via Docker sans déploiement serveur. Chaque requête démarre et arrête un conteneur — moins efficace qu'un serveur permanent, mais sans infrastructure à gérer.

**Prérequis :** Docker installé et démarré sur la machine de l'utilisateur, et les images buildées ou disponibles dans un registry.

```bash
# Build local (depuis la racine du dépôt)
docker build -f greenit/Dockerfile -t greenit-mcp .
docker build -f rgaa/Dockerfile    -t rgaa-mcp .
```

**Configuration Claude Desktop** :

```json
{
  "mcpServers": {
    "greenit": {
      "command": "docker",
      "args": ["run", "--rm", "-i", "greenit-mcp"]
    },
    "rgaa": {
      "command": "docker",
      "args": ["run", "--rm", "-i", "rgaa-mcp"]
    }
  }
}
```

**Claude Code (CLI)** :

```bash
claude mcp add greenit -- docker run --rm -i greenit-mcp
claude mcp add rgaa -- docker run --rm -i rgaa-mcp
```

En mode stdio, aucune authentification n'est requise.

## Releases et versioning

Les versions des trois MCPs sont synchronisées via le script `release.sh` à la racine :

```bash
# Vérifier les CHANGELOGs de chaque MCP, puis :
./release.sh 1.0.0
git push && git push origin v1.0.0
```

Le script bumpe `VERSION` dans les trois `*_mcp.py` et `pyproject.toml`, crée un commit et un tag unifié `v<version>`. Le workflow CI se déclenche automatiquement sur le tag pour builder et publier les images Docker.
