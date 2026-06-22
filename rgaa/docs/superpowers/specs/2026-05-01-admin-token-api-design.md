# Admin Token API — Design Spec

**Date :** 2026-05-01  
**Statut :** approuvé

## Contexte

La gestion des tokens d'accès au serveur MCP RGAA est aujourd'hui uniquement possible via CLI (`--generate-token`, `--list-tokens`, `--revoke-token`), ce qui nécessite un accès shell dans le container Docker. Ce design ajoute une API HTTP d'administration pour permettre la gestion des tokens à distance, utilisable par des humains (curl, scripts) et des systèmes automatisés (CI/CD, onboarding).

## Périmètre

- Disponible uniquement en mode `MCP_TRANSPORT=http`
- Activée uniquement si la variable d'environnement `ADMIN_TOKEN` est définie
- Rechargement dynamique des tokens sans redémarrage du serveur
- Aucun impact sur le mode stdio ni sur les routes publiques existantes

## Architecture

Trois fichiers modifiés, aucun ajouté :

```
auth.py      — DynamicTokenVerifier (remplace construire_verifier / StaticTokenVerifier)
routes.py    — 5 endpoints admin + helper de vérification auth admin
rgaa_mcp.py  — câblage du DynamicTokenVerifier, injection dans routes._token_verifier
```

**Flux de démarrage (mode HTTP) :**
1. `rgaa_mcp.py` instancie `DynamicTokenVerifier(path=TOKENS_FILE)`
2. Le passe à FastMCP comme auth
3. L'injecte dans `routes._token_verifier` (même pattern que `routes._VERSION`)
4. Monte toujours les routes admin — la vérification de `ADMIN_TOKEN` se fait à runtime (retourne `503` si non défini, plutôt qu'un `404` non informatif)

## Composant 1 — `DynamicTokenVerifier` (auth.py)

Remplace `construire_verifier()` et `StaticTokenVerifier`.

```python
class DynamicTokenVerifier:
    def __init__(self, path: Path):
        self._path = path
        self._lock = threading.Lock()
        self._tokens: dict = {}
        self.reload()

    def reload(self) -> None:
        tokens = tokens_pour_auth(self._path)  # fonction existante
        with self._lock:
            self._tokens = tokens

    async def verify_token(self, token: str) -> OAuthToken | None:
        with self._lock:
            info = self._tokens.get(token)
        if not info:
            return None
        return OAuthToken(client_id=info["client_id"], scopes=info["scopes"])
```

Réutilise `tokens_pour_auth()` (déjà existante) pour le rechargement. Thread-safe via `threading.Lock`.

## Composant 2 — Modèle de données

Ajout d'un champ `id` (8 hex chars aléatoires) à chaque token lors de la création. Sert d'identifiant stable dans les URLs admin sans exposer la valeur du token.

```json
{
  "<valeur_token_opaque>": {
    "id": "a3f8c012",
    "name": "Alice",
    "created_at": "2025-01-01T00:00:00+00:00",
    "expires_at": 1767225600,
    "updated_at": "2025-01-01T00:00:00+00:00"
  }
}
```

Les tokens existants sans champ `id` restent valides pour l'auth MCP ; ils n'apparaissent pas dans l'API admin (pas d'`id` pour les référencer).

## Composant 3 — Endpoints admin (routes.py)

**Auth :** header `Authorization: Bearer <ADMIN_TOKEN>` sur chaque requête.

| Méthode | Path | Action | Réponse |
|---------|------|--------|---------|
| `GET` | `/admin/tokens` | Liste tous les tokens | `200` + array (sans valeur du token) |
| `POST` | `/admin/tokens` | Crée un token | `201` + objet avec valeur (une seule fois) |
| `GET` | `/admin/tokens/{id}` | Détail par `id` court | `200` + objet (sans valeur) |
| `PATCH` | `/admin/tokens/{id}` | Modifie `name` et/ou `expires_days` | `200` + objet mis à jour |
| `DELETE` | `/admin/tokens/{id}` | Révoque | `204` |

**Séquence après chaque mutation (POST/PATCH/DELETE) :**
1. Écriture dans `tokens.json`
2. `_token_verifier.reload()` → effet immédiat sur l'auth MCP

**Format réponse POST :**
```json
{
  "token": "<valeur_complète>",
  "id": "a3f8c012",
  "name": "Alice",
  "expires_at": 1767225600
}
```

**Format réponse GET liste :**
```json
[
  {
    "id": "a3f8c012",
    "name": "Alice",
    "created_at": "2025-01-01T00:00:00+00:00",
    "expires_at": 1767225600,
    "status": "active"
  }
]
```

## Gestion d'erreurs

| Cas | Code |
|-----|------|
| `ADMIN_TOKEN` non défini | `503 {"error": "Admin API disabled"}` |
| Auth manquante ou invalide | `401 {"error": "Unauthorized"}` |
| Token introuvable (`{id}`) | `404 {"error": "Token not found"}` |
| Body invalide / `expires_days` ≤ 0 | `400 {"error": "<détail>"}` |
| Erreur écriture `tokens.json` | `500 {"error": "Storage error"}` |

## Tests

Nouveau fichier `tests/test_admin_api.py` :

- CRUD complet avec `ADMIN_TOKEN` valide en mode HTTP
- Token créé via POST immédiatement utilisable pour l'auth MCP (vérifie `reload()`)
- Appel sans header auth → `401`
- Appel avec mauvais `ADMIN_TOKEN` → `401`
- `DELETE` token inexistant → `404`
- `PATCH` avec `expires_days=0` → `400`
- API désactivée si `ADMIN_TOKEN` non défini → `503`

Aucun test existant modifié.

## Variables d'environnement

| Variable | Défaut | Usage |
|----------|--------|-------|
| `ADMIN_TOKEN` | — | Token admin. Si absent, API désactivée. |

## Documentation à mettre à jour

| Fichier | Ce qui change |
|---------|---------------|
| `README.md` | Nouvelle section "Gestion des tokens via API" avec exemples curl (create, list, revoke, patch) + variable `ADMIN_TOKEN` |
| `CLAUDE.md` | Ajouter `ADMIN_TOKEN` dans la table des variables d'environnement clés |
| `API.md` | Documenter les 5 endpoints admin (méthode, path, auth, body, réponses, erreurs) |
| `ARCHITECTURE.md` | Mettre à jour la section auth : `DynamicTokenVerifier` remplace `StaticTokenVerifier` |
| `CHANGELOG.md` | Entrée pour la nouvelle feature |
| `docker-compose.yml` | Ajouter `ADMIN_TOKEN: ${ADMIN_TOKEN:-}` dans la section `environment` avec commentaire explicatif (même style que les autres variables) |

## Hors périmètre

- Interface web de gestion (UI)
- Scopes/permissions par token (tous les tokens ont `["read"]`)
- Rotation automatique des tokens
- Audit log des opérations admin
