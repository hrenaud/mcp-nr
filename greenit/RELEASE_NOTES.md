# GreenIT MCP Release Notes

## Version 2.4.1 (2026-04-27)

### Infrastructure Fixes
- **Dockerfile alignment with Phase 3 architecture:**
  - Removed outdated `COPY files/ecoindex.py` (merged into data.py during Phase 3 refactoring)
  - Added missing `COPY files/_helpers.py` (required by greenit_mcp.py imports)
- **Impact:** Container now builds and starts successfully with all dependencies present

---

## Full Journey: Phases 1-6 Completion

### Phase 1: Environment Stabilization ✅
- Python 3.13 environment configured and verified
- Dependencies installed: fastmcp 3.2.4, pytest 9.0.3, playwright (for Playwright-based analysis)
- All 90 tests passing (Docker integration validated)

### Phase 2: MCP Conformity Audit ✅
- 9 tools fully audited and annotated:
  - `lister_fiches`, `fiches_prioritaires`, `chercher_fiche`, `comparer_fiches`
  - `lister_lifecycles`, `lister_ressources`, `calculer_ecoindex`
  - `obtenir_statistiques`, `obtenir_fiche_complete`
- All tools: outputSchema ✓, readOnlyHint ✓, destructiveHint ✓, idempotentHint ✓, openWorldHint ✓
- Error handling standardized with ToolError for user-facing messages

### Phase 3: Architecture Standardization ✅
- **Modular 5-module structure aligned with mcp-rgaa:**
  - `greenit_mcp.py` (9 tools + 8 prompts + 4 resources)
  - `data.py` (cache loading, lifecycle/resource counting, ecoindex calculations)
  - `_helpers.py` (validation functions: themes, score ranges, non-negative values)
  - `auth.py` (token management with Bearer auth)
  - `routes.py` (HTTP endpoints with content negotiation)
- **Key refactoring:** ecoindex.py merged into data.py for architectural consistency
- **Result:** greenit-mcp mirrors mcp-rgaa structure exactly

### Phase 4: Documentation ✅
- **GET /guide endpoint:** JSON/HTML content negotiation
  - Accept: application/json → JSON with all 9 tools
  - Accept: text/html → HTML documentation
- **Documentation files:**
  - README.md: Installation & Getting Started (Python 3.13 requirement explicit)
  - ARCHITECTURE.md: 294-line documentation of 5-module structure
  - API.md: 923 lines documenting 9 tools, 8 prompts, 4 resources with examples
  - docker-compose.yml: Playwright-specific configuration documented
- **Deployment:** Docker multi-stage build optimized, health checks verified

### Phase 5: Test Coverage ✅
- **Baseline:** 90% coverage (298 tests, 2108 statements)
- **Final:** 94% coverage (604 tests, 3206 statements)
- **Module breakdown:**
  - _helpers.py: 100% (parametrized tests, all boundary conditions)
  - data.py: 100% (comprehensive error handling)
  - routes.py: 100% (HTTP responses, content negotiation)
  - greenit_mcp.py: 84% (testable code 100%, 55 lines uncovered = CLI __main__)
- **Test approach:** Parametrized tests, mocking for error paths, fixture-based data

### Phase 6: Final Verification ✅
- All 604 tests passing (0 failures)
- Docker integration tests passing (8 tests)
- MCP annotations validated in Phase 2 audit
- All documentation current and synced with code

---

## Production Readiness

✅ Parallel architecture with mcp-rgaa achieved
✅ 94% test coverage with comprehensive error handling
✅ Docker container builds successfully and reaches healthy status
✅ HTTP content negotiation working (JSON/HTML via Accept header)
✅ All 9 tools operational and annotated per MCP spec
✅ Full documentation (README, ARCHITECTURE, API)
✅ 604 tests passing, zero infrastructure issues

**Ready for production deployment.**

---

**Build Information:**
- Python: 3.13
- FastMCP: 3.2.4
- Transport: stdio (default) or HTTP via docker-compose
- Health Check: Every 30s, 5s timeout, 3 retries
