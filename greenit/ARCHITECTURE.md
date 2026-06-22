# GreenIT MCP Server — Architecture

## Overview

GreenIT MCP is a Model Context Protocol server that provides access to the 119 ecodesign best practices from the GreenIT reference framework (RWEB_0001 → RWEB_0119). It enables Claude and other MCP clients to discover ecodesign practices, compare their impact, calculate EcoIndex scores, and search by sustainability criteria—all without external API dependencies.

**Key responsibilities:**
- Expose 9 MCP tools for referential access, practice comparison, and EcoIndex calculation
- Provide 3 MCP resources (index, practice details, metadata)
- Support two transport modes: stdio (local) and HTTP (network, with token authentication)
- Calculate EcoIndex scores (0-100) and environmental impact grades (A-G)
- Manage bearer token authentication for HTTP mode
- Serve HTTP endpoints (/, /guide, /install.sh) with content negotiation

---

## Module Structure

### greenit_mcp.py — Main Server

**Responsibility:** Orchestrates the FastMCP server, defines all MCP tools and resources, handles startup logic including token verification and HTTP routing.

**Key exports:**
- **9 MCP Tools:**
  - `lister_fiches` — List all practices or filter by lifecycle, resource type, impact, priority
  - `fiches_prioritaires` — Return high-impact, high-priority practices (sorted by ei+pi score)
  - `chercher_fiche` — Search by keyword with relevance scoring
  - `comparer_fiches` — Compare multiple practices side-by-side with impact matrix
  - `obtenir_fiche_complete` — Fetch full practice details (description, validations, principles)
  - `obtenir_statistiques` — Return referential statistics (distributions, top 5)
  - `lister_lifecycles` — List 7 lifecycle phases with practice count per phase
  - `lister_ressources` — List 8 saved resource types with practice count per resource
  - `calculer_ecoindex` — Calculate EcoIndex score (0-100) and grade (A-G) from page metrics

- **3 MCP Resources:**
  - `greenit://index` — Lightweight index of all practices
  - `greenit://fiche/{id}` — Full practice content (RWEB_0051, etc.)
  - `greenit://metadata` — Referential metadata (languages, versions, source)
  - `greenit://version` — Server and data version

**Process flow:**
1. Startup: Load cache (greenit_cache.json), metadata (greenit_metadata.json), set up token verifier if HTTP mode
2. Inject version and routes into modules
3. FastMCP server runs with selected transport (stdio or HTTP)
4. On tool call: Delegate to specialized modules (data.py, _helpers.py)

---

### data.py — Cache Loading, Metadata, & EcoIndex

**Responsibility:** Single source of truth for loading and caching GreenIT referential data, managing metadata, and calculating EcoIndex scores. Merged ecoindex.py into this module for better maintainability.

**Key functions:**
- `charger_cache()` — Load practices from greenit_cache.json (lazy-load with memoization)
- `charger_metadata()` — Load metadata from greenit_metadata.json with fallback defaults
- `sauvegarder_cache(data)` — Persist practices to greenit_cache.json
- `sauvegarder_metadata(data)` — Persist metadata to greenit_metadata.json
- `calculer_ecoindex(dom, requests, size_kb)` — Calculate EcoIndex score and grade from page metrics
- `compter_fiches()` — Count total practices in cache
- `compter_lifecycles()` — Count unique lifecycle phases
- `compter_ressources()` — Count unique saved resource types

**Data structure:**
```json
{
  "RWEB_0049": {
    "title": "...",
    "description": "...",
    "lifecycle": "3-development",
    "saved_resources": ["network", "cpu"],
    "impact": 4,
    "priority": 4,
    "validations": [...],
    "principles": [...]
  },
  ...
}
```

**EcoIndex calculation (merged from ecoindex.py):**
- Quantile-based algorithm using DOM nodes, HTTP requests, and page size (KB)
- Converts metrics to percentile ranks (0-20)
- Weighted formula: `score = 100 - 5 * (3*q_dom + 2*q_req + q_size) / 6`
- Grades: A (≥80), B (≥70), C (≥55), D (≥40), E (≥25), F (≥10), G (<10)

---

### _helpers.py — Shared Validation

**Responsibility:** Centralized validation functions used by multiple tools to ensure consistent error handling and parameter validation.

**Key functions:**
- `validate_lifecycles(lifecycles: list[str] | None)` — Validate lifecycle IDs against known phases
- `validate_resources(resources: list[str] | None)` — Validate saved resource types
- `validate_score_range(value: int, min_val: int, max_val: int, param_name: str)` — Validate numeric parameter within range
- `validate_nonnegative(value: float, param_name: str)` — Validate numeric parameter is ≥ 0

