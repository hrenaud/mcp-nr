# Règles du projet

## Variables d'environnement clés

| Variable | Défaut | Usage |
|----------|--------|-------|
| `MCP_TRANSPORT` | `stdio` | `stdio` ou `http` |
| `MCP_HOST` | `0.0.0.0` | Adresse d'écoute (mode `http`) |
| `MCP_PORT` | `8000` | Port d'écoute (mode `http`) |
| `MCP_BASE_URL` | auto | URL publique si derrière un reverse proxy |
| `MCP_TOKEN_REQUEST_URL` | vide | URL formulaire demande de token |
| `ADMIN_TOKEN` | vide | Token admin pour l'API de gestion des tokens (HTTP uniquement) |

## Releases

Ordre obligatoire avant toute release :

1. Mettre à jour `CHANGELOG.md` — déplacer `[Unreleased]` vers `[x.y.z] — YYYY-MM-DD`
2. Commiter le CHANGELOG avec le code (`chore(release): bump version to x.y.z`)
3. Créer le tag `vx.y.z`
4. Pusher le tag

Ne jamais suggérer de créer ou pousser un tag avant que le CHANGELOG soit commité.
