# MCP RGAA — Plan de qualité 2026-04-25

> **État:** Merge complété. Environnement Python cassé (FastMCP). PHASE 1 en cours.

## 🎯 Objectifs finaux

- [x] Se conformer aux bonnes pratiques MCP (skill mcp-builder)
- [x] Rendre le code modulaire
- [x] Avoir une architecture identique entre les deux services
- [ ] Que les tests passent (normal + docker) avec couverture complète
- [ ] Documentation *.md et routes `/guide` à jour

---

## PHASE 1: Stabiliser l'environnement (URGENT)

### ✅ État du merge
- [x] Retrouvé branche `claude/confident-fermi-7a558e` avec 9 commits
- [x] Résolu conflits (auth.py, routes.py, rgaa_mcp.py, test_tools.py)
- [x] Merged dans main (commit `edad66f`)
- [x] Files structure post-merge validée:
  - [x] files/data.py (charger_cache, charger_audit_types)
  - [x] files/auth.py (gestion tokens)
  - [x] files/routes.py (routes HTTP)
  - [x] files/rgaa_mcp.py (imports des modules)

### ✅ Dépendances Python — COMPLÉTÉ

- [x] Étape 1.1: Réinstaller dépendances
  - [x] Python 3.13 installé via brew (`/opt/homebrew/bin/python3.13`) → correspond à Docker
  - [x] venv créé : `.venv-py313`
  - [x] Toutes dépendances installées: fastmcp 3.2.4, pytest 9.0.3, etc.
  - [x] Vérifier: `python -c "import fastmcp; print(fastmcp.__version__)"`
    → ✅ fastmcp 3.2.4

- [x] Étape 1.2: Exécuter tests mcp-rgaa
  - [x] Tests lancés: `python -m pytest tests/ -v` (Python 3.13)
  - Status: **96 PASSED, 38 FAILED** (expected — annotations à ajouter)
  - Failures attendues:
    - 2 tests conformité (format retour à adapter)
    - 36 tests annotations (PHASE 2 work)

---

## PHASE 2: Auditer conformité MCP (Context7-verified)
**Status:** ✅ COMPLETE (2026-04-25)
**Tests:** 87/87 passing

### 10 Outils — Audit complété

| Outil | outputSchema | readOnlyHint | destructiveHint | idempotentHint | openWorldHint | Status |
|-------|---|---|---|---|---|---|
| rgaa_lister_criteres | [x] | [x] | [x] | [x] | [x] | ✅ |
| rgaa_obtenir_critere | [x] | [x] | [x] | [x] | [x] | ✅ |
| rgaa_chercher | [x] | [x] | [x] | [x] | [x] | ✅ |
| rgaa_glossaire | [x] | [x] | [x] | [x] | [x] | ✅ |
| rgaa_statistiques | [x] | [x] | [x] | [x] | [x] | ✅ |
| rgaa_types_audit | [x] | [x] | [x] | [x] | [x] | ✅ |
| rgaa_criteres_audit | [x] | [x] | [x] | [x] | [x] | ✅ |
| rgaa_analyser | [x] | [x] | [x] | [x] | [x] | ✅ |
| rgaa_checklist | [x] | [x] | [x] | [x] | [x] | ✅ |
| rgaa_taux_conformite | [x] | [x] | [x] | [x] | [x] | ✅ |

### Completed Tasks

- [x] Étape 2.1: outputSchema ajouté sur tous les 10 outils
  - Audit: `grep -r "outputSchema" files/rgaa_mcp.py | wc -l` = 10 ✓

- [x] Étape 2.2: Annotations ajoutées sur tous les 10 outils
  - [x] readOnlyHint: 8 outils (tous sauf rgaa_analyser, rgaa_checklist)
  - [x] destructiveHint: false sur tous
  - [x] idempotentHint: true sur 8 outils read-only
  - [x] openWorldHint: true sur rgaa_chercher, rgaa_analyser

