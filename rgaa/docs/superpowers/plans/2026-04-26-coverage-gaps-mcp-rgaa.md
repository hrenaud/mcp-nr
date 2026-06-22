# Coverage Gap Analysis: mcp-rgaa (91% baseline)

**Date**: 2026-04-26  
**Current Coverage**: 91% (1917/2114 statements covered)  
**Baseline**: 91% overall (up from 74% mentioned in Phase 5 Task 2)  
**Target**: 94% coverage (requires ~70+ more statements covered from current 197 uncovered)

---

## Executive Summary

The mcp-rgaa codebase has strong test coverage at 91%, with only **197 uncovered statements** remaining. The most critical gaps are:

1. **auth.py** — 24% coverage (48 uncovered) — **CRITICAL security-related module**
2. **rgaa_mcp.py** — 75% coverage (93 uncovered) — **Largest gap by volume**
3. **analyseur.py** — 82% coverage (23 uncovered) — HTML analysis error paths
4. **_helpers.py** — 93% coverage (1 uncovered) — Single line validation edge case

Supporting modules (**data.py, routes.py**) have 100% coverage.

---

## Module-by-Module Analysis

### 1. auth.py — 24% Coverage (CRITICAL PRIORITY)

**Status**: 48 uncovered statements across 6 functions

#### Uncovered Functions & Lines

| Function | Lines | Status | Impact |
|----------|-------|--------|--------|
| `charger_tokens()` | 13-19 | Partial | Error path when JSON parsing fails — never tested |
| `sauvegarder_tokens()` | 23-25 | Untested | File I/O path for token persistence — never tested |
| `tokens_pour_auth()` | 29-39 | Partial | Token expiration filtering — partially tested |
| `construire_verifier()` | 43-47 | Untested | StaticTokenVerifier instantiation — never tested |
| `cmd_generate_token()` | 50-61 | Untested | CLI token generation command — never tested |
| `cmd_list_tokens()` | 64-73 | Untested | CLI token listing command — never tested |
| `cmd_revoke_token()` | 76-83 | Untested | CLI token revocation command — never tested |

#### Detailed Gap Analysis

**charger_tokens() — Lines 13-19**
- Exception handling branch (lines 17-18) uncovered: What happens if JSON is corrupt?
- Return path for missing file (line 19) likely untested edge case
- **Impact**: Token loading could silently fail with bad JSON without proper error handling
- **Why Untested**: Token file typically well-formed in tests; error case not exercised

**sauvegarder_tokens() — Lines 23-25**
- Full function uncovered: JSON serialization path never tested
- Parent directory creation (line 23) untested for permission errors
- **Impact**: Token persistence could fail silently; tokens lost on restart
- **Why Untested**: Test setup likely provides pre-made token files or doesn't test actual I/O

**tokens_pour_auth() — Lines 29-39**
- Token filtering with expiration (lines 32-38) partially tested but edge cases uncovered
- Line 36-37: expires_at conversion to int when present — edge case not exercised
- **Impact**: Expired tokens could leak into auth config if filtering breaks
- **Why Untested**: Tests may not exercise expired token scenarios

**construire_verifier() — Lines 43-47**
- Full function uncovered: How FastMCP's StaticTokenVerifier is instantiated
- Import and instantiation (lines 46-47) never tested
- **Impact**: Auth configuration could fail to initialize; tokens never validated
- **Why Untested**: Likely requires mocking FastMCP's auth module; integration test complexity

**cmd_generate_token() — Lines 50-61**
- Full CLI path uncovered: token generation and user output
- Lines 50-61: Secret generation, timestamp calculation, file updates
- **Impact**: Tokens not generated via CLI; users can't create tokens
- **Why Untested**: Requires testing CLI argument parsing and file system side effects

**cmd_list_tokens() — Lines 64-73**
- Full CLI path uncovered: token listing and expiry status display
- Line 70-73: Loop through tokens and format output
- **Impact**: Token management impossible via CLI
- **Why Untested**: CLI output testing requires capturing stdout/stderr

