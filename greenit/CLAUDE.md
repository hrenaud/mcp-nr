# Règles du projet

## Variables d'environnement clés

| Variable                | Défaut    | Usage                                                          |
| ----------------------- | --------- | -------------------------------------------------------------- |
| `MCP_TRANSPORT`         | `stdio`   | `stdio` ou `http`                                              |
| `MCP_HOST`              | `0.0.0.0` | Adresse d'écoute (mode `http`)                                 |
| `MCP_PORT`              | `8000`    | Port d'écoute (mode `http`)                                    |
| `MCP_BASE_URL`          | auto      | URL publique si derrière un reverse proxy                      |
| `MCP_TOKEN_REQUEST_URL` | vide      | URL formulaire demande de token                                |
| `ADMIN_TOKEN`           | vide      | Token admin pour l'API de gestion des tokens (HTTP uniquement) |

## Releases

Les releases se font depuis la **racine du monorepo** avec `./release.sh <version>`.
Le script bumpe les 3 MCPs simultanément et crée un tag unifié `v<version>`.

Ordre obligatoire avant toute release :

1. Mettre à jour `CHANGELOG.md` de chaque MCP concerné — déplacer `[Unreleased]` vers `[x.y.z] — YYYY-MM-DD`
2. Commiter les CHANGELOGs
3. Lancer `./release.sh x.y.z` depuis la racine
4. Pusher : `git push && git push origin vx.y.z`

Ne jamais suggérer de créer ou pousser un tag avant que les CHANGELOGs soient commités.
