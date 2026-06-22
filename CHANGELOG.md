# Changelog

Format : [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/), [Semantic Versioning](https://semver.org/lang/fr/)

---

## [Unreleased]

---

## [1.0.0] — 2026-06-22

Première release du monorepo `mcp-nr`, regroupant les serveurs MCP greenit et rgaa (précédemment des dépôts séparés) et le nouveau scaffold rgesn.

### Ajouté

- **Monorepo** : structure unifiée `greenit/`, `rgaa/`, `rgesn/` avec package partagé `core/`
- **`core/mcp_ref_core`** : package Python partagé extrait de greenit — `auth.py` (gestion des tokens Bearer), `routes.py` (routes HTTP communes : homepage, install.sh, guide, API admin), `_helpers.py` (validation)
- **rgesn** : scaffold complet du serveur MCP RGESN (Référentiel Général d'Écoconception de Services Numériques) prêt à recevoir les outils
- **CI matricielle** (`.github/workflows/ci.yml`) : tests et build Docker pour les 3 MCPs en parallèle
- **`release.sh`** : script de release synchronisée — bumpe la version des 3 MCPs simultanément, crée un tag unifié `v<version>`
- **`docs/DEPLOIEMENT.md`** : guide DevOps — Docker, gestion des tokens, API admin, reverse proxy, health checks
- **`.mcp.json.example`** : template de configuration Claude pour les 3 MCPs en mode HTTP

### Modifié

- `README.md` réorienté vers les utilisateurs finaux : connexion aux MCPs via token, snippet Claude Desktop et Claude Code
- `greenit` et `rgaa` migrés pour utiliser `core/mcp_ref_core` via injection de module (pattern sans héritage)
- Dockerfiles buildés depuis la racine du monorepo : `docker build -f greenit/Dockerfile .`

### Supprimé

- Workflows CI et release individuels (`greenit/.github/`, `rgaa/.github/`) — remplacés par la matrice racine
- Scripts `release.sh` individuels — remplacés par `release.sh` racine
- `.gitignore` et `.dockerignore` individuels — remplacés par le `.gitignore` racine
- Artefacts de coverage greenit (`COVERAGE_BASELINE_TASK6.txt`, `coverage_report.txt`, `coverage.json`)
- CLAUDE.md individuels greenit et rgaa — remplacés par le CLAUDE.md racine
