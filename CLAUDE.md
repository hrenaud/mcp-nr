# mcp-nr

Monorepo de serveurs MCP pour les référentiels du numérique responsable (greenit, rgaa, rgesn).

## Règles non-évidentes

- Supprimer des fichiers avec `trash`, jamais `rm`
- Docker build depuis la racine : `docker build -f greenit/Dockerfile .`
- Tests depuis `<mcp>/files/` : `cd greenit/files && pytest ../tests/ -v`
- `core/mcp_ref_core/` contient auth.py, routes.py, \_helpers.py — partagés entre tous les MCPs via `pip install -e core/`
- Release : mettre à jour CHANGELOG.md de chaque MCP concerné, puis `./release.sh <version>` depuis la racine
