# Changelog

Format : [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/), [Semantic Versioning](https://semver.org/lang/fr/)

---

## [Unreleased]

### Ajouté

- **Version du référentiel** : chaque MCP expose désormais la version du référentiel qu'il contient (RGAA 4.2.1, RGESN 2024, GreenIT 5.0.0) via l'outil `*_statistiques` et la page d'accueil `/`
- **Homepage** : affichage de la version du référentiel sous la version MCP sur la page `/` des 3 serveurs
- **`core/mcp_ref_core/factory.py`** : nouvelles fonctions `create_mcp()` et `run_main()` qui centralisent l'initialisation du serveur MCP (auth, transport, routes HTTP) — élimine ~150 lignes dupliquées entre les 3 MCPs

### Modifié

- **Refactorisation majeure** : les 3 MCPs utilisent désormais `factory.create_mcp()` et `factory.run_main()` — suppression de `_create_mcp()` local, des fonctions de gestion de tokens locales (`_load_tokens`, `_save_tokens`, `_tokens_for_auth`, `_cmd_*`)
- **Tests mis à jour** : `test_tools.py`, `test_admin_api.py` et `test_architecture_parity.py` des 3 MCPs adaptés à la nouvelle architecture factory

---

## [1.1.0] — 2026-06-22

### Modifié

- **UI** : refonte du design des pages `/` et `/guide` pour les 3 MCPs — CSS custom properties, meilleure lisibilité, cartes avec bordure colorée, tableaux avec lignes alternées, largeur de colonne agrandie
- **Thèmes visuels distincts** : chaque MCP a désormais sa propre identité colorée (greenit : vert, rgesn : ambre, rgaa : bleu) via variables injectables `_LOGO`, `_ACCENT`, `_TAGLINE`
- **greenit** : suppression de 73 lignes dupliquées (`_http_homepage`, `_http_guide`) — routes désormais partagées via `core/mcp_ref_core`

### Corrigé

- `greenit/tests/test_tools.py` : correction du target de monkeypatching (`data.charger_cache` au lieu de `mcp_module.charger_cache`)
- `rgesn/tests` : assertions VERSION non liées à une valeur fixe

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
