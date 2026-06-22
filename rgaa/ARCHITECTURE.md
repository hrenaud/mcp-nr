# RGAA MCP Server — Architecture

## Overview

RGAA MCP is a Model Context Protocol server that provides access to the complete RGAA 4.2.1 (Référentiel Général d'Amélioration de l'Accessibilité) reference framework with 106 criteria. It enables Claude and other MCP clients to analyze web accessibility, search criteria, generate checklists, and calculate compliance rates—all without external API dependencies.

**Key responsibilities:**
- Expose 10 MCP tools for referential access, HTML analysis, and compliance calculation
- Provide 4 MCP resources (version, index, criteria details, metadata)
- Support two transport modes: stdio (local) and HTTP (network, with token authentication)
- Analyze static HTML to detect accessibility violations across 8 themes
- Manage bearer token authentication for HTTP mode
- Serve HTTP endpoints (/, /guide, /install.sh) with content negotiation

---

## Module Structure

### rgaa_mcp.py — Main Server

**Responsibility:** Orchestrates the FastMCP server, defines all MCP tools and resources, handles startup logic including token verification and HTTP routing.

**Key exports:**
- **10 MCP Tools:** 
  - `rgaa_lister_criteres` — List RGAA criteria with optional theme/WCAG filters
  - `rgaa_obtenir_critere` — Fetch full criterion details (tests, conditions, WCAG mapping)
  - `rgaa_chercher` — Search criteria and glossary by keyword with fuzzy matching
  - `rgaa_glossaire` — Look up glossary term definitions
  - `rgaa_statistiques` — Return referential statistics (distribution by theme/level)
  - `rgaa_analyser` — Analyze HTML URL for RGAA violations (8 themes, static analysis)
  - `rgaa_checklist` — Generate manual test checklist with recommended tools
  - `rgaa_taux_conformite` — Calculate official RGAA compliance rate (C/(C+NC)×100)
  - `rgaa_types_audit` — List 3 audit types (complet, rapide, complémentaire) and legal status
  - `rgaa_criteres_audit` — Return criteria list for a specific audit type

- **4 MCP Resources:**
  - `rgaa://version` — Server and data version
  - `rgaa://index` — Lightweight index of all criteria (id, title, level)
  - `rgaa://criteres/{id}` — Full criterion content
  - `rgaa://metadata` — Referential metadata (languages, source, criterion count, automatable count)

**Process flow:**
1. Startup: Load cache (rgaa_cache.json), set up token verifier if HTTP mode
2. Inject version and routes into modules
3. FastMCP server runs with selected transport (stdio or HTTP)
4. On tool call: Delegate to specialized modules (data.py, analyseur.py, _helpers.py)

---

### data.py — Cache Loading & Access

**Responsibility:** Single source of truth for loading and caching RGAA referential data. Provides functions for accessing criteria, themes, glossary, and metadata.

**Key functions:**
- `charger_cache()` — Load RGAA criteria from rgaa_cache.json (lazy-load with memoization)
- `charger_audit_types()` — Load audit type definitions from audit_types.json

**Data structure:**
```json
{
  "1.1": {
    "titre": "...",
    "theme": 1,
    "niveau": "A",
    "automatisable": true,
    "tests": [...],
    "conditions": [...]
  },
  ...
}
```

---

### analyseur.py — HTML Static Analysis

**Responsibility:** Analyze HTML pages to detect accessibility violations without JavaScript execution. Covers 8 of 13 RGAA themes.

**Key functions:**
- `fetcher_html(url: str)` — Fetch HTML content from URL with timeout
- `analyser_html(html: str, themes: list[int])` — Parse HTML and detect violations per theme

**Covered themes (static analysis):**
1. Images — missing alt attributes
2. Frames — missing title attributes
3. Tables — missing headers, summary
5. Links — empty links, missing labels
6. Forms — missing labels, fieldsets
8. Navigation — missing skip links, landmark landmarks
9. Mandatory elements — missing doctype, language, title
11. Structure — heading hierarchy, semantic markup

**Uncovered themes (manual testing required):**
- 4. Multimedia (video/audio controls)
- 7. Scripts (dynamic behavior)
- 10. Presentation (CSS layout)
- 12. Consultation (page display)
- 13. Elements (interactive behavior)

---

### _helpers.py — Shared Validation

**Responsibility:** Centralized validation functions used by multiple tools to ensure consistent error handling and parameter validation.

**Key functions:**
- `validate_themes(themes: list[int] | None) -> list[int]` — Validate theme IDs (1-13), return normalized list
- `validate_score_range(value: int, min_val: int, max_val: int, param_name: str)` — Validate numeric parameter within range, raise ToolError if outside bounds
- `validate_nonnegative(value: float, param_name: str)` — Validate numeric parameter is ≥ 0

**Usage pattern:** Called by tools before processing user input to fail fast with user-friendly French error messages.

---

### auth.py — Token Management

**Responsibility:** Generate, store, list, revoke, and verify bearer tokens for HTTP mode authentication.

**Key functions:**
- `cmd_generate_token(path, name, expires_days=365)` — Create new token with expiration date
- `cmd_list_tokens(path)` — Display all tokens (active and expired)
- `cmd_revoke_token(path, token)` — Revoke specific token by marking it revoked
- `charger_tokens(path) → dict` — Load tokens from tokens.json
- `tokens_pour_auth(path) → dict` — Load and filter non-expired tokens for FastMCP auth
- `construire_verifier(path) → DynamicTokenVerifier` — Build token verifier for FastMCP

**`DynamicTokenVerifier`:** Holds the valid token set in-memory protected by a `threading.Lock`. Supports `reload()` to refresh the token list from disk without restarting the server — called automatically after admin API mutations.

