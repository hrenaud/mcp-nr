# Changelog — RGAA MCP

## [Unreleased]

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

## [2.1.1] — 2026-06-24

### Corrigé

- **Route `/guide`** : ajout section Ressources (`rgaa://version`, `rgaa://metadata`, `rgaa://index`, `rgaa://criteres/{id}`)

---

## [2.0.2] — 2026-06-24

### Modifié

- **Documentation** : mise à jour `docs/DEPLOIEMENT.md` (référence RGAA 4.2.1, 106 critères)

---

## [2.0.1] — 2026-06-24

### Modifié

- **Build** : utilisation de `docker buildx` pour supprimer l'avertissement du builder legacy

---

## [2.0.0] — 2026-06-24

_Pas de changement fonctionnel RGAA — version synchronisée avec le monorepo._

---

## [1.2.0] — 2026-06-22

### Modifié

- **Refactorisation** : utilisation de `factory.create_mcp()` et `factory.run_main()` depuis `core/mcp_ref_core/factory.py`
- **Tests** : `test_tools.py`, `test_admin_api.py` et `test_architecture_parity.py` adaptés à la nouvelle architecture factory

---

## [1.1.1] — 2026-06-22

### Ajouté

- **Prompts** (2 nouveaux) : `plan_correction`, `formuler_exigences` — passe de 9 à 11 prompts
- **`test_prompts.py`** : tests TDD pour les nouveaux prompts

### Modifié

- **Guide** : section prompts MCP ajoutée dans `docs/GUIDE_DEVELOPPEMENT.md`

---

## [1.1.0] — 2026-06-22

### Modifié

- **UI** : thème visuel bleu distinct pour les pages `/` et `/guide` — CSS custom properties, cartes avec bordure colorée, tableaux avec lignes alternées
- Logo et tagline « Accessibilité numérique »

---

## [1.0.0] — 2026-06-22

Première release dans le monorepo `mcp-nr` (migration depuis dépôt séparé).

### Ajouté

- Serveur MCP RGAA 4.2.1 — 106 critères d'accessibilité numérique
- 10 outils : `rgaa_lister_criteres`, `rgaa_obtenir_critere`, `rgaa_chercher`, `rgaa_glossaire`, `rgaa_statistiques`, `rgaa_analyser`, `rgaa_checklist`, `rgaa_taux_conformite`, `rgaa_types_audit`, `rgaa_criteres_audit`
- 9 prompts : `audit_page`, `rapport_audit`, `expliquer_critere`, `criteres_par_sujet`, `checklist_audit`, `criteres_wcag`, `audit_par_type`, `audit_rapide`, `audit_complementaire`
- Ressources MCP : `rgaa://version`, `rgaa://index`, `rgaa://critere/{id}`, `rgaa://metadata`
- Migration vers `core/mcp_ref_core` — routes HTTP partagées (homepage, guide, install.sh, API admin)
