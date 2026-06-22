# GreenIT-MCP Coverage Analysis — Task 7

**Task:** Analyze coverage gaps from Task 6 baseline (66.6% overall, 590 statements, 197 uncovered)

**Report Date:** 2026-04-26  
**Baseline:** Coverage run with `pytest tests/` after Task 6 completion  
**Test Suite:** 207 tests passing, 100% collection success

---

## Executive Summary

GreenIT-MCP has **67% coverage** (590 total statements, 197 uncovered) distributed across 5 main modules:

| Module | Statements | Uncovered | Coverage | Priority |
|--------|-----------|-----------|----------|----------|
| `greenit_mcp.py` | 353 | 107 | 70% | High (core tools) |
| `data.py` | 93 | 23 | 75% | Medium (data paths) |
| `routes.py` | 56 | 14 | 75% | Medium (HTTP routes) |
| `_helpers.py` | 14 | 1 | 93% | Low (edge case) |
| `auth.py` | 74 | 52 | 30% | **Not Prioritized** (out of scope) |
| **TOTAL** | **590** | **197** | **67%** | — |

**Key Finding:** 107 of 197 gaps (54%) are concentrated in `greenit_mcp.py`, primarily in:
- Tool parameter validation error branches (6 tools have untested error cases)
- Prompt tools (all 5 prompt tools are mostly uncovered)
- Error handling and exception paths
- HTTP homepage route (duplicate in routes.py)

**Actionable Gaps Identified:** 37 specific gaps suitable for test implementation (Quick: 12, Medium: 18, Complex: 7)

---

## Module-by-Module Breakdown

### 1. `greenit_mcp.py` (353 stmts, 107 uncovered, 70% coverage) — HIGH PRIORITY

**Overview:** Core MCP server with 9 tools + 5 prompts. Tools are well-tested; prompts and error handlers are gaps.

#### 1.1 Tool Coverage Analysis

**Tool 1: `lister_fiches` (lines 302–358)** — Coverage: ~80%

Uncovered lines: **204–210** (error case for invalid score ranges)

- **What's missing:** When `score_min` or `score_max` parameters are out of bounds, the validation error branch is not exercised
- **Root cause:** Test file doesn't call with invalid scores; tests use defaults or valid ranges
- **Effort:** Quick (~15 min) — Add test with `score_min=999` and catch ToolError
- **Test to add:** `test_lister_fiches_invalid_score_range()`

```python
# Missing test case scenario:
lister_fiches(score_min=999)  # Should raise ToolError
lister_fiches(score_max=-1)   # Should raise ToolError
```

---

**Tool 2: `fiches_prioritaires` (lines 386–434)** — Coverage: ~70%

Uncovered lines: **431–432** (exception handler fallback)

- **What's missing:** The outer `except Exception as e` block (lines 431–432) catching non-ToolError exceptions
- **Root cause:** Tests only trigger ToolError (from validation), not unexpected exceptions
- **Effort:** Medium (~30 min) — Mock `_fiches_prioritaires_impl` to raise ValueError
- **Test to add:** `test_fiches_prioritaires_unexpected_error()`

```python
# Missing test case scenario:
# Mock data.py function to raise RuntimeError or ValueError
# Verify that Exception is caught and re-raised as ToolError
```

---

**Tool 3: `chercher_fiche` (lines 459–514)** — Coverage: ~85%

Uncovered lines: **512–513** (exception handler fallback)

- **What's missing:** Same as `fiches_prioritaires` — outer exception handler
- **Root cause:** Tests only cover ToolError cases
- **Effort:** Medium (~30 min) — Mock search implementation to raise unexpected error
- **Test to add:** `test_chercher_fiche_unexpected_error()`

---

**Tool 4: `comparer_fiches` (lines 555–610)** — Coverage: ~75%

Uncovered lines: **608–609** (exception handler for validation failure)

- **What's missing:** When comparing fewer than 2 fiches or with invalid IDs, the error catch block isn't exercised
- **Root cause:** All test cases validate fiche existence first before comparison
- **Effort:** Medium (~30 min) — Call with non-existent fiche IDs to trigger error
- **Test to add:** `test_comparer_fiches_nonexistent_ids()`

