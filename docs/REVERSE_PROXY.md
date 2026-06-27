# Reverse proxy — Caddy et Traefik

Les trois MCPs (greenit, rgaa, rgesn) sont prêts pour une auto-découverte via labels Docker. Ce guide couvre la mise en place avec **Caddy** (`caddy-docker-proxy`) ou **Traefik** v3.

> Utiliser l'un **ou** l'autre — pas les deux simultanément.

---

## Principe

Chaque `docker-compose.yml` déclare :

- un réseau externe `proxy` (partagé avec le reverse proxy)
- des labels pour l'auto-découverte Traefik et Caddy
- la variable `DOMAIN` pour construire les sous-domaines

```
greenit.example.com  →  greenit:8000
rgaa.example.com     →  rgaa:8000
rgesn.example.com    →  rgesn:8000
```

---

## Prérequis communs

**1. Créer le réseau Docker partagé (une seule fois sur le serveur) :**

```bash
docker network create proxy
```

**2. Configurer le domaine dans chaque `.env` :**

```bash
# greenit/.env, rgaa/.env, rgesn/.env
DOMAIN=example.com
MCP_BASE_URL=https://greenit.example.com   # adapter par service
```

> `MCP_BASE_URL` est affiché dans les pages `/guide` et les scripts d'installation. Il doit pointer vers l'URL publique finale du service.

---

## Caddy (caddy-docker-proxy)

[`caddy-docker-proxy`](https://github.com/lucaslorentz/caddy-docker-proxy) lit les labels Docker des conteneurs et génère la configuration Caddy dynamiquement. TLS Let's Encrypt est automatique.

### docker-compose.yml pour Caddy

Créer `caddy/docker-compose.yml` (ou à la racine du serveur) :

```yaml
services:
  caddy:
    image: lucaslorentz/caddy-docker-proxy:ci-alpine
    ports:
      - "80:80"
      - "443:443"
    environment:
      - CADDY_INGRESS_NETWORKS=proxy
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - caddy_data:/data
    networks:
      - proxy
    restart: unless-stopped

volumes:
  caddy_data:

networks:
  proxy:
    external: true
```

### Lancement

```bash
# Lancer Caddy
docker compose -f caddy/docker-compose.yml up -d

# Lancer les MCPs (dans l'ordre ou ensemble)
docker compose -f greenit/docker-compose.yml up -d
docker compose -f rgaa/docker-compose.yml    up -d
docker compose -f rgesn/docker-compose.yml   up -d
```

Caddy détecte les conteneurs actifs via les labels et configure les routes automatiquement. Les certificats TLS sont provisionnés au premier accès.

### Labels utilisés (déjà dans chaque docker-compose.yml)

```yaml
labels:
  - "caddy=greenit.${DOMAIN}"
  - "caddy.reverse_proxy={{upstreams 8000}}"
```

### Vérification

```bash
curl https://greenit.example.com/
curl https://rgaa.example.com/
curl https://rgesn.example.com/
```

---

## Traefik v3

Traefik surveille l'API Docker et configure ses routes à partir des labels des conteneurs. TLS Let's Encrypt est géré via un `certificatesResolver`.

### docker-compose.yml pour Traefik

Créer `traefik/docker-compose.yml` (ou à la racine du serveur) :

```yaml
services:
  traefik:
    image: traefik:v3
    command:
      - "--providers.docker=true"
      - "--providers.docker.exposedbydefault=false"
      - "--providers.docker.network=proxy"
      - "--entrypoints.web.address=:80"
      - "--entrypoints.web.http.redirections.entrypoint.to=websecure"
      - "--entrypoints.web.http.redirections.entrypoint.scheme=https"
      - "--entrypoints.websecure.address=:443"
      - "--certificatesresolvers.letsencrypt.acme.tlschallenge=true"
      - "--certificatesresolvers.letsencrypt.acme.email=admin@example.com"
      - "--certificatesresolvers.letsencrypt.acme.storage=/letsencrypt/acme.json"
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - traefik_letsencrypt:/letsencrypt
    networks:
      - proxy
    restart: unless-stopped

volumes:
  traefik_letsencrypt:

networks:
  proxy:
    external: true
```

> Remplacer `admin@example.com` par une adresse email réelle — Let's Encrypt l'utilise pour les notifications d'expiration.

### Activer le resolver Let's Encrypt dans les labels

Les labels dans chaque `docker-compose.yml` déclarent `tls=true` mais ne précisent pas le resolver. Ajouter dans chaque `.env` ou directement dans les labels :

```yaml
# À ajouter dans les labels de chaque service si TLS automatique Let's Encrypt est voulu
- "traefik.http.routers.greenit.tls.certresolver=letsencrypt"
```

Ou en l'absence de DNS public (test local), supprimer les labels `tls` pour fonctionner en HTTP simple.

### Labels utilisés (déjà dans chaque docker-compose.yml)

```yaml
labels:
  - "traefik.enable=true"
  - "traefik.http.routers.greenit.rule=Host(`greenit.${DOMAIN}`)"
  - "traefik.http.routers.greenit.entrypoints=websecure"
  - "traefik.http.routers.greenit.tls=true"
  - "traefik.http.services.greenit.loadbalancer.server.port=8000"
```

### Lancement

```bash
# Lancer Traefik
docker compose -f traefik/docker-compose.yml up -d

# Lancer les MCPs
docker compose -f greenit/docker-compose.yml up -d
docker compose -f rgaa/docker-compose.yml    up -d
docker compose -f rgesn/docker-compose.yml   up -d
```

### Dashboard Traefik (optionnel)

Pour activer le dashboard de supervision :

```yaml
command:
  - "--api.dashboard=true"
  # ...
labels:
  - "traefik.enable=true"
  - "traefik.http.routers.traefik.rule=Host(`traefik.example.com`)"
  - "traefik.http.routers.traefik.service=api@internal"
  - "traefik.http.routers.traefik.tls.certresolver=letsencrypt"
```

### Vérification

```bash
curl https://greenit.example.com/
curl https://rgaa.example.com/
curl https://rgesn.example.com/
```

---

## Variables d'environnement à configurer par service

| Variable       | Valeur attendue               | Description                                         |
| -------------- | ----------------------------- | --------------------------------------------------- |
| `DOMAIN`       | `example.com`                 | Domaine de base pour les sous-domaines              |
| `MCP_BASE_URL` | `https://greenit.example.com` | URL publique du service (liens /guide, /install.sh) |
| `ADMIN_TOKEN`  | token aléatoire long          | Active l'API d'admin des tokens (`/admin/tokens`)   |

Exemple de `.env` pour greenit :

```bash
DOMAIN=example.com
MCP_BASE_URL=https://greenit.example.com
ADMIN_TOKEN=$(openssl rand -hex 32)
```

---

## Test local sans DNS public

Pour tester avec des sous-domaines locaux, ajouter les entrées dans `/etc/hosts` :

```
127.0.0.1  greenit.localhost
127.0.0.1  rgaa.localhost
127.0.0.1  rgesn.localhost
```

Et dans chaque `.env` :

```bash
DOMAIN=localhost
MCP_BASE_URL=http://greenit.localhost
```

Supprimer les labels `tls` des `docker-compose.yml` et utiliser l'entrypoint `web` (port 80) à la place de `websecure`.