**Token storage:** `tokens/tokens.json` (volume-mounted, persists across restarts)

```json
{
  "<token_string>": {
    "name": "Alice",
    "created_at": 1713398400.0,
    "expires_at": 1744934400.0
  }
}
```

---

### routes.py — HTTP Endpoints

**Responsibility:** Handle HTTP routes (/, /guide, /install.sh) with content negotiation and markdown rendering.

**Key endpoints:**
- **GET /** — Homepage with server status, cache summary, quick install command
- **GET /guide** — Documentation with content negotiation:
  - `Accept: text/html` → Interactive HTML documentation
  - `Accept: application/json` → Machine-readable tool metadata (name, description, inputSchema)
- **GET /install.sh** — Bash installation script for Claude Code/Cursor/VS Code with multi-scope support (user/local/project)

**Content negotiation:** Inspects `Accept` header to return HTML or JSON from same endpoint.

---

## Data Flow

```
User/Claude
    │
    ├─→ MCP Tool Call (stdio or HTTP)
    │
    ├─→ rgaa_mcp.py routes to tool handler
    │
    ├─→ Handler validates input (_helpers.py) → data.py → result
    │   OR
    ├─→ Handler fetches HTML → analyseur.py → violations
    │   OR
    ├─→ Handler calculates compliance (taux_conformite)
    │
    ├─→ MCP Tool Response
    │
    ├─→ HTTP endpoint (routes.py) with content negotiation
    │
    └─→ Response (JSON/HTML)
```

---

## Key Design Decisions

### 1. Modular Architecture

**Why:** Separation of concerns enables independent testing, maintenance, and reuse.

- `data.py` loads cache once (lazy-load with memoization)
- `analyseur.py` focuses solely on HTML parsing
- `_helpers.py` centralizes validation for consistency
- `auth.py` handles all token operations
- `routes.py` contains HTTP logic, isolated from MCP tools

### 2. Extracted _helpers.py

**Why:** Avoid code duplication across 10 tools. Validation functions (theme IDs, score ranges) are used by multiple tools. Centralization ensures consistent error messages and behavior.

### 3. Static Analysis Coverage

**Why:** Cannot determine violations for ~43% of criteria without JavaScript/user interaction.

- Tools like `rgaa_analyser` handle automatable checks only
- Complementary `rgaa_checklist` tool provides manual tests for remaining criteria
- README documents which themes are automatable

### 4. Content Negotiation on /guide

**Why:** One endpoint serves both human (HTML) and machine (JSON) audiences.

- Navigating `/guide` in browser → interactive documentation
- Programmatic clients (`Accept: application/json`) → structured metadata for integration

### 5. HTTP Token Auth (Optional)

**Why:** stdio mode (local) requires no auth. HTTP mode (network) requires bearer tokens for security.

- Tokens stored in volume, never in Docker image
- Tokens expire automatically (checked on each request)
- CLI commands (--generate-token, --list-tokens, --revoke-token) manage tokens

---

## Testing

### Test Coverage: 250 Tests

Tests live in `tests/` directory with pytest.

```
tests/
├── test_tools.py        # MCP tool functionality (10 tools)
├── test_analyseur.py    # HTML static analyzer
├── test_referentiel.py  # Criteria access and search
└── test_conformite.py   # Compliance rate calculation
```

**Test categories:**
- **Referential tests:** Cache loading, criteria lookup, theme filtering, search/fuzzy matching, glossary
- **Analyzer tests:** HTML parsing, violation detection per theme, valid/invalid markup
- **Tool tests:** Input validation, edge cases, output schema compliance
- **HTTP tests:** Content negotiation, endpoint status codes, JSON/HTML responses
- **Auth tests:** Token generation, expiration, verification

### Running Tests

```bash
# Locally
pip install -e ".[dev]"
python -m pytest tests/ -v

# Via Docker
docker build -t rgaa-mcp-test .
docker run --rm --entrypoint python rgaa-mcp-test -m pytest tests/ -v

# Count tests
python -m pytest tests/ --collect-only -q
```

---

## Initialization & Startup

1. **Mode Detection:** Check `MCP_TRANSPORT` env var (default: stdio)

2. **Stdio Mode (default):**
   - Load cache (rgaa_cache.json)
   - No authentication
   - FastMCP server reads from stdin, writes to stdout

3. **HTTP Mode:**
   - Load cache (rgaa_cache.json)
   - Load tokens from `tokens/tokens.json`
   - Build token verifier if tokens exist
   - Start FastMCP in HTTP server (default port 8000)
   - Mount routes for /, /guide, /install.sh

4. **Health Check:**
   ```bash
   docker run --rm rgaa-mcp --health
   # Output: OK: 106 critères chargés
   ```

---

## Summary: Phase 3 Completion

**Phase 3 (modularization) delivered:**

| Module | Responsibility | Lines |
|--------|-----------------|-------|
| rgaa_mcp.py | Server orchestration, 10 tools, 4 resources | ~1400 |
| data.py | Cache loading, lazy memoization | ~26 |
| analyseur.py | HTML parsing, violation detection | ~320 |
| _helpers.py | Shared validation functions | ~68 |
| auth.py | Token lifecycle, verification | ~120 |
| routes.py | HTTP endpoints, content negotiation | ~1100 |

**Architectural improvements:**
- ✅ Single responsibility per module
- ✅ Testable, reusable components
- ✅ Centralized validation (_helpers.py)
- ✅ Isolated HTTP logic (routes.py)
- ✅ 250 comprehensive tests

**Phase 4 delivered:**
- ✅ GET / (homepage with status)
- ✅ GET /guide with content negotiation (HTML + JSON)
- ✅ GET /install.sh (multi-scope installation)
- ✅ 250 tests including HTTP endpoint tests with content negotiation