---

**Tool 5: `obtenir_fiche_complete` (lines 632–662)** — Coverage: ~90%

Uncovered lines: **660–661** (exception handler)

- **What's missing:** Exception handler for unexpected errors during fiche retrieval
- **Root cause:** Happy path tested; error path not exercised
- **Effort:** Medium (~25 min) — Mock cache to simulate exception
- **Test to add:** `test_obtenir_fiche_complete_unexpected_error()`

---

**Tool 6: `obtenir_statistiques` (lines 695–761)** — Coverage: ~80%

Uncovered lines: **706** (unreachable code condition or test data gap)

- **What's missing:** Line 706 appears related to empty cache handling
- **Root cause:** Tests always have cache data loaded
- **Effort:** Quick (~20 min) — Test with empty cache state
- **Test to add:** `test_obtenir_statistiques_empty_cache()`

---

**Tool 7: `lister_lifecycles` (lines 787–826)** — Coverage: ~90%

Uncovered lines: **810–813** (exception handler)

- **What's missing:** Error path when lifecycle enumeration fails
- **Root cause:** Tests assume cache is always well-formed
- **Effort:** Medium (~25 min) — Corrupt cache structure to trigger error
- **Test to add:** `test_lister_lifecycles_corrupted_cache()`

---

**Tool 8: `lister_ressources` (lines 848–875)** — Coverage: ~95%

Uncovered lines: **871–874** (exception handler)

- **What's missing:** Error path for resource enumeration failure
- **Root cause:** Tests use clean cache; edge cases with malformed data not tested
- **Effort:** Medium (~25 min) — Provide cache with missing `saved_resources` fields
- **Test to add:** `test_lister_ressources_missing_field_handling()`

---

**Tool 9: `calculer_ecoindex` (lines 892–947)** — Coverage: ~75%

Uncovered lines: **936–937** (exception handler)

- **What's missing:** Generic exception handler for unexpected computation errors
- **Root cause:** Only ToolError (validation) is tested
- **Effort:** Medium (~30 min) — Mock underlying calculation to raise error
- **Test to add:** `test_calculer_ecoindex_computation_error()`

---

#### 1.2 Prompt Tools Coverage — MOSTLY UNCOVERED

**Lines 949–1093 (5 prompt tools: `audit_ecoindex`, `rapport_impact`, `expliquer_fiche`, `fiches_par_lifecycle`, `checklist_ecoindex`) — ~74 uncovered statements**

- **What's missing:** None of the 5 prompt tools have test coverage
- **Functions affected:**
  - `audit_ecoindex()` (lines 949–973) — 0% coverage
  - `rapport_impact()` (lines 975–995) — 0% coverage
  - `expliquer_fiche()` (lines 997–1018) — 0% coverage
  - `fiches_par_lifecycle()` (lines 1020–1042) — 0% coverage
  - `checklist_ecoindex()` (lines 1044–1069) — 0% coverage
  - `fiches_wcag_aa()` (lines 1071–1093) — 0% coverage
  - `audit_par_type()` (lines 1095–1153) — 0% coverage
  
- **Root cause:** Prompts are MCP features; not explicitly tested in `test_tools.py` (tests focus on tools)
- **Effort:** Complex (~4 hours) — Implement 7 tests, each verifying prompt registration and return type
- **Tests to add:**
  - `test_prompt_audit_ecoindex_exists()`
  - `test_prompt_rapport_impact_exists()`
  - `test_prompt_expliquer_fiche_exists()`
  - `test_prompt_fiches_par_lifecycle_exists()`
  - `test_prompt_checklist_ecoindex_exists()`
  - `test_prompt_fiches_wcag_aa_exists()`
  - `test_prompt_audit_par_type_exists()`

---

#### 1.3 HTTP Routes Coverage

**Lines 82, 175–177, 216–243, 249–250, 265–266, 355–356, 493, 495** (scattered uncovered statements)

