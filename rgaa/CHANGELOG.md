# Changelog

Toutes les modifications notables sont documentées ici.
Format : [Semantic Versioning](https://semver.org/lang/fr/)

---

## [Unreleased]

---

## [1.2.1] — 2026-05-01

### Modifié
- Refactoring : suppression de `_configure_mcp`, logique inlinée dans `_create_mcp()` appelée avant les décorateurs (aligne le pattern avec mcp-greenit)

---

## [1.2.0] — 2026-04-19

### Ajouté
- API HTTP d'administration des tokens (`/admin/tokens`) : créer, lister, détailler, modifier, révoquer
- `DynamicTokenVerifier` : rechargement des tokens sans redémarrage du serveur
- Variable d'environnement `ADMIN_TOKEN` pour sécuriser l'API admin
- Routes `/admin/tokens` montées via `custom_route` dans `_create_mcp()` (HTTP uniquement)

---

## [1.0.0] — 2026-04-26 (Production Release)

### Phase 7: Production Release ✅
- Official v1.0.0 production release after Phases 1-6 completion
- Development journey documented in RELEASE_NOTES.md
- All 253 unit tests passing, 93.5% code coverage
- 10 tools, 8 prompts, 4 resources fully operational
- Docker support with health checks
- HTTP endpoints with JSON/HTML content negotiation
- Token-based authentication for HTTP mode

### Quality Metrics
- Test coverage: 93.5% (422 tests, 100% passing)
- MCP compliance: 10/10 tools spec-compliant with annotations
- Docker: Fully tested integration with compose
- Performance: Sub-second response times

### Documentation
- RELEASE_NOTES.md: Complete Phase 1-6 development journey
- ARCHITECTURE.md: 5-module design documentation
- API.md: 907+ line comprehensive tool documentation
- README.md: Updated with all endpoints and examples

---

## [1.1.0] — 2026-04-18

### Ajouté
- Prompts MCP : `expliquer_critere`, `criteres_par_sujet`, `checklist_audit`, `criteres_wcag`
- Authentification Bearer token fonctionnelle via `StaticTokenVerifier` (bug corrigé)
- Pattern `_create_mcp()` : routes HTTP conditionnelles (stdio ne charge plus les routes web)
- Route `/install.sh` : script bash d'installation automatique pour Claude Code
- Flag `--health` pour le healthcheck Docker (remplace la sonde HTTP urllib)
- Logs de démarrage : version, nombre de critères, statut auth, port
- Helpers `_get_base_url()` et `_get_token_request_url()` (support `MCP_TOKEN_REQUEST_URL`)
- Ressources MCP : `rgaa://version`, `rgaa://criteres/{id}`, `rgaa://index`
- Transport `streamable-http` (corrige la compatibilité FastMCP 3.x)
- Suite de tests pytest complète (`tests/test_tools.py`, 66 tests)

### Modifié
- Annotations de types améliorées : `Literal["A","AA","AAA"]` pour `niveau_wcag`, `Literal["criteres","glossaire"]` pour `scope`
- README : paramètres des outils corrigés (`rgaa_chercher`, `rgaa_analyser`, `rgaa_checklist`, `rgaa_taux_conformite`)
- README : table des ressources MCP corrigée (suppression de `rgaa://criteres` et `rgaa://glossaire` inexistantes, correction `rgaa://critere/` → `rgaa://criteres/`)
- README : `MCP_PORT` défaut corrigé à `8000` (port interne conteneur)
- TODO : items V1 cochés (tout implémenté depuis v1.0.0)
- `VERSION` synchronisée avec le CHANGELOG (était restée à `1.0.0`)

---

## [1.0.0] — 2026-04-18

### Ajouté
- Serveur MCP initial avec 8 outils RGAA 4.2.1
- 106 critères RGAA embarqués avec tests, niveaux WCAG et thèmes
- Glossaire RGAA (termes et définitions)
- Mode stdio (local) et HTTP (réseau) via `MCP_TRANSPORT`
- Authentification Bearer token en mode HTTP
- Gestion des tokens : création avec `--name` et `--expires-days`, liste, révocation
- Routes HTTP publiques `GET /`, `GET /guide` avec documentation interactive
- Ressource `rgaa://version` exposant la version serveur et données
- Image Docker basée sur `python:3.11-slim`
- `docker-compose.yml` avec healthcheck HTTP