- [x] Étape 2.3: Gestion erreurs vérifiée et améliorée
  - [x] ToolError utilisé pour erreurs utilisateur
  - [x] Messages d'erreur exploitables avec suggestions
  - [x] Gestion erreurs réseau (rgaa_analyser)

---

## PHASE 3: Standardiser architecture

**Tâches exécutées avec subagent-driven development:**

- [x] **Task 1: Créer _helpers.py pour mcp-rgaa** (COMPLÉTÉ 2026-04-25)
  - [x] Extrait validation helpers: `validate_themes()`, `validate_score_range()`, `validate_nonnegative()`
  - [x] Refactorisé rgaa_mcp.py imports (3 call sites mis à jour)
  - [x] Tous 134 tests passent ✅
  - [x] Commit: 30f77db "refactor: extract validation helpers to _helpers.py (rgaa)"

- [x] **Task 2: Créer _helpers.py pour greenit-mcp** (COMPLÉTÉ 2026-04-25)
  - [x] Créé files/_helpers.py (3 validation functions identiques à mcp-rgaa)
  - [x] Refactorisé greenit_mcp.py imports (7 call sites mis à jour)
  - [x] Tous 110 tests passent ✅ (spec compliant fix)
  - [x] Commits: cd74d4f + 13baabc "refactor: extract validation helpers to _helpers.py (greenit)"

- [x] **Task 3: Fusionner ecoindex.py dans data.py (greenit-mcp)** (COMPLÉTÉ 2026-04-25)
  - [x] Vérification: ecoindex.py fusionné dans data.py (lines 66-110)
  - [x] greenit_mcp.py importation mise à jour : `calculer_ecoindex` depuis data
  - [x] Tous 110 tests passent ✅
  - [x] Commit: 744d7d3 "refactor: merge ecoindex.py into data.py for architectural consistency"
  - [x] Architecture alignment: greenit-mcp now mirrors mcp-rgaa (modulaire)

- [ ] **Task 4-8: Autres standardisations** (À venir)

### Étape 3.1: Vérifier structure files/ post-merge
  - [x] files/rgaa_mcp.py ✓
  - [x] files/data.py ✓
  - [x] files/auth.py ✓
  - [x] files/routes.py ✓
  - [x] files/_helpers.py ✓ (CREATED Task 1)
  - [x] files/rgaa_cache.json ✓
  - [x] files/audit_types.json ✓

### Étape 3.2: Metadata uniformes
  - [x] Vérifier rgaa_cache.json structure
  - [x] Vérifier rgaa://metadata resource

### Étape 3.3: Routes HTTP uniformes
  - [x] Vérifier routes.py (GET /, GET /health, GET /guide)

---

## PHASE 4: Vérifier et mettre à jour documentation

**Tasks 6-7 Completed (2026-04-25):**
- [x] Implemented JSON content negotiation on GET /guide endpoints
- [x] Accept: application/json returns JSON with all tools
- [x] Accept: text/html (or no header) returns HTML documentation
- [x] Added comprehensive test coverage (15+ new tests)
- [x] Fixed 5 code quality issues (TOOLS_DEFINITIONS, type hints, schema validation, HTML rendering, routing logic)
- [x] All tests passing (253 for mcp-rgaa)
- [x] Both spec compliance and code quality reviews: ✅ APPROVED

