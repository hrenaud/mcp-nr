# GreenIT MCP — API Reference

Serveur MCP exposant le référentiel GreenIT (bonnes pratiques web écologiques) à Claude et autres clients MCP.

## Table of Contents

1. [Overview](#overview)
2. [Tools](#tools)
   - [Discovery & Filtering](#discovery--filtering)
   - [Analysis & Comparison](#analysis--comparison)
   - [Statistics & Metrics](#statistics--metrics)
3. [Prompts](#prompts)
4. [Resources](#resources)
5. [Configuration](#configuration)

---

## Overview

GreenIT MCP is a production-ready environmental sustainability tool that exposes best practices for reducing web carbon footprint. It provides 9 tools for discovering recommendations, calculating EcoIndex scores, comparing practices by impact, and analyzing resource savings.

**Key Facts:**
- **100+ fiches** (recommendations) covering web sustainability
- **7 lifecycle phases** (specification to retirement)
- **8 resource types** (network, CPU, RAM, storage, requests, electricity, GHG, e-waste)
- **9 tools** with comprehensive filtering and analysis
- **Prompts** for guided workflows (audit, reporting, optimization)
- **Token-based auth** for HTTP transport

**Quick Start:**
```bash
# stdio (local)
docker run --rm -i greenit-mcp

# HTTP with auth
docker compose up -d
docker run --rm -v $(pwd)/tokens:/app/tokens greenit-mcp --generate-token --name "Alice"
```

---

## Tools

### Discovery & Filtering

#### `lister_fiches`

Lists GreenIT fiches with optional filters by lifecycle, resource, or impact/priority thresholds.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `lifecycle` | `string` | No | Lifecycle phase (e.g., "3-developement", "2-conception"). Use `lister_lifecycles()` to see all. |
| `saved_resource` | `string` | No | Resource type to filter (e.g., "network", "cpu", "requests"). Use `lister_ressources()` to see all. |
| `impact_min` | `integer` | No | Minimum environmental impact score (1-5). |
| `priorite_min` | `integer` | No | Minimum implementation priority score (1-5). |

**Returns:** `{"fiches": [...]}`

Each fiche includes:
- `id` (string): Unique identifier (e.g., "RWEB_0051")
- `num` (string): Fiche number
- `titre` (string): Title
- `environmental_impact` (integer): Impact score (1-5)
- `priority_implementation` (integer): Priority score (1-5)
- `lifecycle` (string): Lifecycle phase
- `saved_resources` (array): Resource types saved

**Example:**
```json
{
  "fiches": [
    {
      "id": "RWEB_0051",
      "num": "51",
      "titre": "Minifier CSS et JavaScript",
      "environmental_impact": 4,
      "priority_implementation": 5,
      "lifecycle": "3-developement",
      "saved_resources": ["network", "requests"]
    }
  ]
}
```

**Usage Examples:**
```python
# All fiches
result = lister_fiches()

# Only development phase
result = lister_fiches(lifecycle="3-developement")

# Network optimization only
result = lister_fiches(saved_resource="network")

# High impact + quick to implement
result = lister_fiches(impact_min=4, priorite_min=4)

# Combine filters
result = lister_fiches(lifecycle="3-developement", impact_min=3)
```

---

#### `fiches_prioritaires`

Returns high-impact, high-priority fiches sorted by combined score.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `impact_min` | `integer` | No | Minimum environmental impact (1-5). Defaults to 4. |
| `priorite_min` | `integer` | No | Minimum implementation priority (1-5). Defaults to 4. |

**Returns:** `{"fiches": [...]}`

Each fiche includes:
- All fields from `lister_fiches` plus:
- `description` (string): Short description (up to 300 chars)
- `score` (integer): Combined score (impact + priority)
- `url` (string): Link to fiche details

**Example:**
```json
{
  "fiches": [
    {
      "id": "RWEB_0051",
      "num": "51",
      "titre": "Minifier CSS et JavaScript",
      "description": "Réduire la taille des fichiers CSS...",
      "environmental_impact": 4,
      "priority_implementation": 5,
      "score": 9,
      "lifecycle": "3-developement",
      "saved_resources": ["network", "requests"],
      "url": "https://rweb.greenit.fr/fiches/51"
    }
  ]
}
```

**Usage:**
```python
# Default: impact >= 4 and priority >= 4
top = fiches_prioritaires()

# Lower thresholds
top = fiches_prioritaires(impact_min=3, priorite_min=3)

# For budget-constrained projects
urgent = fiches_prioritaires(impact_min=5, priorite_min=5)
```

---

#### `chercher_fiche`

Searches fiches by keyword with relevance scoring.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `terme` | `string` | Yes | Search keyword (e.g., "images", "caching", "minify") |

**Returns:** `{"fiches": [...]}`

Each result includes:
- `id`, `num`, `titre`: Basic info
- `apercu` (string): Short description (up to 200 chars)
- `environmental_impact`, `priority_implementation`: Scores
- `pertinence` (integer): Relevance score (higher = better match)

Results are sorted by relevance (max 15).

**Example:**
```json
{
  "fiches": [
    {
      "id": "RWEB_0051",
      "num": "51",
      "titre": "Minifier CSS et JavaScript",
      "apercu": "Réduire la taille des fichiers...",
      "environmental_impact": 4,
      "priority_implementation": 5,
      "pertinence": 10
    }
  ]
}
```

**Scoring Logic:**
- Title match: +10 points
- Short description match: +5 points
- Full description match: +3 points
- Resource match: +2 points
- Lifecycle match: +1 point

**Usage:**
```python
# Find image optimization tips
images = chercher_fiche("images")

# Find caching strategies
caching = chercher_fiche("cache")

# Network optimization
network = chercher_fiche("réseau")
```

---

### Analysis & Comparison

#### `obtenir_fiche_complete`

Returns the complete details of a single fiche.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `fiche_id` | `string` | Yes | Fiche ID (e.g., "RWEB_0051") |

**Returns:** Complete fiche object with all fields

**Major Fields:**
- `id`, `num`, `title`, `shortDescription`, `description`: Content
- `environmental_impact`, `priority_implementation`: Scores
- `lifecycle`: Lifecycle phase
- `saved_resources`: Array of resource types
- `url`: Reference link
- `principes_de_validation`: Validation rules

**Example:**
```json
{
  "id": "RWEB_0051",
  "num": "51",
  "title": "Minify CSS and JavaScript files",
  "shortDescription": "Reduce file size by removing...",
  "description": "Detailed explanation of minification benefits...",
  "environmental_impact": 4,
  "priority_implementation": 5,
  "lifecycle": "3-developement",
  "saved_resources": ["network", "requests"],
  "url": "https://rweb.greenit.fr/fiches/51",
  "principes_de_validation": [
    "CSS files must be < 100KB",
    "JS files must be < 500KB"
  ]
}
```

**Usage:**
```python
fiche = obtenir_fiche_complete("RWEB_0051")
print(f"Title: {fiche['title']}")
print(f"Impact: {fiche['environmental_impact']}/5")
print(f"How to validate: {fiche['principes_de_validation']}")
```

---

#### `comparer_fiches`

Compares multiple fiches side-by-side with scoring and recommendation.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `fiche_ids` | `List[str]` | Yes | List of fiche IDs (e.g., ["RWEB_0049", "RWEB_0051"]) |

**Returns:** `{"comparaison": [...], "recommandation": {...}}`

Comparison includes:
- All fields from each fiche
- `score_combined`: Sum of impact + priority
- Sorted by combined score (highest first)

Recommendation includes:
- `priorite_1`: Top recommended fiche ID
- `classement`: Array of fiche IDs ranked by score
- `note`: Explanation of ranking

**Example:**
```json
{
  "comparaison": [
    {
      "id": "RWEB_0051",
      "titre": "Minify CSS and JavaScript",
      "environmental_impact": 4,
      "priority_implementation": 5,
      "score_combined": 9,
      "saved_resources": ["network", "requests"],
      ...
    }
  ],
  "recommandation": {
    "priorite_1": "RWEB_0051",
    "classement": ["RWEB_0051", "RWEB_0049"],
    "note": "Ranking based on combined impact + priority score"
  }
}
```

**Usage:**
```python
# Compare optimization strategies
comparison = comparer_fiches(["RWEB_0049", "RWEB_0051", "RWEB_0052"])
print(f"Best choice: {comparison['recommandation']['priorite_1']}")
for fiche_id in comparison['recommandation']['classement']:
    print(f"  {fiche_id}")
```

---

### Statistics & Metrics

#### `lister_lifecycles`

Lists the 7 lifecycle phases with count of fiches in each.

**Parameters:** None

**Returns:** `{"lifecycles": [...]}`

Each entry includes:
- `id` (string): Phase ID (e.g., "3-developement")
- `label` (string): French label (e.g., "Développement")
- `count` (integer): Number of fiches in this phase

**Example:**
```json
{
  "lifecycles": [
    {
      "id": "1-specification",
      "label": "Spécification",
      "count": 15
    },
    {
      "id": "2-concept",
      "label": "Conception",
      "count": 22
    },
    {
      "id": "3-developement",
      "label": "Développement",
      "count": 35
    },
    {
      "id": "4-production",
      "label": "Production",
      "count": 18
    },
    {
      "id": "5-utilization",
      "label": "Utilisation",
      "count": 12
    },
    {
      "id": "6-support",
      "label": "Support",
      "count": 8
    },
    {
      "id": "7-retirement",
      "label": "Fin de vie",
      "count": 5
    }
  ]
}
```

**Usage:**
```python
# Get all phases
phases = lister_lifecycles()

# Use phase ID to filter fiches
dev_fiches = lister_fiches(lifecycle="3-developement")
```

---

#### `lister_ressources`

Lists the 8 resource types with count of fiches saving each.

**Parameters:** None

**Returns:** `{"ressources": [...]}`

Each entry includes:
- `id` (string): Resource ID (e.g., "network", "cpu")
- `label` (string): French label (e.g., "Réseau")
- `count` (integer): Number of fiches saving this resource

Sorted by count (most to least).

**Example:**
```json
{
  "ressources": [
    {
      "id": "network",
      "label": "Réseau",
      "count": 45
    },
    {
      "id": "requests",
      "label": "Requêtes",
      "count": 38
    },
    {
      "id": "cpu",
      "label": "Processeur",
      "count": 32
    },
    {
      "id": "storage",
      "label": "Stockage",
      "count": 28
    },
    {
      "id": "ram",
      "label": "Mémoire vive",
      "count": 22
    },
    {
      "id": "electricity",
      "label": "Consommation électrique",
      "count": 18
    },
    {
      "id": "ghg",
      "label": "Émissions de gaz à effet de serre",
      "count": 15
    },
    {
      "id": "e-waste",
      "label": "Déchets électroniques",
      "count": 10
    }
  ]
}
```

**Usage:**
```python
# Get all resource types
resources = lister_ressources()

# Find fiches that reduce network usage
network_fiches = lister_fiches(saved_resource="network")

# Find fiches that reduce electricity
green_fiches = lister_fiches(saved_resource="electricity")
```

---

#### `obtenir_statistiques`

Returns advanced reference statistics with distributions and top fiches.

**Parameters:** None

**Returns:** Complex object with:
- `total_fiches`: Total count
- `data_version`: Data version string
- `updated_at`: Last update timestamp
- `distribution_lifecycle`: Fiche counts per phase
- `distribution_ressources`: Fiche counts per resource
- `distribution_impact_environnemental`: Count of fiches by impact score (1-5)
- `distribution_priorite_implementation`: Count of fiches by priority score (1-5)
- `top_5_score_combine`: Top 5 fiches by combined score

**Example:**
```json
{
  "total_fiches": 115,
  "data_version": "2.3.0",
  "updated_at": "2026-04-20T10:30:00Z",
  "distribution_lifecycle": {
    "1-specification": 15,
    "2-concept": 22,
    "3-developement": 35,
    "4-production": 18,
    "5-utilization": 12,
    "6-support": 8,
    "7-retirement": 5
  },
  "distribution_ressources": {
    "network": 45,
    "requests": 38,
    "cpu": 32,
    ...
  },
  "distribution_impact_environnemental": {
    "1": 5,
    "2": 15,
    "3": 40,
    "4": 35,
    "5": 20
  },
  "distribution_priorite_implementation": {
    "1": 8,
    "2": 18,
    "3": 42,
    "4": 32,
    "5": 15
  },
  "top_5_score_combine": [
    {
      "id": "RWEB_0051",
      "titre": "Minify CSS and JavaScript",
      "score": 9
    }
  ]
}
```

**Usage:**
```python
stats = obtenir_statistiques()
print(f"Total fiches: {stats['total_fiches']}")
print(f"Most common resource to save: {max(stats['distribution_ressources'], key=stats['distribution_ressources'].get)}")
print(f"Average impact: {sum([int(k)*v for k,v in stats['distribution_impact_environnemental'].items()]) / stats['total_fiches']}")
```

---

#### `calculer_ecoindex`

Calculates EcoIndex score and grade from 3 raw metrics.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `dom_nodes` | `integer` | Yes | Number of DOM nodes on the page |
| `requests` | `integer` | Yes | Number of HTTP requests |
| `size_kb` | `float` | Yes | Total page size transferred in kilobytes |
| `url` | `string` | No | Optional URL for context |

**Returns:** `{"url": string, "dom_nodes": int, "requests": int, "size_kb": float, "score": int, "grade": string}`

**Score Range:** 0-100 (higher is better)
**Grades:** A (excellent), B, C, D, E, F, G (poor)

**Example:**
```json
{
  "url": "https://example.com",
  "dom_nodes": 850,
  "requests": 42,
  "size_kb": 1850.5,
  "score": 62,
  "grade": "D"
}
```

**Measurement Protocol:**
1. Open context with 1920x1080 viewport (EcoIndex spec)
2. Navigate to page
3. Wait 3 seconds
4. Scroll to bottom progressively
5. Wait 3 seconds
6. Measure DOM nodes, HTTP requests, total size (KB)
7. Call this tool

**Usage:**
```python
# Measure a page
result = calculer_ecoindex(
    dom_nodes=850,
    requests=42,
    size_kb=1850.5,
    url="https://example.com"
)
print(f"EcoIndex: {result['score']}/100 (Grade {result['grade']})")

# Identify optimization targets
if result['score'] < 50:
    print("Consider: network optimization, DOM reduction, request minification")
```

---

## Prompts

Prompts are guided workflows for common sustainability analysis scenarios.

### `audit_ecoindex`

**Input Arguments:**
- `url` (required): Page URL to analyze
- `focus` (optional): Optimization focus area ("all", "dom", "requests", "size")

**Description:** Analyzes a page's environmental impact via EcoIndex, interprets results, and recommends optimizations.

**Workflow:**
1. Measure page metrics (DOM, requests, size)
2. Calculate EcoIndex score and grade
3. Interpret against benchmarks
4. Recommend top 3-5 optimizations if score < 50

---

### `rapport_impact`

**Input Arguments:**
- `resultats` (required): Audit results to analyze

**Description:** Generates a structured environmental impact report.

**Report Structure:**
1. Title: "Environmental Impact Report"
2. Summary: Global EcoIndex score and interpretation
3. Details by metric: DOM, requests, size
4. Recommendations: 5-10 actions ranked by potential impact
5. Resource savings: Estimated energy/CO2 savings per optimization

---

### `expliquer_fiche`

**Input Arguments:**
- `fiche_id` (required): Fiche ID (e.g., "RWEB_0001")

**Description:** Explains a sustainability recommendation in detail.

**Content:**
1. Objective and environmental benefit
2. Resources saved (CPU, network, storage, energy)
3. Implementation steps (design/development/testing)
4. 2-3 concrete code/pattern examples
5. Measurable impacts (before/after metrics)

**Language:** Pedagogical, accessible to developers

---

### `fiches_par_lifecycle`

**Input Arguments:**
- `phase` (required): Lifecycle phase name
- `impact_min` (optional): Minimum impact threshold (1-5). Defaults to 3.

**Description:** Finds recommendations for a specific project phase.

**Output:**
1. All applicable fiches for the phase
2. Organized by domain (architecture, frontend, backend, infrastructure)
3. Summary of each fiche (1 line)
4. Recommended implementation order (by ROI)

---

### `checklist_ecoindex`

**Input Arguments:**
- `domaines` (optional): Domains to focus ("all", "dom", "requests", "size", "js", "images", "css")

**Description:** Creates a manual optimization checklist.

**Format:**
- Organized by category (DOM reduction, HTTP reduction, transfer size reduction)
- Each item is manually verifiable
- Estimated implementation time
- Impact level (High/Medium/Low)
- Uses reference statistics for context

---

### `ressources_comparaison`

**Input Arguments:**
- `fiche_ids` (required): Comma-separated fiche IDs (e.g., "RWEB_0001,RWEB_0002")

**Description:** Compares resource savings across multiple recommendations.

**Output:**
1. Fetch each fiche with details
2. Extract saved resources (network/CPU/storage/energy)
3. Generate comparison table
4. Calculate cumulative impact
5. Recommend implementation order by ROI
6. List relative difficulties and dependencies

---

### `audit_rapide_greenit`

**Input Arguments:**
- `url` (required): Page to audit

**Description:** Quick 5-minute audit using top 10 high-impact recommendations.

**Output:**
1. Page EcoIndex score/grade
2. Top 5 missing recommendations
3. Estimated impact if implemented
4. 1 immediate action to prioritize

---

### `audit_par_ressource`

**Input Arguments:**
- `ressource` (required): Resource type ("network", "cpu", "storage", "energy", "requests")
- `budget` (optional): Time budget in hours. Defaults to 2.

**Description:** Targeted audit optimizing a specific resource within time constraints.

**Output:**
1. All fiches for the resource type
2. Filter by quick implementation (< budget hours)
3. Estimate global savings if all implemented
4. Detail implementation chain
5. Action plan for the resource within time budget

---

## Resources

Static resources accessible via MCP resource protocol.

### `greenit://version`

**Description:** Server and data version information

**Example Response:**
```json
{
  "server_version": "2.3.0",
  "data_version": "2.3.0",
  "data_updated_at": "2026-04-20T10:30:00Z",
  "fiches": 115
}
```

---

### `greenit://index`

**Description:** Lightweight index of all fiches

**Example Response:**
```json
{
  "total": 115,
  "fiches": [
    {
      "id": "RWEB_0051",
      "num": "51",
      "title": "Minify CSS and JavaScript",
      "description": "Reduce file size by removing..."
    }
  ],
  "categories": ["network", "cpu", "3-developement", ...]
}
```

---

### `greenit://fiche/{id}`

**Description:** Complete details of a fiche (equivalent to `obtenir_fiche_complete`)

**Example:** `greenit://fiche/RWEB_0051` returns full fiche object

---

### `greenit://metadata`

**Description:** Reference metadata with statistics

**Example Response:**
```json
{
  "languages": ["fr"],
  "versions": ["2.3.0"],
  "source": "https://github.com/greenit-apps/greenit-data",
  "updated_at": "2026-04-20T10:30:00Z",
  "nb_fiches": 115,
  "nb_lifecycles": 7,
  "nb_ressources": 8,
  "taux_ecoindex_moyen": 58.5
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
| `ADMIN_TOKEN` | empty | Admin token for the token management API (HTTP mode only) |

### Admin Token API

When `MCP_TRANSPORT=http` and `ADMIN_TOKEN` is set, the following routes are available. All require `Authorization: Bearer <ADMIN_TOKEN>`.

#### `GET /admin/tokens`

Lists all tokens.

**Response:**
```json
{
  "tokens": [
    {
      "id": "vpezBq_s",
      "name": "Alice",
      "created_at": 1744000000,
      "expires_at": 1775536000,
      "scopes": ["read"]
    }
  ]
}
```

#### `POST /admin/tokens`

Creates a new token.

**Request body:**
```json
{ "name": "Alice", "expires_days": 365 }
```

**Response:** `201 Created` with the created token object including the raw token value.

#### `GET /admin/tokens/{id}`

Returns a single token by its `client_id`.

**Response:** Token object (same shape as list items).

#### `PATCH /admin/tokens/{id}`

Updates a token's name or expiration.

**Request body (all fields optional):**
```json
{ "name": "Alice (updated)", "expires_days": 90 }
```

**Response:** Updated token object.

#### `DELETE /admin/tokens/{id}`

Revokes a token.

**Response:** `204 No Content`

### Token Management

```bash
# Generate token (expires in 365 days)
docker run --rm -v $(pwd)/tokens:/app/tokens greenit-mcp \
  --generate-token --name "Alice"

# Generate with custom expiration
docker run --rm -v $(pwd)/tokens:/app/tokens greenit-mcp \
  --generate-token --name "Bob" --expires-days 180

# List tokens
docker run --rm -v $(pwd)/tokens:/app/tokens greenit-mcp --list-tokens

# Revoke token
docker run --rm -v $(pwd)/tokens:/app/tokens greenit-mcp \
  --revoke-token <token>
```

### Testing

```bash
cd /Users/renaudheluin/DEV/DEV_GREENIT/refs/mcp-115-greenit
python -m pytest tests/ -v
```

---

## Integration Examples

### Finding Recommendations

```python
# Get all high-impact, quick-to-implement fiches
top = fiches_prioritaires(impact_min=4, priorite_min=4)
for fiche in top['fiches']:
    print(f"{fiche['num']}: {fiche['titre']} ({fiche['score']})")

# Find network optimization strategies
network = lister_fiches(saved_resource="network", lifecycle="3-developement")
for fiche in network['fiches']:
    print(f"  {fiche['titre']}")
```

### EcoIndex Analysis

```python
# Measure and analyze a page
result = calculer_ecoindex(
    dom_nodes=1200,
    requests=45,
    size_kb=2100,
    url="https://example.com"
)

print(f"Score: {result['score']}/100")
print(f"Grade: {result['grade']}")

if result['score'] < 60:
    # Get optimization recommendations
    recs = lister_fiches(impact_min=4)
    print("Top recommendations:")
    for fiche in recs['fiches'][:5]:
        print(f"  - {fiche['titre']}")
```

### Comparing Optimization Strategies

```python
# Compare different approaches
comparison = comparer_fiches(["RWEB_0051", "RWEB_0049", "RWEB_0052"])

print(f"Best approach: {comparison['recommandation']['priorite_1']}")
for fiche_id in comparison['recommandation']['classement']:
    fiche = obtenir_fiche_complete(fiche_id)
    print(f"  {fiche['title']} (impact: {fiche['environmental_impact']}/5)")
```

### Lifecycle-Based Planning

```python
# Get development phase recommendations
dev_phases = lister_lifecycles()
dev = [p for p in dev_phases['lifecycles'] if p['id'] == '3-developement'][0]
print(f"Development phase: {dev['count']} recommendations")

# Get high-impact dev fiches
dev_fiches = lister_fiches(
    lifecycle="3-developement",
    impact_min=3,
    priorite_min=3
)

print("Development priorities:")
for fiche in sorted(dev_fiches['fiches'], key=lambda x: x['environmental_impact'], reverse=True)[:10]:
    print(f"  {fiche['num']}: {fiche['titre']}")
```

---

## Notes

- **EcoIndex Calculation**: Uses official formula from [greenit.fr](https://www.greenit.fr)
- **Resource Coverage**: 8 types of resources; fiches may save multiple types
- **Lifecycle Phases**: 7 phases from specification to retirement; most recommendations are in development
- **Implementation ROI**: Combined score (impact + priority) is good proxy for ROI
- **Data Source**: GitHub repository [greenit-apps/greenit-data](https://github.com/greenit-apps/greenit-data)