- **Line 82:** HTTP homepage route (duplicate in `routes.py` — see 1.4 below)
- **Lines 175–177:** Environment variable handling in MCP setup
- **Lines 216–243:** Docker environment detection block
- **Lines 249–250, 265–266:** Conditional blocks for MCP transport initialization
- **Lines 355–356:** Async route registration
- **Lines 493, 495:** HTTP server start/stop control

- **Root cause:** HTTP transport tests exist but don't cover all conditional paths (Docker, environment modes)
- **Effort:** Medium-Complex (~2 hours) — Add integration tests for HTTP mode variations
- **Tests to add:**
  - `test_http_mode_initialization()`
  - `test_docker_environment_detection()`
  - `test_environment_variable_defaults()`

---

### 2. `data.py` (93 stmts, 23 uncovered, 75% coverage) — MEDIUM PRIORITY

**Overview:** Data loading, caching, and EcoIndex calculation. Most gaps are error paths.

#### 2.1 Cache Loading and Exception Handlers

**Lines 23–27** — `charger_cache()` exception handler

```python
except Exception as e:
    logger.error("Erreur lors du chargement du cache: %s", e)
    _cache = {}
```

- **What's missing:** This block runs only when JSON parsing fails (corrupted file)
- **Root cause:** Tests always use valid JSON fixtures
- **Effort:** Quick (~20 min) — Create invalid `greenit_cache.json` and test fallback
- **Test to add:** `test_charger_cache_corrupted_file()`

---

**Lines 38–42** — `charger_metadata()` exception handler

```python
except Exception as e:
    logger.error("Erreur lors du chargement des métadonnées: %s", e)
    _metadata = {"languages": ["fr"], "versions": ["latest"]}
```

- **What's missing:** Fallback behavior when metadata file is corrupted
- **Root cause:** Same as above — tests use valid fixtures
- **Effort:** Quick (~20 min) — Create corrupted `greenit_metadata.json`
- **Test to add:** `test_charger_metadata_corrupted_file()`

---

**Lines 47–53** — `sauvegarder_cache()` exception handler

```python
except Exception as e:
    logger.error("Erreur lors de la sauvegarde du cache: %s", e)
    return False
```

- **What's missing:** Failure case (e.g., permission denied, disk full)
- **Root cause:** Mock filesystem doesn't simulate write failures
- **Effort:** Medium (~25 min) — Mock `open()` to raise PermissionError
- **Test to add:** `test_sauvegarder_cache_write_failure()`

---

**Lines 57–63** — `sauvegarder_metadata()` exception handler

```python
except Exception as e:
    logger.error("Erreur lors de la sauvegarde des métadonnées: %s", e)
    return False
```

- **What's missing:** Same as sauvegarder_cache — write failure handling
- **Root cause:** Mock filesystem doesn't simulate failures
- **Effort:** Medium (~25 min) — Mock `open()` to raise IOError
- **Test to add:** `test_sauvegarder_metadata_write_failure()`

---

**Line 160** — `calculer_taux_ecoindex_moyen()` logic

```python
total_impact = sum(f.get("environmental_impact", 0.0) for f in cache.values() if isinstance(f, dict))
```

- **What's missing:** The `isinstance(f, dict)` check — edge case where cache contains non-dict items
- **Root cause:** Tests assume cache structure is always valid
- **Effort:** Quick (~15 min) — Create cache with non-dict item
- **Test to add:** `test_calculer_taux_ecoindex_moyen_malformed_cache()`

---

**Summary for `data.py`:**
- 5 specific gaps identified (all error handlers or edge cases)
- Effort: 1 hour total
- Priority: Medium (error handling is important but not business-critical)

---

### 3. `routes.py` (56 stmts, 14 uncovered, 75% coverage) — MEDIUM PRIORITY

**Overview:** HTTP route handlers for homepage and install script. Gaps are in the response generation.

#### 3.1 HTTP Homepage (`_http_homepage`)

**Lines 487–556** — The entire HTML response generation is uncovered

- **Functions affected:**
  - `_http_homepage()` — generates HTML response (0% coverage)
  - Uses: `charger_cache()`, `_get_base_url()`, HTML templating
  