- [x] **Étape 4.1: Vérifier docs/** (COMPLÉTÉ 2026-04-26)
  - [x] **Task 9: README.md à jour vs code** (COMPLÉTÉ 2026-04-26)
    - [x] Fixed test count references (227→253, 250→253)
    - [x] Added HTTP endpoint documentation (GET /, GET /guide, GET /install.sh, GET /health)
    - [x] All 253 tests passing ✅
    - [x] Commits: 8e6ebd3 (GET endpoint docs), cd60ea6 (test count fixes)
  - [x] **Task 10: ARCHITECTURE.md création** (COMPLÉTÉ 2026-04-26)
    - [x] Created 307-line ARCHITECTURE.md documenting 5-module structure
    - [x] Documented: rgaa_mcp.py (10 tools), data.py (cache/criteria), _helpers.py (validation), auth.py (tokens), routes.py (HTTP), analyseur.py (HTML analysis)
    - [x] Documented data flow, design decisions, testing approach
    - [x] All 253 tests passing ✅
    - [x] Commit: 4d4b35a "docs: document Phase 3 modular architecture"
  - [x] API.md complet avec tous les outils (COMPLÉTÉ 2026-04-26)

- [x] Étape 4.2: Routes `/guide` opérationnelles (COMPLÉTÉ 2026-04-25)
  - [x] GET /guide retourne HTML ou JSON valide (content negotiation)
  - [x] Affiche: liste outils, description, paramètres, exemple
  - [x] Tests: 15+ new tests covering JSON/HTML responses
  - [x] Code quality: 5 issues fixed (TOOLS_DEFINITIONS unified, type hints added, schema validation, HTML rendering optimized, routing consolidated)

- [x] **Étape 4.3: Documentation de déploiement** (COMPLÉTÉ 2026-04-26)
  - [x] docker-compose.yml env vars documentées (44 lines, all 5 env vars with examples)
  - [x] Installation: pip install -r requirements.txt explicit with Python 3.13 requirement
  - [x] Startup: docker-compose quick start + stdio mode + health check verification
  - [x] Deployment docs complete: docker-compose.yml comments, README.md Installation & Getting Started sections
  - [x] Code quality review: 4 issues identified and fixed (copy-paste errors, placeholders, defaults, duplication)
  - [x] All tests passing (253) ✅
  - [x] Commits: 1e14c3a (docs: add deployment documentation), 8109769 (fix: correct deployment documentation)

---

## PHASE 5: Mesurer couverture de tests

- [x] **Task 1-3 COMPLETED** (2026-04-26): Coverage baseline and gap analysis
  - [x] Task 1: Baseline coverage 91% (measured with coverage.py)
  - [x] Task 2: Gap analysis identifying 197 uncovered statements (420-line spec)
  - [x] Task 3: analyseur.py coverage improved 79% → 97% with 12 focused tests

- [x] **Task 4 COMPLETED** (2026-04-26): data.py and _helpers.py coverage
  - [x] data.py: 100% coverage (17 statements, all executed)
  - [x] _helpers.py: 93% coverage (14 statements, 1 uncovered edge case)

- [x] **Task 5 COMPLETED** (2026-04-26): 21 unit tests for all 10 RGAA tools
  - [x] Added tests targeting parameter validation, error handling, edge cases
  - [x] All 156 tests passing
  - [x] Fixed 3 code quality issues: class name typo, duplicate tests removed, tautological assertion fixed
  - [x] Code quality review: ✅ APPROVED

- [x] **Task 6 COMPLETED** (2026-04-26): Baseline coverage for greenit-mcp (parallel)
  - [x] Generate coverage report for greenit-mcp (measure baseline)
  - [x] **Measured baseline: 90%** (same architecture, 1% lower than mcp-rgaa)
  - [x] Results: 298 tests, 2108 statements, 212 missed
  - [x] Ready for coverage improvements in Tasks 7-10

- [x] Étape 5.2: Ajouter tests manquants
  - [x] mcp-rgaa: Tests ajoutés pour couvrir gaps (Tasks 4-6)
  - [x] Commit: "test: improve coverage to 93.5%"

---

## PHASE 6: Vérification finale

- [x] Étape 6.1: Tous les tests passent
  ```bash
  python -m pytest tests/ -v
  ```
  - [x] 0 failures (253 tests passing)

- [x] Étape 6.2: Docker tests passent
  ```bash
  docker-compose up -d
  docker-compose exec rgaa pytest tests/test_docker_integration.py
  docker-compose down
  ```
  - [x] 0 failures (Docker integration tests passing)

- [x] Étape 6.3: MCP Inspector validation (optionnel)
  ```bash
  npx @modelcontextprotocol/inspector npx python rgaa_mcp.py
  ```
  - [x] Tous les 10 outils listés
  - [x] Annotations visibles (readOnlyHint, destructiveHint, idempotentHint, openWorldHint)
  - [x] OutputSchema valide sur tous les outils

- [x] Étape 6.4: Documentation finale
  - [x] CHANGELOG.md: résumé changements (Phase 5-6 improvements documented)
  - [x] README: instructions claires (updated with endpoint documentation)
  - [x] API.md: tous 10 outils documentés avec exemples

---

## 📋 Résumé avancement

| Phase | Description | mcp-rgaa | greenit-mcp | Blockers |
|-------|-------------|----------|------------|----------|
| 1 | Stabiliser environnement | ✅ 100% | ✅ 100% | None |
| 2 | Auditer conformité MCP | ✅ 100% | ✅ 100% (9 tools) | None |
| 3 | Standardiser architecture | ✅ 100% (8/8 tasks) | ✅ 100% (aligned) | None |
| 4 | Documentation | ✅ 100% | ✅ 100% | None |
| 5 | Couverture tests | ✅ 100% (93.5% coverage, 422 tests) | ✅ 100% (94% coverage, 604 tests) | None |
| 6 | Vérification finale | ✅ 100% | ✅ 100% | None |

---

**Status:** ✅ PHASE 5-6 COMPLETE POUR TOUS SERVICES (2026-04-27)

**mcp-rgaa:**
- PR#2 merged (Phase 5 coverage improvements: 93.5% core coverage, 422 tests passing)
- Phase 6 verification complete (all tests passing, Docker validated)
- Ready for production deployment

**greenit-mcp:**
- Phase 5 complete (94% overall coverage, 604 tests passing)
- Phase 6 verification complete (clean working directory, all branches merged)
- Version: 2.4.0 — Ready for production deployment

**Alignment Achieved:**
- ✅ Identical architecture (5-module structure: {service}_mcp.py, data.py, _helpers.py, auth.py, routes.py)
- ✅ Identical test coverage approach (parametrized tests, comprehensive error handling, mocking strategies)
- ✅ Identical documentation structure (README.md, ARCHITECTURE.md, API.md, DEPLOYMENT.md)
- ✅ Both services: 100% passing tests, >93% code coverage, Docker-ready

---

## PHASE 7: Production Release

✅ **Phase 7 COMPLETE** (2026-04-27)

### Tasks Completed
- [x] **mcp-rgaa v1.0.0** — Tag created and pushed
  - Annotated tag with Phase 1-6 journey documentation
  - Release notes document: 93.5% core coverage, 422 tests, full modular architecture
  - Commits: Version bump and release documentation

- [x] **greenit-mcp v2.4.1** — Tag created and pushed
  - Includes Dockerfile infrastructure fixes for Phase 3 architectural alignment
  - Fixed: Removed obsolete ecoindex.py reference, added missing _helpers.py
  - Release notes document: 94% coverage, 604 tests, full modular architecture
  - Commits: Two Dockerfile fixes + version bump

### Both Services Now Production-Ready
- ✅ Docker containers build successfully
- ✅ HTTP endpoints functional with content negotiation
- ✅ All tests passing (93.5% mcp-rgaa, 94% greenit-mcp)
- ✅ Release notes and CHANGELOG.md updated
- ✅ Official tags v1.0.0 and v2.4.1 pushed to origin
- ✅ NO registry publishing (Docker Hub, PyPI skipped as requested)

**Future Phase Options:**
1. **Phase 8 — Monitoring & Observability:** Add structured logging, metrics collection, health dashboards
2. **Phase 8 — Cross-Service Integration:** Combine RGAA + GreenIT scoring in unified dashboard
3. **Phase 8 — Continuous Deployment:** Automate releases and Docker image builds

**Date:** 2026-04-27
**Status:** Both services aligned, tested, documented, and released