**cmd_revoke_token() — Lines 76-83**
- Full CLI path uncovered: token deletion path
- Lines 78-81: Success path (token found and deleted)
- Lines 82-83: Error path (token not found)
- **Impact**: Tokens can't be revoked; security risk
- **Why Untested**: CLI argument parsing + file system mutation testing

#### Recommended Test Coverage (auth.py)

**Priority 1 (SECURITY-CRITICAL)** — Implement immediately:
1. **Test token file corruption recovery** — Try loading malformed JSON in tokens file
   ```python
   def test_charger_tokens_malformed_json(tmp_path):
       tokens_file = tmp_path / "tokens.json"
       tokens_file.write_text("{ invalid json }")
       result = charger_tokens(tokens_file)
       assert result == {}
   ```

2. **Test token persistence** — Verify tokens round-trip correctly
   ```python
   def test_sauvegarder_tokens_persistence(tmp_path):
       tokens = {"abc123": {"name": "test", "expires_at": 1234567890}}
       sauvegarder_tokens(tmp_path / "tokens.json", tokens)
       loaded = charger_tokens(tmp_path / "tokens.json")
       assert loaded == tokens
   ```

3. **Test token expiration filtering** — Verify expired tokens are excluded
   ```python
   def test_tokens_pour_auth_filters_expired(tmp_path):
       now = time.time()
       tokens = {
           "valid": {"name": "v", "expires_at": now + 1000},
           "expired": {"name": "e", "expires_at": now - 1000}
       }
       # Write tokens, then call tokens_pour_auth
       # Assert only valid token is returned
   ```

4. **Test CLI token generation** — Test --generate-token argument path
   ```python
   def test_cmd_generate_token_cli(tmp_path, capsys):
       cmd_generate_token(tmp_path / "tokens.json", "TestUser", expires_days=30)
       captured = capsys.readouterr()
       assert "Token généré" in captured.out
       # Verify tokens file was created with one entry
   ```

5. **Test CLI token listing** — Test --list-tokens argument path
   ```python
   def test_cmd_list_tokens_displays_all(tmp_path, capsys):
       tokens = {"abc123": {"name": "User1"}}
       sauvegarder_tokens(tmp_path / "tokens.json", tokens)
       cmd_list_tokens(tmp_path / "tokens.json")
       captured = capsys.readouterr()
       assert "User1" in captured.out
   ```

6. **Test CLI token revocation** — Test --revoke-token argument path
   ```python
   def test_cmd_revoke_token_removes_token(tmp_path, capsys):
       tokens = {"abc123": {"name": "ToDelete"}}
       sauvegarder_tokens(tmp_path / "tokens.json", tokens)
       cmd_revoke_token(tmp_path / "tokens.json", "abc123")
       loaded = charger_tokens(tmp_path / "tokens.json")
       assert "abc123" not in loaded
   ```

---

### 2. rgaa_mcp.py — 75% Coverage (93 uncovered statements)

**Status**: Largest volume of uncovered code. 93 statements uncovered across main module.

#### Uncovered Lines Summary (from coverage report)

```
Missing: 301-302, 665, 670-673, 774-776, 798, 822, 846, 866, 889, 909, 935, 961, 989-990, 995-997, 1019-1029, 1033-1041, 1045-1051, 1079-1081, 1095, 1144, 1147-1149, 1180-1228
```

#### Detailed Gap Analysis

**Lines 301-302 — Glossary fuzzy matching suggestion**
- Location: `rgaa_glossaire()` function, search result suggestion path
- Functionality: When term not found exactly but difflib finds a close match, suggest the match
- **Impact**: Glossary search returns unhelpful error when term is slightly misspelled
- **Why Untested**: Fuzzy matching tests likely don't trigger suggestion formatting (line 302)
- **Test Approach**: Add test with misspelled term (e.g., "imagee" when "image" exists), verify suggestion in output

