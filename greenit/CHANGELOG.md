# Changelog

Toutes les modifications notables sont documentées ici.
Format : [Semantic Versioning](https://semver.org/lang/fr/)

---

## [Unreleased]

---

## [2.5.0] — 2026-05-01

### Ajouté
- API d'administration des tokens HTTP (GET/POST/PATCH/DELETE `/admin/tokens`) protégée par `ADMIN_TOKEN`
- `DynamicTokenVerifier` : vérificateur de tokens avec rechargement en mémoire à chaud

### Modifié (Phase 5: Test Coverage)
- **Test coverage baseline:** Measured 90% baseline (298 tests, 2108 statements)
- **_helpers.py:** 93% → 100% coverage — added 62 parametrized tests for `validate_themes()`, `validate_score_range()`, `validate_nonnegative()` covering all boundary conditions
- **greenit_mcp.py:** 70% → 84% coverage — added 11 focused tests for error handling and tool execution paths (55 uncovered lines = CLI __main__ out of scope)
- **data.py:** 75% → 100% coverage — added 50+ tests for cache loading, metadata, EcoIndex calculation, and edge case handling
- **routes.py:** 75% → 100% coverage — added 50+ tests for HTTP endpoints, content negotiation, and error responses
- **Overall coverage:** Improved to 94% (3206 statements, 180 missed) — exceeds 93% target
- **Test suite:** 604 total tests passing with comprehensive coverage of production code paths

---

## [2.3.0] — 2026-04-19

### Ajouté
- 5 prompts MCP paramétrés (`@mcp.prompt`) : `auditer_site`, `mesurer_ecoindex`, `fiches_par_contexte`, `fiches_par_sujet`, `rapport_ecoconception` — remplacent les 3 prompts génériques sans paramètres

---

## [2.2.0] — 2026-04-19

### Ajouté
- Script `install.sh` : support multi-clients (Cursor, VS Code) avec sélection interactive, JSON helpers `write_json_mcp`/`remove_json_mcp`, désinstallation tous scopes

### Modifié
- Page `/guide` : restructurée en 6 sections numérotées (suppression de la section "Prérequis", ajout sous-section "Commande directe" avec `claude mcp add`, `.note` en vert `#22c55e`)
- `docs/GUIDE_UTILISATEUR.md` renommé en `docs/GUIDE_DEVELOPPEMENT.md`, titre mis à jour en "Guide développeur"

---

## [2.1.0] — 2026-04-11

### Ajouté
- `obtenir_fiche_complete` : nouveau champ `principes_de_validation` — liste les règles de validation formatées en phrases lisibles ("Le nombre … est inférieur à …")

### Corrigé
- `lister_fiches` : suppression du champ `description` du listing pour alléger les réponses
- Données (`greenit_cache.json`) : 29 règles de validation tronquées corrigées (blocs scalaires YAML `>-` mal parsés)
- `calculer_ecoindex` : viewport 1920×1080 documenté dans la docstring du protocole de mesure

### Modifié
- `README.md` : mis à jour pour v2.0.0 — 9 outils (ajout `calculer_ecoindex`, `lister_lifecycles`, `lister_ressources` ; suppression `audit_rapide`, `auditer_url`), 119 fiches, structure `files/` sans `audit_url.py`, exemples de prompts actualisés
- `docs/GUIDE_UTILISATEUR.md` : réécrit pour v2.0.0 — suppression du workflow `auditer_url`/`planifier_remediations`, documentation des 9 outils actuels, protocole de mesure EcoIndex avec Playwright, tableau des grades avec code couleur officiel (A>80, B>70, C>55, D>40, E>25, F>10, G≤10)

---

## [2.0.0] — 2026-04-10

### Supprimé
- Outils `audit_rapide`, `auditer_url`, `planifier_remediations` — retirés du serveur MCP
- Modules locaux `audit_url.py`, `checklist.py`, `report.py`, `remediation.py` — supprimés
- Dépendances Playwright et pytest dans le Dockerfile — image allégée

### Ajouté
- Outil `calculer_ecoindex(dom_nodes, requests, size_kb, url="")` — calcule l'EcoIndex brut (score + grade) à partir des 3 métriques mesurées par Playwright
- Math EcoIndex inlinée dans `greenit_mcp_final.py` (quantiles, formule, grades)

### Modifié
- Dockerfile simplifié : `pip install fastmcp httpx` uniquement, plus de Playwright ni de modules supplémentaires
- Guide `/guide` mis à jour avec le protocole de mesure EcoIndex (load → 3s → scroll → 3s → mesurer)
- VERSION passée à `2.0.0`

---

## [1.4.1] — 2026-04-10

### Corrigé
- `TestCrawlViewport` : patch via `sys.modules` au lieu de `patch("playwright.async_api.async_playwright")` pour que le test fonctionne en CI sans que `playwright` soit installé

---

## [1.4.0] — 2026-04-10

### Ajouté
- Helper `_scroll_to_bottom_progressive()` dans `audit_url.py` — scroll progressif (4 étapes 25/50/75/100%) pour déclencher les IntersectionObserver sur les éléments lazy-loadés
- Tests pour `_scroll_to_bottom_progressive()` dans `test_tools.py` — 3 tests de validation du comportement du scroll
- Viewport 1920×1080 dans `crawl()` — conforme à la spec EcoIndex officielle
- Test `TestCrawlViewport` dans `test_tools.py` — valide que `new_context()` reçoit le bon viewport
- `TestExtractPageMetrics` dans `test_tools.py` — 5 tests directs vérifiant le séquençage deux phases (Phase 1 avant scroll, dom_nodes après scroll, complétude des clés)

### Modifié
- `extract_page_metrics()` : protocole EcoIndex officiel implémenté (wait 3s → scroll progressif → wait 3s → mesure) avec mesure en deux phases — Phase 1 (DOM initial) pour `images_sans_lazy`, `fonts`, `iframes`, `links` ; Phase 2 (post-scroll) pour `dom_nodes` final et score EcoIndex

---

## [1.3.3] — 2026-04-09

### Modifié
- Fiches mises à jour depuis GitHub (`cnumr/best-practices`) : 119 fiches chargées, fiche anciennement dupliquée en 69 renommée en 68 (`RWEB_0068`)

---

## [1.3.2] — 2026-04-09

### Corrigé
- Docker : ajout de `DEBIAN_FRONTEND=noninteractive` dans le Dockerfile — évite le blocage du build lors de l'installation des dépendances Playwright/Chromium (notamment sur Synology)
- Docker : ajout de `shm_size: 256mb` dans `docker-compose.yml` — évite les crashes de Chromium liés à un `/dev/shm` trop petit

---

## [1.3.1] — 2026-04-09

### Ajouté
- Option `--project` dans le script d'installation — installe le MCP en scope `project` (crée `.mcp.json` dans le répertoire courant, partageable via git)
- Commande de rebuild Docker (`docker compose down && docker compose build --no-cache && docker compose up -d`) documentée dans le README

### Modifié
- Homepage (`/`) : bouton `install.sh` supprimé — redondant avec la commande `curl` déjà affichée
- Guide (`/guide`) et README : `--project` documenté avec explication des trois scopes (user / local / project)

---

## [1.3.0] — 2026-04-09

### Ajouté
- Variables d'environnement `MCP_BASE_URL` et `MCP_TOKEN_REQUEST_URL` — configurent l'URL publique du serveur et le lien du formulaire de demande de token
- Routes HTTP publiques `GET /`, `GET /install.sh`, `GET /guide` — actives uniquement en mode `MCP_TRANSPORT=http`
- Page d'accueil (`/`) : nom, version, statut du cache, commande `curl` d'installation, liens vers `/guide` et `/install.sh`
- Script d'installation bash (`/install.sh`) : installe le serveur MCP dans Claude Code via `claude mcp add`, gère les scopes user/local, la pré-autorisation des outils et la désinstallation
- Page de documentation (`/guide`) : prérequis, obtention d'un token, installation, installation manuelle, outils disponibles, exemples de prompts

### Modifié
- `synchroniser_cache` : retiré du registre MCP — opération réservée à l'administrateur du serveur

### Corrigé
- `expires_at` / `created_at` des tokens casté en `int` — FastMCP rejetait les timestamps float avec une `ValidationError` pydantic

---

## [1.2.0] — 2026-04-09

### Ajouté
- `auditer_url` : nouvel outil MCP — crawl Playwright d'un site, calcul EcoIndex par page, mapping vers fiches GreenIT, rapport Markdown ou JSON
  - Paramètres : `url`, `format` (`"markdown"` | `"json"`), `max_pages` (défaut : 5)
  - EcoIndex calculé selon la formule officielle cnumr (quantiles DOM / requêtes / poids)
  - Détection automatique des scripts de tracking (Google Analytics, GTM, Facebook Pixel, Hotjar, Intercom)
  - Rapport global : EcoIndex moyen, grade moyen, recommandations classées par fréquence
- `files/audit_url.py` : module autonome contenant EcoIndex, mapper GreenIT, extracteur de métriques, crawler et générateur de rapport
- `Dockerfile` : ajout de `playwright` et `playwright install chromium --with-deps`
- 50 tests unitaires couvrant EcoIndex, mapper et report builder

---

## [1.1.0] — 2026-04-08

### Ajouté
- `lister_fiches` : filtres optionnels (lifecycle, saved_resource, impact_min, priorite_min)
- `fiches_prioritaires` : nouvel outil, tri par score ei+pi décroissant
- `chercher_fiche` : scoring pondéré (title=10, desc=5, corps=3, ressources=2, lifecycle=1)
- `comparer_fiches` : nouvel outil, matrice comparative + classement
- `audit_rapide` : nouvel outil, détection de domaine + filtrage par score
- `obtenir_statistiques` : distributions détaillées et top 5 combiné
- Logs structurés via `logging` (remplace les `print` stderr)
- Flag `--health` pour le healthcheck Docker
- `HEALTHCHECK` dans le Dockerfile
- `docker-compose.yml` pour le mode HTTP
- `release.sh` pour la gestion des releases
- `tests/test_tools.py` : tests pytest pour tous les outils
- `.github/workflows/ci.yml` : tests + docker build sur push/PR vers main
- `.github/workflows/release.yml` : build + push vers GHCR sur tag `v*.*.*`
- `docker-compose.yml` : contexte de build inclus (`build: .`) — plus besoin de `docker build` manuel

---

## [1.0.0] — 2026-04-08

### Ajouté
- Serveur MCP initial avec 5 outils, 3 ressources, 3 prompts
- 118 fiches GreenIT embarquées (RWEB_0001 → RWEB_0119)
- Mode stdio (local) et HTTP (réseau) via `MCP_TRANSPORT`
- Authentification Bearer token en mode HTTP
- Gestion des tokens : création avec `--name` et `--expires-days`, liste, révocation
- Stockage des tokens dans `tokens.json` (volume Docker) avec expiration automatique
- Ressource `greenit://version` exposant la version serveur et données
- Image Docker basée sur `python:3.12-slim`