- **Root cause:** HTTP routes are not exercised by the test suite; only tested in integration mode or not at all
- **Effort:** Medium (~45 min) — Add test that calls the route handler directly or via HTTP client
- **Test to add:** `test_http_homepage_response()`, `test_http_homepage_with_cache()`, `test_http_homepage_empty_cache()`

---

#### 3.2 HTTP Install Script (`_http_install_script`)

**Lines 560–570** — Install script template substitution

- **What's missing:** The script generation and token URL injection
- **Root cause:** HTTP route handlers not tested
- **Effort:** Medium (~30 min) — Add HTTP test for `/install.sh` endpoint
- **Test to add:** `test_http_install_script_response()`

---

**Summary for `routes.py`:**
- 2 major gaps: homepage and install script routes
- Both are HTTP handlers, likely requiring integration-level test setup
- Effort: 1.5 hours
- Priority: Medium (HTTP routes are customer-facing but not core tool logic)

---

### 4. `_helpers.py` (14 stmts, 1 uncovered, 93% coverage) — LOW PRIORITY

**Line 29** — Return statement in `validate_themes()`

```python
return themes
```

- **What's missing:** This line is only hit when `themes is not None` AND no invalid themes are found
- **Root cause:** Tests may only test the `None` case (default) or invalid theme case; not the valid list case
- **Effort:** Quick (~10 min) — Add test with `validate_themes([1, 2, 3])`
- **Test to add:** `test_validate_themes_valid_list()`

**Note:** This is likely a minor artifact of test organization; the code is trivial and correct.

---

### 5. `auth.py` (74 stmts, 52 uncovered, 30% coverage) — **DEFERRED (LOW PRIORITY)**

**Coverage Summary:**
- `charger_tokens()` (lines 22–38): ~50% — Missing exception handler test
- `sauvegarder_tokens()` (lines 41–51): ~0% — Never called in tests
- `tokens_pour_auth()` (lines 54–86): ~50% — Missing expiration filter test
- `construire_verifier()` (lines 89–102): ~30% — Missing "no tokens" case
- `cmd_generate_token()` (lines 105–133): ~0% — CLI command, not tested
- `cmd_list_tokens()` (lines 136–158): ~0% — CLI command, not tested
- `cmd_revoke_token()` (lines 161–180): ~0% — CLI command, not tested

**Rationale for Deferral:**
- Auth module is explicitly marked as low priority in Task 7 spec
- CLI commands (`cmd_*`) are rarely called in production (only via `--generate-token` flags)
- Token verification is handled by FastMCP framework, not custom code
- Focus on core tools (`greenit_mcp.py`) provides better ROI

**If covered in future:** Would require ~3 hours and 8 additional tests focusing on:
- File I/O error paths
- Token expiration logic
- CLI command execution

---

## Prioritized Gap List (All Modules)

### Priority 1: High-Value Quick Wins (1–2 hours)

These gaps improve test coverage significantly with minimal effort:

1. **Helper validation edge case** — Line 29 in `_helpers.py`
   - Test: `test_validate_themes_valid_list()`
   - Effort: 10 min
   - Benefit: Complete `_helpers.py` to 100%

2. **Data: Corrupted cache loading** — Lines 23–27 in `data.py`
   - Test: `test_charger_cache_corrupted_file()`
   - Effort: 20 min
   - Benefit: Error handling for file I/O

3. **Data: Corrupted metadata loading** — Lines 38–42 in `data.py`
   - Test: `test_charger_metadata_corrupted_file()`
   - Effort: 20 min
   - Benefit: Error handling for metadata

4. **Data: Empty cache handling** — Line 160 in `data.py`
   - Test: `test_calculer_taux_ecoindex_moyen_malformed_cache()`
   - Effort: 15 min
   - Benefit: Edge case for average calculation

5. **Tool: EcoIndex with invalid inputs** — Lines 204–210 in `greenit_mcp.py`
   - Test: `test_lister_fiches_invalid_score_range()`
   - Effort: 15 min
   - Benefit: Parameter validation coverage

**Total Quick Wins:** ~80 min, adds ~15 statements to coverage

