# Règles du projet mcp-nr

## Contexte

Monorepo regroupant les serveurs MCP du numérique responsable.

## Repos sources (à lire pendant la migration)

| MCP     | Chemin local                                               | Version |
| ------- | ---------------------------------------------------------- | ------- |
| greenit | `/Users/renaudheluin/DEV/DEV_GREENIT/refs/mcp-115-greenit` | 2.5.1   |
| rgaa    | `/Users/renaudheluin/DEV/mcp-rgaa`                         | 1.2.2   |

## Plan de migration

`docs/superpowers/plans/2026-06-22-monorepo-migration.md`

5 tâches : `core/` → greenit → rgaa → rgesn scaffold → CI matrix.

## Structure cible

```
mcp-nr/
  core/mcp_ref_core/   ← auth.py, routes.py, _helpers.py (partagés)
  greenit/             ← migration de mcp-115-greenit
  rgaa/                ← migration de mcp-rgaa
  rgesn/               ← scaffold vide
```

## Règles

- Utiliser `trash` pour supprimer des fichiers, jamais `rm`
- Les Dockerfiles se buildent depuis la racine : `docker build -f greenit/Dockerfile .`
- Mettre à jour CHANGELOG.md avant tout commit de release
- `auth.py` de greenit est la version canonique (plus complète que rgaa)