**Usage pattern:** Called by tools before processing user input to fail fast with user-friendly French error messages.

---

### auth.py — Token Management

**Responsibility:** Generate, store, list, revoke, and verify bearer tokens for HTTP mode authentication.

**Key functions:**
- `cmd_generate_token(path, name, expires_days=365)` — Create new token with expiration date
- `cmd_list_tokens(path)` — Display all tokens (active and expired)
- `cmd_revoke_token(path, token)` — Revoke specific token
- `charger_tokens(path) → dict` — Load tokens from tokens.json
- `tokens_pour_auth(path) → dict` — Load and filter non-expired tokens for FastMCP auth
- `construire_verifier(path) → StaticTokenVerifier` — Build token verifier for FastMCP

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
    ├─→ greenit_mcp.py routes to tool handler
    │
    ├─→ Handler validates input (_helpers.py) → data.py → result
    │   OR
    ├─→ Handler calculates EcoIndex (data.py.calculer_ecoindex)
    │   OR
    ├─→ Handler compares practices (data.py) with impact matrix
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
- `data.py` includes EcoIndex calculation (previously separate ecoindex.py)
- `_helpers.py` centralizes validation for consistency
- `auth.py` handles all token operations
- `routes.py` contains HTTP logic, isolated from MCP tools

### 2. Merged ecoindex.py into data.py

**Why:** EcoIndex is a data transformation, not a separate concern. Consolidating reduces module count, simplifies imports, and keeps related functionality together.

**What was merged:**
- Quantile tables for DOM, requests, and size
- Grade boundaries (A-G)
- Quantile computation algorithm
- `calculer_ecoindex(dom, requests, size_kb)` function

### 3. Extracted _helpers.py

**Why:** Avoid code duplication across 9 tools. Validation functions (lifecycle/resource IDs, score ranges) are used by multiple tools. Centralization ensures consistent error messages and behavior.

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

### Test Coverage: 207 Tests

Tests live in `tests/` directory with pytest.

```
tests/
└── test_tools.py        # MCP tool functionality (9 tools), HTTP endpoints, validations
```

**Test categories:**
- **Referential tests:** Cache loading, practice lookup, lifecycle/resource filtering, search/scoring
- **Tool tests:** Input validation, edge cases, output schema compliance
- **EcoIndex tests:** Quantile computation, score calculation, grade assignment
- **HTTP tests:** Content negotiation, endpoint status codes, JSON/HTML responses
- **Auth tests:** Token generation, expiration, verification

### Running Tests

```bash
# Locally
python -m pytest tests/ -v

# Via Docker
docker build -t greenit-mcp-test .
docker run --rm --entrypoint python greenit-mcp-test -m pytest tests/ -v

# Count tests
python -m pytest tests/ --collect-only -q
```

---

## Initialization & Startup

1. **Mode Detection:** Check `MCP_TRANSPORT` env var (default: stdio)

2. **Stdio Mode (default):**
   - Load cache (greenit_cache.json)
   - Load metadata (greenit_metadata.json)
   - No authentication
   - FastMCP server reads from stdin, writes to stdout

3. **HTTP Mode:**
   - Load cache (greenit_cache.json)
   - Load metadata (greenit_metadata.json)
   - Load tokens from `tokens/tokens.json`
   - Build token verifier if tokens exist
   - Start FastMCP in HTTP server (default port 8000)
   - Mount routes for /, /guide, /install.sh

4. **Health Check:**
   ```bash
   docker run --rm greenit-mcp --health
   # Output: OK: 119 fiches chargées
   ```

---

## Summary: Phase 3 Completion

**Phase 3 (modularization) delivered:**

| Module | Responsibility | Lines |
|--------|-----------------|-------|
| greenit_mcp.py | Server orchestration, 9 tools, 3 resources | ~1450 |
| data.py | Cache loading, metadata, EcoIndex calculation | ~250 |
| _helpers.py | Shared validation functions | ~80 |
| auth.py | Token lifecycle, verification | ~150 |
| routes.py | HTTP endpoints, content negotiation | ~1100 |

**Architectural improvements:**
- ✅ Single responsibility per module
- ✅ Testable, reusable components
- ✅ EcoIndex merged into data.py for maintainability
- ✅ Centralized validation (_helpers.py)
- ✅ Isolated HTTP logic (routes.py)
- ✅ 207 comprehensive tests

**Phase 4 delivered:**
- ✅ GET / (homepage with status)
- ✅ GET /guide with content negotiation (HTML + JSON)
- ✅ GET /install.sh (multi-scope installation)
- ✅ HTTP endpoint tests including content negotiation