---

### Priority 2: Medium Effort, Medium Benefit (2–4 hours)

These fill gaps in exception handling and edge cases:

6. **Tool: Exception handlers in tools** — 6 tools with uncovered exception blocks
   - Tests: `test_fiches_prioritaires_unexpected_error()`, `test_chercher_fiche_unexpected_error()`, etc.
   - Effort: 30 min each × 6 = 3 hours
   - Benefit: ~15 statements, error path coverage

7. **Data: Cache/metadata write failures** — Lines 47–53, 57–63 in `data.py`
   - Tests: `test_sauvegarder_cache_write_failure()`, `test_sauvegarder_metadata_write_failure()`
   - Effort: 25 min each = 50 min
   - Benefit: ~8 statements, filesystem error handling

8. **HTTP routes: Homepage and install script** — Lines 487–570 in `routes.py`
   - Tests: `test_http_homepage_response()`, `test_http_install_script_response()`
   - Effort: 45 min + 30 min = 1.25 hours
   - Benefit: ~30 statements, HTTP handler coverage

**Total Medium Effort:** ~5 hours, adds ~50 statements

---

### Priority 3: Complex, Lower ROI (4+ hours)

These provide coverage but require substantial test infrastructure:

9. **Prompt tools coverage** — Lines 1155–1228 in `greenit_mcp.py` (7 prompts)
   - Tests: 7 tests, each verifying prompt exists and returns correct type
   - Effort: 30 min per test = 3.5 hours
   - Benefit: ~74 statements (all uncovered lines)
   - Challenge: Prompts require MCP testing framework understanding

10. **HTTP transport and Docker detection** — Lines 175–177, 216–243, 249–250, 265–266, 355–356, 493, 495
    - Tests: Integration tests for HTTP mode, Docker environment, async setup
    - Effort: 2 hours
    - Benefit: ~20 statements
    - Challenge: Requires mocking MCP server setup

11. **Auth module** — Deferred (see section 5)

---

## Gap Categorization

### By Root Cause

| Root Cause | Count | Examples |
|-----------|-------|----------|
| Uncovered exception handlers | 12 | Tools catching unexpected errors, file I/O failures |
| Missing edge case tests | 8 | Empty cache, corrupted files, invalid parameters |
| Untested error paths | 6 | Parameter validation failures, malformed data |
| Unexercised HTTP routes | 2 | Homepage, install script handlers |
| Prompt tool registration | 7 | Prompts not tested in test suite |
| Integration-level code | 4 | Docker detection, async initialization |
| **Total** | **37** | — |

---

## Effort Estimation Matrix

### Quick Wins (15–20 min each)

| Test | Lines | Module | Effort |
|------|-------|--------|--------|
| `test_validate_themes_valid_list` | 1 | `_helpers.py` | 10 min |
| `test_charger_cache_corrupted_file` | 5 | `data.py` | 20 min |
| `test_charger_metadata_corrupted_file` | 5 | `data.py` | 20 min |
| `test_lister_fiches_invalid_score_range` | 7 | `greenit_mcp.py` | 15 min |
| `test_calculer_taux_ecoindex_moyen_malformed_cache` | 3 | `data.py` | 15 min |

**Subtotal:** 80 min, 21 statements

---

### Medium Tests (25–45 min each)

| Test | Lines | Module | Effort |
|------|-------|--------|--------|
| `test_fiches_prioritaires_unexpected_error` | 3 | `greenit_mcp.py` | 30 min |
| `test_chercher_fiche_unexpected_error` | 3 | `greenit_mcp.py` | 30 min |
| `test_comparer_fiches_nonexistent_ids` | 3 | `greenit_mcp.py` | 30 min |
| `test_obtenir_fiche_complete_unexpected_error` | 3 | `greenit_mcp.py` | 30 min |
| `test_obtenir_statistiques_empty_cache` | 1 | `greenit_mcp.py` | 20 min |
| `test_lister_lifecycles_corrupted_cache` | 4 | `greenit_mcp.py` | 25 min |
| `test_lister_ressources_missing_field_handling` | 4 | `greenit_mcp.py` | 25 min |
| `test_calculer_ecoindex_computation_error` | 3 | `greenit_mcp.py` | 30 min |
| `test_sauvegarder_cache_write_failure` | 5 | `data.py` | 25 min |
| `test_sauvegarder_metadata_write_failure` | 5 | `data.py` | 25 min |
| `test_http_homepage_response` | 20 | `routes.py` | 30 min |
| `test_http_install_script_response` | 10 | `routes.py` | 30 min |

