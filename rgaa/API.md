# RGAA MCP — API Reference

Serveur MCP exposant le référentiel RGAA 4.2.1 (106 critères d'accessibilité numérique) à Claude et autres clients MCP.

## Table of Contents

1. [Overview](#overview)
2. [Tools](#tools)
   - [Reference & Listing](#reference--listing)
   - [Analysis & Automation](#analysis--automation)
   - [Testing & Reporting](#testing--reporting)
3. [Prompts](#prompts)
4. [Resources](#resources)
5. [Configuration](#configuration)

---

## Overview

RGAA MCP is a production-ready accessibility audit tool that exposes the French accessibility standard (RGAA 4.2.1) as an MCP service. It provides 10 tools for querying the reference, performing automated analysis, generating test checklists, and calculating compliance rates.

**Key Facts:**
- **106 RGAA criteria** across 13 themes
- **~57% automated** (themes 1, 2, 5, 6, 8, 9, 11, 12)
- **8 prompts** for guided workflows
- **4 resources** for static data access
- **Token-based auth** for HTTP transport

**Quick Start:**
```bash
# stdio (local)
docker run --rm -i rgaa-mcp

# HTTP with auth
docker compose up -d
docker run --rm -v $(pwd)/tokens:/app/tokens rgaa-mcp --generate-token --name "Alice"
```

---

## Tools

### Reference & Listing

#### `rgaa_lister_criteres`

Lists RGAA criteria with optional filters by theme or WCAG level.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `theme` | `integer` | No | Theme number (1-13). If `None`, includes all themes. |
| `niveau_wcag` | `Literal["A", "AA", "AAA"]` | No | WCAG level to filter. If `None`, includes all levels. |

**Returns:** `{"total": int, "criteres": [...]}`

Each criterion includes:
- `id` (string): Criterion ID (e.g., "1.1", "11.3")
- `theme` (integer): Theme number
- `titre` (string): Criterion title
- `automatisable` (boolean): Whether automated testing is possible
- `niveau` (string): WCAG level (A, AA, or AAA)

**Example:**
```json
{
  "total": 6,
  "criteres": [
    {
      "id": "1.1",
      "theme": 1,
      "titre": "Chaque image a une alternative textuelle",
      "automatisable": true,
      "niveau": "A"
    }
  ]
}
```

**Usage Examples:**
```python
# All criteria
rgaa_lister_criteres()

# Only theme 6 (Forms)
rgaa_lister_criteres(theme=6)

# Only WCAG AA level criteria
rgaa_lister_criteres(niveau_wcag="AA")

# Combine filters
rgaa_lister_criteres(theme=11, niveau_wcag="AAA")
```

---

#### `rgaa_obtenir_critere`

Returns the complete details of a single RGAA criterion.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `id` | `string` | Yes | Criterion ID (e.g., "1.1", "11.3") |

**Returns:** Complete criterion object with all test details and WCAG references.

**Returned Fields:**
- `id`, `theme`, `titre`: Basic info
- `tests` (object): Raw test procedures
- `wcag` (array): WCAG references (e.g., ["1.1.1 (A)"])
- `cas_particuliers` (string): Special cases or exceptions
- `niveau` (string): WCAG level
- `automatisable` (boolean): Automation capability

**Example:**
```json
{
  "id": "1.1",
  "theme": 1,
  "titre": "Chaque image a une alternative textuelle",
  "automatisable": true,
  "wcag": ["1.1.1 (A)"],
  "niveau": "A",
  "tests": {...},
  "cas_particuliers": "Sauf if image is purely decorative"
}
```

**Usage:**
```python
rgaa_obtenir_critere("11.3")
rgaa_obtenir_critere("6.1")
```

---

#### `rgaa_chercher`

Searches criteria and glossary terms by keyword.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `query` | `string` | Yes | Search term (e.g., "images", "formulaires", "couleurs") |
| `scope` | `list[Literal["criteres", "glossaire"]]` | No | Search scope. Defaults to both. |

**Returns:** `{"criteres": [...], "termes_glossaire": [...]}`

Each result includes:
- **Criteria**: `id`, `theme`, `titre`
- **Glossary**: `terme`, `definition`, `examples` (optional)

**Example:**
```json
{
  "criteres": [
    {
      "id": "1.1",
      "theme": 1,
      "titre": "Chaque image a une alternative textuelle"
    }
  ],
  "termes_glossaire": [
    {
      "terme": "alternative textuelle",
      "definition": "Texte décrivant le contenu...",
      "examples": ["alt=\"Logo de la marque\""]
    }
  ]
}
```

**Usage:**
```python
# Search everywhere
rgaa_chercher("images")

# Only glossary
rgaa_chercher("contraste", scope=["glossaire"])

# Only criteria
rgaa_chercher("formulaires", scope=["criteres"])
```

---

#### `rgaa_glossaire`

Returns the definition of a single glossary term (case-insensitive).

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `terme` | `string` | Yes | Term to look up (e.g., "alternatives textuelles") |

**Returns:** `{"terme": string, "definition": string, "exemples": [string] or null}`

**Example:**
```json
{
  "terme": "alternatives textuelles",
  "definition": "Descriptions textuelles des images...",
  "exemples": ["alt=\"Logo de la marque\"", "aria-label=\"Bouton menu\""]
}
```

**Usage:**
```python
rgaa_glossaire("alternatives textuelles")
rgaa_glossaire("contraste de couleur")
```

---

#### `rgaa_statistiques`

Returns reference statistics grouped by theme.

**Parameters:** None

**Returns:** `{"total_criteres": int, "automatisables": int, "manuels": int, "par_theme": {...}}`

**Example:**
```json
{
  "total_criteres": 106,
  "automatisables": 60,
  "manuels": 46,
  "par_theme": {
    "1": {
      "titre": "Images",
      "nb_criteres": 8,
      "automatisables": 7
    }
  }
}
```

**Usage:**
```python
stats = rgaa_statistiques()
print(f"Automated coverage: {stats['automatisables']}/{stats['total_criteres']}")
```

---

#### `rgaa_types_audit`

Lists available audit types and whether they satisfy legal compliance requirements.

**Parameters:** None

**Returns:** `{"types": [{"type": string, "nom": string, "description": string, "conforme_obligation": bool, "nb_criteres": int}]}`

**Example:**
```json
{
  "types": [
    {
      "type": "complet",
      "nom": "Audit complet",
      "description": "All 106 criteria",
      "conforme_obligation": true,
      "nb_criteres": 106
    },
    {
      "type": "rapide",
      "nom": "Audit rapide",
      "description": "Essential level A criteria",
      "conforme_obligation": false,
      "nb_criteres": 25
    }
  ]
}
```

**Usage:**
```python
types = rgaa_types_audit()
legal_audits = [t for t in types['types'] if t['conforme_obligation']]
```

---

#### `rgaa_criteres_audit`

Returns the list of criteria for a specific audit type.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `type` | `Literal["complet", "rapide", "complementaire"]` | Yes | Audit type: "complet" (legal requirement), "rapide" (25 essential A-level), "complementaire" (25 advanced) |

**Returns:** `{"type": string, "nom": string, "conforme_obligation": bool, "nb_criteres": int, "criteres": [...]}`

**Example:**
```json
{
  "type": "rapide",
  "nom": "Audit rapide",
  "conforme_obligation": false,
  "nb_criteres": 25,
  "criteres": [
    {
      "id": "1.1",
      "theme": 1,
      "titre": "Chaque image a une alternative textuelle"
    }
  ]
}
```

**Usage:**
```python
# Legal-compliant audit
full = rgaa_criteres_audit("complet")

# Quick assessment
quick = rgaa_criteres_audit("rapide")
```

---

### Analysis & Automation

#### `rgaa_analyser`

Analyzes a web page for automatable RGAA violations.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `url` | `string` | Yes | Page URL (must start with http:// or https://) |
| `themes` | `list[int]` | No | Theme numbers (1-13). Defaults to automatable themes [1,2,5,6,8,9,11,12]. |

**Returns:** `{"url": string, "date": string, "themes_analyses": [int], "nb_violations": int, "criteres": [...], "note": string}`

Each violation includes criteria details and severity.

**Example:**
```json
{
  "url": "https://example.com",
  "date": "2026-04-26T10:30:00+00:00",
  "themes_analyses": [1, 2, 5, 6, 8, 9, 11, 12],
  "nb_violations": 3,
  "criteres": [
    {
      "id": "1.1",
      "theme": 1,
      "titre": "Images sans alt",
      "violations": 5
    }
  ],
  "note": "Analysis covers ~57% of criteria. Manual testing required for remaining 49%."
}
```

**Usage:**
```python
# Full automated analysis
result = rgaa_analyser("https://example.com")

# Specific themes only
result = rgaa_analyser("https://example.com", themes=[6, 11])
```

---

#### `rgaa_checklist`

Generates a manual testing checklist for specified criteria or themes.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `themes` | `list[int]` | No | Theme numbers (1-13). At least one parameter required. |
| `criteres` | `list[str]` | No | Criterion IDs (e.g., ["1.1", "6.1"]). At least one parameter required. |

**Returns:** `{"criteres": [...]}`

Each item includes:
- `id`: Criterion ID
- `titre`: Criterion title
- `tests`: Array of test procedures with tools needed

**Example:**
```json
{
  "criteres": [
    {
      "id": "1.1",
      "titre": "Images have alternatives",
      "tests": [
        {
          "description": "Check alt attributes on img elements",
          "methode": "Inspect manually with tools below",
          "outils": ["DevTools", "WAVE", "NVDA"]
        }
      ]
    }
  ]
}
```

**Usage:**
```python
# By theme
checklist = rgaa_checklist(themes=[1, 6])

# By specific criteria
checklist = rgaa_checklist(criteres=["1.1", "6.1"])

# Combined
checklist = rgaa_checklist(themes=[1], criteres=["6.1"])
```

---

### Testing & Reporting

#### `rgaa_taux_conformite`

Calculates compliance rate using the official RGAA formula: C / (C + NC) × 100 (N/A excluded).

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `resultats` | `dict` | Yes | Audit results: `{criterion_id: status}` where status is "C" (compliant), "NC" (non-compliant), or "NA" (not applicable). |

**Returns:** `{"taux": float, "nb_conformes": int, "nb_non_conformes": int, "nb_non_applicables": int, "criteres_evalues": int}`

**Example Input:**
```json
{
  "1.1": "C",
  "1.2": "NC",
  "1.3": "NA",
  "6.1": "C"
}
```

**Example Output:**
```json
{
  "taux": 66.67,
  "nb_conformes": 2,
  "nb_non_conformes": 1,
  "nb_non_applicables": 1,
  "criteres_evalues": 3
}
```

**Usage:**
```python
results = {"1.1": "C", "1.2": "NC", "6.1": "C"}
compliance = rgaa_taux_conformite(results)
print(f"Compliance: {compliance['taux']}%")
```

---

## Prompts

Prompts are guided workflows for common audit scenarios. Use with appropriate tool combinations.

### `audit_page`

**Input Arguments:**
- `url` (required): Page to audit
- `themes` (optional): Comma-separated theme numbers (e.g., "1,6,11")

**Description:** Conducts a full RGAA audit by combining automated analysis, manual checklists, and DOM inspection.

**Workflow:**
1. Run automated analysis with `rgaa_analyser`
2. Generate manual checklists for affected themes
3. Retrieve detailed criterion info for NC violations
4. Use Playwright MCP (if available) for advanced DOM checks
5. Synthesize into structured report

---

### `rapport_audit`

**Input Arguments:**
- `resultats` (required): Audit results (JSON or text format)

**Description:** Generates a complete markdown audit report with compliance rate, violations by theme, and prioritized recommendations.

**Report Structure:**
1. Executive summary (compliance %, C/NC/NA counts)
2. Violations by theme with user impact
3. Top 5 recommendations with code examples
4. Methodology note (~57% automated coverage)

---

### `expliquer_critere`

**Input Arguments:**
- `id_critere` (required): Criterion ID (e.g., "1.1", "11.3")

**Description:** Provides pedagogical explanation of a criterion, testing procedure, and real examples.

**Output:**
1. Objective and accessibility impact
2. Affected user profiles
3. Testing steps with tools
4. Compliant/non-compliant code examples
5. WCAG references

---

### `criteres_par_sujet`

**Input Arguments:**
- `sujet` (required): Keyword (e.g., "images", "formulaires", "couleurs")
- `niveau` (optional): WCAG level ("A", "AA", "AAA"). Defaults to "A".

**Description:** Lists criteria related to a subject, filtered by WCAG level.

**Output:** Tabular list (ID, Title, Theme, relevance explanation)

---

### `checklist_audit`

**Input Arguments:**
- `themes` (required): Theme names or numbers (e.g., "formulaires, navigation" or "11,12")

**Description:** Generates a practical manual testing checklist for specified themes.

**Output:**
- Tests organized by theme
- Tools needed for each criterion
- Consolidated tool list

---

### `criteres_wcag`

**Input Arguments:**
- `niveau_wcag` (optional): WCAG level ("A", "AA", "AAA"). Defaults to "AA".

**Description:** Lists all RGAA criteria for a specific WCAG level.

**Output:** Criteria grouped by theme with WCAG references, automation coverage stats

---

### `audit_par_type`

**Input Arguments:**
- `url` (required): Page to audit
- `type` (optional): Audit type ("complet", "rapide", "complementaire"). Defaults to "complet".

**Description:** Conducts audit using a specific audit type's criteria list.

**Output:**
- Audit type info and legal compliance statement
- Violations within scope
- Remaining coverage if not full audit

---

### `audit_rapide` / `audit_complementaire`

**Input Arguments:**
- `url` (required): Page to audit

**Description:**
- **audit_rapide**: Quick assessment with 25 essential A-level criteria (diagnostic, not legally compliant)
- **audit_complementaire**: Advanced criteria (25 image, media, table, consultation criteria)

**Output:** Concise report with violations, recommendations, and scope disclaimer

---

## Resources

Static resources accessible via MCP resource protocol.

### `rgaa://version`

**Description:** Server and data version information

**Example Response:**
```json
{
  "server_version": "1.2.0",
  "data_version": "4.2.1",
  "data_updated_at": "2026-04-20T10:30:00Z",
  "nb_criteres": 106
}
```

---

### `rgaa://index`

**Description:** Lightweight index of all criteria (id, theme, title, level, automation status)

**Example Response:**
```json
[
  {
    "id": "1.1",
    "theme": 1,
    "titre": "Chaque image a une alternative textuelle",
    "niveau": "A",
    "automatisable": true
  },
  ...
]
```

---

### `rgaa://criteres/{id}`

**Description:** Complete details of a criterion (equivalent to `rgaa_obtenir_critere`)

**Example:** `rgaa://criteres/1.1` returns full criterion object

---

### `rgaa://metadata`

**Description:** Reference metadata (languages, versions, source, statistics)

**Example Response:**
```json
{
  "languages": ["fr"],
  "versions": ["4.2.1"],
  "source": "https://github.com/DISIC/RGAA",
  "updated_at": "2026-04-20T10:30:00Z",
  "nb_criteres": 106,
  "nb_themes": 13,
  "taux_automatisable": 57.1
}
```

---

## Configuration

### Environment Variables

| Variable | Default | Usage |
|----------|---------|-------|
| `MCP_TRANSPORT` | `stdio` | `stdio` (local) or `http` (remote) |
| `MCP_HOST` | `0.0.0.0` | Bind address (HTTP mode only) |
| `MCP_PORT` | `8000` | Server port (HTTP mode only) |
| `MCP_BASE_URL` | auto | Public URL if behind reverse proxy |
| `MCP_TOKEN_REQUEST_URL` | empty | URL for token request form |
| `ADMIN_TOKEN` | empty | Secret for the admin token API (HTTP only) |

### Token Management

```bash
# Generate token
docker run --rm -v $(pwd)/tokens:/app/tokens rgaa-mcp \
  --generate-token --name "Alice" --expires-days 365

# List tokens
docker run --rm -v $(pwd)/tokens:/app/tokens rgaa-mcp --list-tokens

# Revoke token
docker run --rm -v $(pwd)/tokens:/app/tokens rgaa-mcp \
  --revoke-token <token>
```

### Testing

```bash
cd /Users/renaudheluin/DEV/mcp-rgaa
python -m pytest tests/ -v
```

---

## Integration Examples

### Basic Criterion Lookup

```python
# Get criterion details
critere = rgaa_obtenir_critere("1.1")
print(f"Title: {critere['titre']}")
print(f"WCAG: {critere['wcag']}")
print(f"Automated: {critere['automatisable']}")
```

### Page Audit with Report

```python
# Run automated analysis
violations = rgaa_analyser("https://example.com")

# For each theme with violations, create checklist
for theme_id in violations['themes_analyses']:
    checklist = rgaa_checklist(themes=[theme_id])
    # Review manual tests...

# Calculate compliance if manual audit done
results = {"1.1": "C", "1.2": "NC", "6.1": "C"}
rate = rgaa_taux_conformite(results)
print(f"Compliance: {rate['taux']}%")
```

### Search-Based Discovery

```python
# Find all criteria related to images
images = rgaa_chercher("images")
for criterion in images['criteres']:
    print(f"{criterion['id']}: {criterion['titre']}")

# Get definition of term
term = rgaa_glossaire("alternative textuelle")
print(term['definition'])
```

---

---

## Admin Token API

Available in HTTP mode when the `ADMIN_TOKEN` environment variable is set. All endpoints require `Authorization: Bearer <ADMIN_TOKEN>` header.

**Error codes common to all endpoints:**

| Condition | Status | Body |
|-----------|--------|------|
| `ADMIN_TOKEN` not set | 503 | `{"error": "Admin API disabled"}` |
| Missing or wrong auth | 401 | `{"error": "Unauthorized"}` |
| Token not found | 404 | `{"error": "Token not found"}` |
| Invalid request body | 400 | `{"error": "<detail>"}` |

---

### `GET /admin/tokens`

List all tokens (active, expired, and revoked).

**Auth:** `Authorization: Bearer <ADMIN_TOKEN>`

**Response:** `200 OK`
```json
[
  {
    "id": "a3f8c012",
    "name": "Alice",
    "created_at": "2026-01-01T00:00:00Z",
    "expires_at": 1767225600,
    "updated_at": "2026-01-01T00:00:00Z",
    "status": "active"
  }
]
```

---

### `POST /admin/tokens`

Create a new MCP access token.

**Auth:** `Authorization: Bearer <ADMIN_TOKEN>`

**Request body:**
```json
{"name": "Alice", "expires_days": 365}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Display name for the token |
| `expires_days` | integer | No | Validity in days (default: 365) |

**Response:** `201 Created`
```json
{
  "token": "<value>",
  "id": "a3f8c012",
  "name": "Alice",
  "expires_at": 1767225600,
  "created_at": "2026-01-01T00:00:00Z"
}
```

> The `token` field is only returned at creation time. Store it immediately.

---

### `GET /admin/tokens/{id}`

Get details for a specific token by its short ID.

**Auth:** `Authorization: Bearer <ADMIN_TOKEN>`

**Path parameter:** `id` — short token ID (e.g., `a3f8c012`)

**Response:** `200 OK` — same shape as one entry from `GET /admin/tokens`

---

### `PATCH /admin/tokens/{id}`

Update a token's name and/or expiration.

**Auth:** `Authorization: Bearer <ADMIN_TOKEN>`

**Path parameter:** `id` — short token ID

**Request body (at least one field required):**
```json
{"name": "Alice Renamed", "expires_days": 180}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | No | New display name |
| `expires_days` | integer | No | New expiration from now in days |

**Response:** `200 OK` — updated token object (same shape as GET by id)

---

### `DELETE /admin/tokens/{id}`

Revoke a token immediately.

**Auth:** `Authorization: Bearer <ADMIN_TOKEN>`

**Path parameter:** `id` — short token ID

**Response:** `200 OK`
```json
{"status": "revoked", "id": "a3f8c012"}
```

---

## Notes

- **Automation Coverage**: ~57% of criteria can be tested automatically. The remaining ~43% require manual testing or specialized tools.
- **WCAG Alignment**: All 106 RGAA criteria map to WCAG 2.1 (A, AA, or AAA levels).
- **Legal Requirement**: Only a complete audit (all 106 criteria) satisfies French legal compliance. Quick and complementary audits are diagnostic only.
- **Tools Required**: Automated analysis uses static HTML parsing. Manual testing requires DevTools, accessibility scanners (WAVE), or screen readers (NVDA, JAWS).
