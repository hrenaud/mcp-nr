# mcp-nr

Monorepo de serveurs MCP pour les référentiels du numérique responsable (greenit, rgaa, rgesn).

## Règles non-évidentes

- Supprimer des fichiers avec `trash`, jamais `rm`
- Docker build depuis la racine : `docker build -f greenit/Dockerfile .`
- Tests depuis `<mcp>/files/` : `cd greenit/files && pytest ../tests/ -v`
- Release : mettre à jour CHANGELOG.md de chaque MCP concerné, puis `./release.sh <version>` depuis la racine
- Toute modification ou évolution (renommage d'outil, ajout de fonctionnalité, changement de comportement) doit être répercutée dans : `README.md` racine, `<mcp>/README.md`, `OUTILS.md`, `<mcp>/docs/GUIDE_DEVELOPPEMENT.md`, la route `/guide` (`core/mcp_ref_core/routes.py`), et `docs/DEPLOIEMENT.md` si pertinent

## Architecture

**Principe fondamental : tous les MCPs fonctionnent de manière identique. Le code partagé va dans `core`, pas dans chaque MCP.**

### `core/mcp_ref_core/` — logique commune à tous les MCPs

- `auth.py` : vérification des tokens (DynamicTokenVerifier)
- `routes.py` : routes HTTP (`/`, `/guide`, `/install.sh`, `/admin/*`), ressource MCP `{mcp_id}://version` via `register_version_resource()`
- `_helpers.py` : validation des paramètres (validate_themes, validate_score_range, validate_nonnegative)
- `core/tests/` : tests de la logique partagée

Variables injectables dans `routes.py` (chaque MCP les définit) :

- `_VERSION`, `_REFERENTIEL_VERSION`, `_MCP_NAME`, `_MCP_ID`
- `_ITEMS_KEY` : clé du dict cache qui contient les éléments (`"fiches"` pour GreenIT, `"criteres"` pour RGAA/RGESN)
- `_LOGO`, `_ACCENT`, `_ACCENT_DARK`, `_ACCENT_LIGHT`, `_ACCENT_BTN_TEXT`, `_TAGLINE`
- `_token_verifier`, `_get_tool_definitions`, `_guide_extra_sections`

### Ce qui reste dans chaque MCP (le spécifique)

- `data.py` : chargement du cache propre au référentiel, structure `{"meta": {...}, "fiches"|"criteres": {...}}`
- `*_mcp.py` : outils MCP spécifiques, ressources spécifiques (index, item par ID, metadata), `_create_mcp()`, injections routes
- `preparer_donnees.py` : téléchargement et préparation des données du référentiel

### Règle d'or

Si deux MCPs ont du code quasi-identique → il doit aller dans `core`. Toute divergence entre MCPs est un bug architectural.

### Structure du cache (uniforme)

```json
{"meta": {"version": "...", "updated_at": "...", ...}, "fiches|criteres": {...}}
```

Lecture version : `cache.get("meta", {}).get("version", "")`
