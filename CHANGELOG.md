# Changelog

Format : [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/), [Semantic Versioning](https://semver.org/lang/fr/)

---

## [Unreleased]

### Sécurité

- **Robustesse `auth.py` (core)** : `verify_token` lève une `RuntimeError` explicite si `fastmcp.AccessToken` est indisponible au runtime (au lieu d'un `TypeError` opaque) ; `update()` valide ses entrées (`name` non vide, `expires_days > 0`). (review #2/#3)
- **Rate limiting `rgaa_analyser`** : limiteur en mémoire (fenêtre glissante, 10 req/60 s) sur l'outil qui effectue une requête HTTP vers une URL arbitraire — atténue le vecteur DoS. Timeout réseau de `fetcher_html` ramené de 30 s à 10 s (paramétrable). (review #17/#18)
- **Fail-safe auth** (`core/factory.py`, `run_main`) : en transport HTTP, le serveur refuse désormais de **servir** si aucun token valide n'est présent, au lieu de basculer silencieusement en mode sans authentification. Override explicite via `MCP_ALLOW_NO_AUTH=1` (avec WARNING). Le contrôle est au moment de servir (pas à l'import) pour ne pas casser `--health` ni les commandes CLI de gestion des tokens. Évite qu'un volume de tokens vide/mal monté n'expose un MCP sans auth (cf. incident prod rgesn).

### Refactorisé

- **Code spécifique GreenIT sorti de `core/routes.py`** : `_greenit_tool_definitions` et `_greenit_guide_extra_sections` déplacés dans `greenit/files/greenit_mcp.py` (parité avec RGAA/RGESN qui définissent leurs fonctions localement). `core/routes.py` expose désormais des défauts neutres (`_default_tool_definitions → []`, `_default_guide_extra_sections → ""`). Le guide GreenIT (section EcoIndex) est injecté explicitement via `factory.create_mcp(...)`. (review #7/#8/#13/#48, #46 partiel)

### Corrigé

- **`_helpers.validate_themes` (core)** : le message d'erreur ne cite plus `rgaa_statistiques` (nom d'outil spécifique à RGAA). `core` ne doit connaître aucun MCP — docstring du module généralisé. (review #11/#47)
- **Convergence du périmètre infra** : `Dockerfile` et `docker-compose.yml` des 3 MCP rendus identiques (modulo nom/port/deps). `greenit/Dockerfile` aligné sur la forme canonique (fichiers sous `/app/files`, `VOLUME /app/tokens`, `PYTHONPATH=/app`) ; `shm_size`/Playwright supprimés (le serveur ne lance pas de navigateur). `rgesn/docker-compose.yml` : volume nommé vide remplacé par le **bind mount** `./tokens:/app/tokens` (cause racine de l'auth désactivée en prod). `greenit_mcp.py` : `TOKENS_FILE` résolu via `_BASE_DIR.parent / "tokens"` comme rgaa/rgesn.

### Ajouté

- **`tests/test_infra_parity.py`** : verrouille la parité Dockerfile/compose/résolution des tokens entre les 3 MCP ; échoue à toute divergence non autorisée.

---

## [2.1.3] — 2026-06-27

### Ajouté

- **Reverse proxy** : labels Docker Caddy (`caddy-docker-proxy`) et Traefik ajoutés aux 3 `docker-compose.yml` pour l'auto-découverte
- **Réseau `proxy`** : réseau externe partagé déclaré dans les 3 `docker-compose.yml`
- **`docs/REVERSE_PROXY.md`** : guide de déploiement derrière Caddy ou Traefik (réseau partagé, TLS Let's Encrypt, test local)
- **Variable `DOMAIN`** : ajoutée dans les `.env` des 3 MCPs pour configurer les sous-domaines

### Modifié

- **`local-build.sh`** : séparation tests unitaires (avant build) / tests d'intégration Docker (après `docker compose up`) ; création automatique du réseau `proxy` si absent
- **`docs/DEPLOIEMENT.md`** : section reverse proxy nginx remplacée par une référence à `REVERSE_PROXY.md`

### Corrigé

- **`test_docker_integration.py`** (greenit, rgaa) : chemins absolus vers anciens dépôts remplacés par `Path(__file__).parent.parent / "files"`
- **`rgesn/tests/test_docker_integration.py`** : créé pour parité architecturale avec greenit et rgaa

---

## [2.1.2] — 2026-06-24

### Corrigé

- **Route `/guide` GreenIT** : ajout section "5. Prompts MCP" listant les 8 prompts `@mcp.prompt()` (parité avec RGAA et RGESN) ; renommage "Exemples de prompts" → "Exemples de questions" (section 7)
- **Skill `mcp-nr-release`** : vérifications de parité outils/prompts/ressources renforcées avec commandes bash concrètes

---

## [2.1.1] — 2026-06-24

### Corrigé

- **Route `/guide` RGESN** : ajout section Ressources (`rgesn://version`, `rgesn://metadata`, `rgesn://index`, `rgesn://criteres/{id}`) et prompt `criteres_prioritaires_rgesn` manquant
- **Route `/guide` RGAA** : ajout section Ressources (`rgaa://version`, `rgaa://metadata`, `rgaa://index`, `rgaa://criteres/{id}`)
- **Skill `mcp-nr-release`** : ajout vérification explicite des routes `/guide` (outils, prompts, ressources)

---

## [2.1.0] — 2026-06-24

### Ajouté

- **`rgesn://metadata`** (RGESN) : ressource MCP exposant les statistiques du référentiel et les pondérations
- **Skill `mcp-nr-add-tool`** : checklist pour ajouter un outil ou un prompt avec TDD, mise à jour docs, CHANGELOG
- **Skill `mcp-nr-release`** : checklist complète de release (docs, changelogs, tests, tag git)

### Modifié

- **`GUIDE_DEVELOPPEMENT.md`** (greenit, rgaa, rgesn) : réécriture en documentation mainteneur (architecture, tests, ajout d'outil, ressources)
- **`CLAUDE.md`** : références aux skills locaux, règles simplifiées

---

## [2.0.2] — 2026-06-24

### Modifié

- **Documentation** : mise à jour complète — RGESN décrit comme complet, préfixe `greenit_` dans tous les guides et la route `/guide`, chiffres corrects (119 fiches GreenIT, 78 critères RGESN)
- **CLAUDE.md** : règle explicite de mise à jour obligatoire de la documentation à chaque évolution

---

## [2.0.1] — 2026-06-24

### Modifié

- **Build** : utilisation de `docker buildx` pour supprimer l'avertissement du builder legacy

---

## [2.0.0] — 2026-06-24

### Ajouté

- **`greenit_criteres_prioritaires`** → **`rgesn_criteres_prioritaires`** : nouvel outil RGESN retournant les 30 critères de priorité Prioritaire (poids ×1.5), sans paramètre
- **`criteres_prioritaires_rgesn`** : nouveau prompt associé guidant l'exploration des 30 critères Prioritaire
- **`build.sh`** : script de build et lancement local des 3 MCPs

### Modifié

- **Préfixe `greenit_`** : les 9 outils GreenIT renommés (`lister_fiches` → `greenit_lister_fiches`, etc.) pour cohérence avec RGAA et RGESN

### Corrigé

- `greenit/tokens/` : correction du nom du placeholder `.gitkeep`

---

## [1.2.0] — 2026-06-22

### Ajouté

- **`core/mcp_ref_core/factory.py`** : nouvelles fonctions `create_mcp()` et `run_main()` qui centralisent l'initialisation du serveur MCP (auth, transport, routes HTTP) — élimine ~150 lignes dupliquées entre les 3 MCPs
- **`rgesn_cache.json` complet** : les 68 critères des thèmes 2 à 9 disposent maintenant de `objectif`, `mise_en_oeuvre` et `moyen_de_controle` extraits du PDF officiel RGESN 2024 (ARCEP)

### Modifié

- **Refactorisation majeure** : les 3 MCPs utilisent désormais `factory.create_mcp()` et `factory.run_main()` — suppression de `_create_mcp()` local et des fonctions de gestion de tokens locales
- **Tests mis à jour** : `test_tools.py`, `test_admin_api.py` et `test_architecture_parity.py` des 3 MCPs adaptés à la nouvelle architecture factory
- **`local-build.sh`** : exécution des tests avant le build

---

## [1.1.1] — 2026-06-22

### Ajouté

- **Prompts RGESN** (5 nouveaux) : `rapport_conformite`, `checklist_par_metier`, `audit_rapide_rgesn`, `plan_action`, `evaluer_score` — passe de 3 à 8 prompts
- **Prompts RGAA** (2 nouveaux) : `plan_correction`, `formuler_exigences` — passe de 9 à 11 prompts
- **Tests** : `test_prompts.py` pour RGESN et RGAA

### Modifié

- **Guides** : sections prompts MCP ajoutées dans les guides RGESN et RGAA

### Corrigé

- `fix(test)` : restauration de `routes._VERSION` après mutation dans les tests

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