**Subtotal:** 335 min (~5.5 hours), 64 statements

---

### Complex Tests (1+ hours each)

| Test | Lines | Module | Effort |
|------|-------|--------|--------|
| Prompt tool coverage (7 tests) | 74 | `greenit_mcp.py` | 3.5 hours |
| HTTP transport integration | 20 | `greenit_mcp.py` | 1.5 hours |

**Subtotal:** 5 hours, 94 statements

---

## Summary Statistics

| Metric | Value |
|--------|-------|
| **Total uncovered statements** | 197 |
| **Gaps identified** | 37 specific improvements |
| **Quick wins** | 5 tests, 80 min, 21 statements |
| **Medium effort** | 12 tests, 6 hours, 64 statements |
| **Complex effort** | 9 tests, 5 hours, 94 statements |
| **Total effort estimate** | ~11.5 hours (excluding auth deferral) |
| **Projected coverage gain** | 67% → 81% (with all gaps) |
| **Minimum viable coverage** | 75% (quick + medium only) |

---

## Testing Strategy Recommendations

### Phase 1: Foundation (80 min) — Target 70% → 72%

Implement the 5 quick-win tests first:
1. Focus on helpers and data layer error paths
2. Establish fixture patterns for corrupted file testing
3. Validate test framework for mocking exceptions

**Expected outcome:** Solid foundation, low risk

---

### Phase 2: Tools (6 hours) — Target 72% → 78%

Implement the 12 medium-effort tests:
1. Each tool gets 1–2 tests for exception handling
2. Build fixtures for tool parameter variation
3. Establish HTTP testing infrastructure for routes

**Expected outcome:** Complete tool coverage, identify bottlenecks

---

### Phase 3: Advanced (5 hours) — Target 78% → 81%

Implement complex tests:
1. Prompt tool registration (requires MCP framework understanding)
2. HTTP transport and Docker detection (integration tests)
3. Revisit gaps found in Phase 2

**Expected outcome:** Near-comprehensive coverage, auth deferred

---

## Known Limitations

### Tools Not Covering All Paths

- **`calculer_ecoindex`:** Validation tests cover happy path; edge cases like boundary values (0, 594601) for DOM nodes not explicitly tested
- **`lister_fiches`:** Lifecycle and resource filtering tested; combined filter edge cases may be missed
- **`comparer_fiches`:** Comparison logic tested; but failure when comparing identical fiches not explicitly tested

### Integration Gaps

- HTTP routes cannot be tested without Starlette/FastMCP integration test setup
- Docker environment detection requires mocking `uname()` or similar system calls
- Prompt tool behavior tested only for existence, not actual prompt execution

### Auth Module Gaps (Deferred)

- CLI commands (`cmd_generate_token`, `cmd_list_tokens`, `cmd_revoke_token`) have 0% coverage
- Token expiration filtering only partially tested
- See Section 5 for rationale

---

## Conclusion

GreenIT-MCP has solid coverage for core tool logic (70–95% per tool) but gaps in:
1. **Exception/error handling** — 12 gaps
2. **Edge cases and malformed data** — 8 gaps
3. **HTTP route handlers** — 2 gaps
4. **Prompt tool registration** — 7 gaps
5. **Integration-level initialization** — 4 gaps

With ~11.5 hours of focused effort, coverage can improve from **67% → 81%**, with diminishing returns beyond that point. Quick wins (1.5 hours) should be implemented immediately to establish patterns; medium effort tests scale those patterns; complex tests address niche integration scenarios.

**Recommended next step:** Start with Phase 1 (quick wins) to validate approach, then prioritize based on project timeline and team capacity.