**Line 665 — Checklist tool, continue statement in loop**
- Location: `rgaa_checklist()` tool, line 665 skips themes not in themes list
- Functionality: Filter out criteria for themes not requested
- **Impact**: Invalid themes in request might get included in checklist
- **Why Untested**: Tests may not exercise multi-theme requests with excluded themes
- **Test Approach**: Call checklist with theme=[1,2] and verify theme 3+ criteria excluded

**Lines 670-673 — Test format conversion in checklist**
- Location: `rgaa_checklist()`, convert tests_raw to tests_list
- Functionality: Parse test data (dict, list, or string) and normalize to list
- **Impact**: Checklist may display malformed test descriptions
- **Why Untested**: Test data format variation not exercised (dict, list, string cases)
- **Test Approach**: Create test criteria with each format (tests_raw={}, tests_raw=[], tests_raw="string") and verify proper conversion

**Lines 774-776 — _configure_mcp() error handler**
- Location: MCP tool/prompt registration, exception handling when tools fail to register
- **Impact**: Tool registration errors hidden from logs
- **Why Untested**: Normal operation doesn't trigger exception during registration
- **Test Approach**: Mock tool registration to raise exception, verify error handling

**Line 798 — Tool error formatting in error path**
- Location: Generic tool error response formatting
- **Impact**: Error messages may not reach user properly
- **Why Untested**: Only triggered when tool raises ToolError
- **Test Approach**: Create test tool that raises ToolError, verify error message in response

