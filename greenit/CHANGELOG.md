# Changelog — GreenIT MCP

## [Unreleased]

---

## [2.2.0] — 2026-06-28

### Corrigé

- URL de base des pages `/`, `/guide`, `/install.sh` détectée depuis la requête (reverse proxy / en-tête `Host`) ; correction client supplémentaire des URLs affichées via `window.location.origin`. (core)

---

## [2.1.3] — 2026-06-27

### Ajouté

- Labels Caddy (`caddy-docker-proxy`) et Traefik dans `docker-compose.yml` pour l'auto-découverte reverse proxy
- Réseau externe `proxy` dans `docker-compose.yml`
- Variable `DOMAIN` dans `.env`

### Modifié

- `local-build.sh` : tests d'intégration Docker déplacés après `docker compose up`

### Corrigé

- `tests/test_docker_integration.py` : chemin absolu vers ancien dépôt remplacé par chemin relatif

---

## [2.1.2] — 2026-06-24

### Corrigé

- **Route `/guide`** : ajout section "5. Prompts MCP" listant les 8 `@mcp.prompt()` (parité avec RGAA et RGESN) ; renommage "Exemples de prompts" → "7. Exemples de questions"

---

## [2.0.2] — 2026-06-24

### Modifié

- **Documentation** : `README.md` et `docs/GUIDE_DEVELOPPEMENT.md` mis à jour avec le préfixe `greenit_` sur tous les noms d'outils

---

## [2.0.0] — 2026-06-24

### Modifié

- **Préfixe `greenit_`** : les 9 outils MCP renommés avec le préfixe `greenit_` pour cohérence avec les MCPs RGAA et RGESN (`lister_fiches` → `greenit_lister_fiches`, etc.)

---

## [1.2.0] — 2026-06-22

### Modifié

- **Refactorisation** : utilisation de `factory.create_mcp()` et `factory.run_main()` depuis `core/mcp_ref_core/factory.py`
- **Tests** : `test_tools.py` et `test_architecture_parity.py` adaptés à la nouvelle architecture factory

---

## [1.1.1] — 2026-06-22

### Corrigé

- `test_tools.py` : restauration de `routes._VERSION` après mutation dans les tests

---

## [1.1.0] — 2026-06-22

### Modifié

- **UI** : thème visuel vert distinct (`#22c55e`) pour les pages `/` et `/guide` — CSS custom properties, cartes avec bordure colorée, tableaux avec lignes alternées
- **Routes partagées** : suppression de 73 lignes dupliquées (`_http_homepage`, `_http_guide`) — délégation complète à `core/mcp_ref_core`
- Logo 🌱 et tagline « Bonnes pratiques d'écoconception web »

---

## [1.0.0] — 2026-06-22

Première release dans le monorepo `mcp-nr`.