**Lines 822, 846, 866, 889, 909, 935, 961 — Resource response formatting**
- Locations: JSON response formatting in resource handlers (rgaa://*, async functions)
- **Impact**: Resource APIs may return malformed JSON
- **Why Untested**: Resources tested for existence but not response format verification
- **Test Approach**: Request each resource type and verify JSON parseable and structure correct

**Lines 989-990 — HTTP transport mode initialization**
- Location: HTTP server setup, host/port configuration
- **Impact**: Server may fail to start in HTTP mode
- **Why Untested**: Tests likely use stdio mode, not HTTP mode
- **Test Approach**: Test HTTP mode initialization with various host/port configs

**Lines 995-997 — MCP run() call for streamable-http**
- Location: HTTP transport execution
- **Impact**: HTTP server never starts
- **Why Untested**: Unit tests don't start actual HTTP server
- **Test Approach**: Integration test (docker) only; too complex for unit test

**Lines 1019-1029 — Command-line --generate-token parsing**
- Location: CLI argument handling for token generation
- **Impact**: Token generation via CLI broken
- **Why Untested**: Tests don't exercise CLI entry point
- **Test Approach**: Separate test for CLI argument parsing and cmd_generate_token call

**Lines 1033-1041 — Command-line error handling for token commands**
- Location: Exception handling for IndexError/ValueError in CLI args
- **Impact**: CLI crashes ungracefully when args malformed
- **Why Untested**: CLI path not tested
- **Test Approach**: Test with missing/invalid token arguments

**Lines 1045-1051 — Command-line --list-tokens and --revoke-token**
- Location: CLI argument parsing for token list/revoke
- **Impact**: Token management CLI broken
- **Why Untested**: CLI path not tested
- **Test Approach**: Test with correct and missing token arguments

**Lines 1079-1081 — Resource "rgaa://metadata" response**
- Location: Metadata resource handler
- **Impact**: Metadata endpoint fails
- **Why Untested**: Resource not tested for response format
- **Test Approach**: Request metadata resource, verify JSON structure

**Line 1095 — Glossary resource error path**
- Location: Return error JSON when glossaire not found
- **Impact**: 404 not properly formatted
- **Why Untested**: Resource tests may not exercise missing glossaire case
- **Test Approach**: Request with invalid glossaire ID

**Lines 1144, 1147-1149 — Health check and transport mode logic**
- Location: --health flag and transport selection
- **Impact**: Health check broken, wrong transport selected
- **Why Untested**: __main__ block not unit tested
- **Test Approach**: Subprocess tests with CLI flags

**Lines 1180-1228 — Full __main__ execution block**
- Location: Entry point execution
- **Impact**: Entire CLI interface untested
- **Why Untested**: Typically not unit tested; integration tests via Docker
- **Test Approach**: Subprocess integration tests for each CLI flag

#### Recommended Test Coverage (rgaa_mcp.py)

**Priority 1 (Core functionality)**:
1. Glossary fuzzy matching suggestion (lines 301-302)
2. Checklist theme filtering (line 665)
3. Test format conversion (lines 670-673)
4. Resource response formatting for all resource types (lines 822, 846, 866, 889, 909, 935, 961)

**Priority 2 (CLI paths)**:
1. --generate-token argument parsing and execution
2. --list-tokens argument parsing and execution
3. --revoke-token argument parsing and execution
4. --health flag handling
5. Error handling for malformed arguments

**Priority 3 (Advanced/Integration)**:
1. HTTP transport mode initialization (requires setup changes)
2. MCP module registration error handling (mock-based)

---

### 3. analyseur.py — 82% Coverage (23 uncovered statements)

**Status**: 23 uncovered statements, mostly HTML analysis edge paths.

#### Uncovered Lines Summary

```
Missing: 66, 101-113, 196-197, 215-224, 268
```

#### Detailed Gap Analysis

**Line 66 — Image with aria-hidden in theme 1**
- Location: `_theme1()`, checking if image is decorative
- Condition: `if aria_hidden == "true" or role in ("presentation", "none"): continue`
- **Impact**: Images marked as decorative may still be flagged as violations
- **Why Untested**: Test fixtures don't include decorative images with aria-hidden="true"
- **Test Approach**: Add HTML with `<img src="..." aria-hidden="true">` (no alt), verify not flagged

**Lines 101-113 — Table detection edge cases in theme 5**
- Location: `_theme5()`, checking table descriptions (caption, summary, aria-label, aria-describedby)
- **Impact**: Some table markup combinations not validated
- **Why Untested**: Test coverage gaps in table structural variants
- **Test Approach**: Test tables with:
  - Only `<caption>` (no summary/aria-label)
  - Only `summary` attribute
  - Only `aria-label` attribute
  - Only `aria-describedby` attribute
  - Multiple present (verify count correct)

**Lines 196-197 — Heading hierarchy jump detection in theme 9**
- Location: `_theme9()`, checking for valid heading level progressions (h1→h2, h2→h3, etc.)
- Specific case: `if niveaux[i] > niveaux[i-1] + 1:` (line 196) — skip more than 1 level
- **Impact**: Large heading jumps detected but only one-level jumps tested
- **Why Untested**: Test fixtures may not include large jumps (e.g., h1→h4)
- **Test Approach**: Add HTML with heading jumps: h1→h3, h1→h4, h2→h5, etc., verify all detected

**Lines 215-224 — Form field exclusion types in theme 11**
- Location: `_theme11()`, excluding certain input types from label requirement check
- TYPES_EXCLUS = {"hidden", "submit", "reset", "button", "image"}
- Condition: `if input_type in TYPES_EXCLUS: continue`
- **Impact**: Some input types incorrectly flagged as requiring labels
- **Why Untested**: Not all excluded types tested (likely only "hidden" or "submit")
- **Test Approach**: Add HTML with each excluded type (`<input type="hidden">`, `<input type="submit">`, etc.), verify none flagged

**Line 268 — _selecteur() CSS class limit (first 2 classes)**
- Location: `_selecteur()`, limit class selector to first 2 classes: `.".".join(tag["class"][:2])`
- **Impact**: Elements with 3+ classes have truncated selectors
- **Why Untested**: Test elements typically have 0-2 classes
- **Test Approach**: Add HTML with `<img class="a b c d">`, verify selector is `img.a.b` not full list

#### Recommended Test Coverage (analyseur.py)

**Priority 1 (Theme coverage)**:
1. Test decorative images with aria-hidden="true" — verify not flagged (line 66)
2. Test tables with single description types (caption-only, summary-only, etc.) — lines 101-113
3. Test large heading hierarchy jumps (h1→h4, h2→h5) — lines 196-197
4. Test form fields with all excluded types (hidden, submit, reset, button, image) — lines 215-224
5. Test elements with 3+ classes — verify selector limiting — line 268

---

### 4. _helpers.py — 93% Coverage (1 uncovered)

**Status**: Excellent coverage. Only 1 statement uncovered.

#### Uncovered Lines

**Line 20 — validate_themes() error message path**
- Location: `validate_themes()`, error condition for invalid theme numbers
- Condition: When theme not in 1-13 range
- **Impact**: Invalid theme requests could bypass validation silently
- **Why Untested**: Tests likely only pass valid themes
- **Test Approach**: Call validate_themes with invalid theme (0, 14, -1, 999), verify ToolError raised

---

## Coverage Summary Table

| Module | Statements | Covered | Missed | % | Priority | Gap Type |
|--------|-----------|---------|--------|---|----------|----------|
| auth.py | 63 | 15 | 48 | 24% | CRITICAL | Security: token management, CLI |
| rgaa_mcp.py | 368 | 275 | 93 | 75% | HIGH | CLI paths, resource formatting |
| analyseur.py | 127 | 104 | 23 | 82% | MEDIUM | HTML analysis edge cases |
| _helpers.py | 14 | 13 | 1 | 93% | LOW | Single validation error path |
| data.py | 17 | 17 | 0 | 100% | — | Complete |
| routes.py | 56 | 56 | 0 | 100% | — | Complete |

---

## Test Implementation Strategy

### Phase 1: Security-Critical (auth.py)
Estimated effort: 4-6 hours
- Token file corruption handling
- Token persistence round-trip
- Token expiration filtering
- All 3 CLI commands (generate, list, revoke)

### Phase 2: Core Functionality (rgaa_mcp.py priority 1)
Estimated effort: 6-8 hours
- Glossary fuzzy matching formatting
- Checklist theme filtering and test format conversion
- All resource endpoint response verification
- _helpers.py single edge case

### Phase 3: HTML Analysis Edge Cases (analyseur.py)
Estimated effort: 3-4 hours
- Decorative image handling (aria-hidden)
- Table description variants
- Heading hierarchy jumps
- Form field exclusion types
- CSS class selector limiting

### Phase 4: CLI Integration (rgaa_mcp.py priority 2)
Estimated effort: 4-5 hours
- Full CLI argument parsing for token commands
- Health check flag handling
- Error message formatting for malformed arguments
- Subprocess-based integration tests

---

## Recommendations

1. **Start with auth.py** — Security-critical gaps that could lead to token management failures
2. **Focus on rgaa_mcp.py core tools** — Largest uncovered volume affecting primary user features
3. **Use fixtures strategically** — Create reusable HTML fixtures for analyseur testing (decorative images, various table types, heading structures)
4. **CLI testing approach** — Separate CLI integration tests from unit tests; use subprocess for end-to-end coverage
5. **Target 94%** — Implementing all Priority 1+2 items (~60 statements) will achieve target coverage

---

## Test File Organization

Suggested additions to test suite:

- `tests/test_auth.py` — Token file I/O, expiration filtering, CLI commands (NEW)
- `tests/test_tools.py` — Add glossary, checklist, resource formatting tests (EXTEND)
- `tests/test_analyseur.py` — Add edge case HTML fixtures (EXTEND)
- `tests/test_cli_integration.py` — Subprocess-based CLI tests (NEW)

---

**Next Steps**: Implement Priority 1 tests in auth.py and rgaa_mcp.py core functionality to move from 91% → 94% coverage.
