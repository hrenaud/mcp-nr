# MCP Tool Annotations — RGAA Server API

> **Version:** 1.4.0
> **Updated:** 2026-04-24
> **Target Clients:** Claude Code, MCP Inspector, all MCP-compliant clients

## Overview

All 10 RGAA MCP tools now include comprehensive MCP annotations that communicate tool characteristics to clients. Annotations help clients understand safety, idempotence, and input scope of each tool.

---

## Annotation Types

### readOnlyHint

**What it means:** Tool doesn't modify state or data in the server.

- ✅ `true` — Tool is read-only (safe for non-destructive operations)
- ❌ `false` — Tool modifies state (requires caution)

**Use case:** Clients can safely call read-only tools without transaction management.

**RGAA Tools:** ALL 10 tools are read-only (`true`)

---

### destructiveHint

**What it means:** Tool permanently deletes, removes, or destroys data.

- ❌ `true` — Tool is destructive (requires user confirmation)
- ✅ `false` — Tool is non-destructive (safe to use)

**Use case:** Clients requiring user confirmation before destructive operations can check this hint.

**RGAA Tools:** ALL 10 tools are non-destructive (`false`)

---

### idempotentHint

**What it means:** Calling a tool multiple times with identical inputs produces identical results.

- ✅ `true` — Tool is idempotent (safe to retry)
- ❌ `false` — Tool is non-idempotent (results may differ on retry)

**Use case:** Clients implementing retry logic can safely retry idempotent tools on network errors.

**RGAA Tools:**
- ✅ **9 tools are idempotent** (true):
  - rgaa_lister_criteres
  - rgaa_obtenir_critere
  - rgaa_chercher
  - rgaa_glossaire
  - rgaa_statistiques
  - rgaa_types_audit
  - rgaa_criteres_audit
  - rgaa_checklist
  - rgaa_taux_conformite

- ❌ **1 tool is non-idempotent** (false):
  - rgaa_analyser (depends on external URL content, which may change)

---

### openWorldHint

**What it means:** Tool accepts any input values or only a fixed/known set.

- ✅ `true` — Tool accepts any input (open-world scope)
- ✅ `false` — Tool expects specific values (closed-world, fixed set)

**Use case:** Clients can determine if pre-validation is needed or if user input can be passed through directly.

**RGAA Tools:**

- ✅ **3 tools accept any input** (true):
  - **rgaa_chercher** — Accepts any search keyword/phrase
  - **rgaa_checklist** — Accepts any combination of themes (1-13) and criteria IDs
  - **rgaa_analyser** — Accepts any HTTP/HTTPS URL

- ✅ **7 tools expect fixed values** (false):
  - **rgaa_lister_criteres** — Fixed themes (1-13), fixed saved resources
  - **rgaa_obtenir_critere** — Fixed set of 106 criterion IDs
  - **rgaa_glossaire** — Fixed glossary terms
  - **rgaa_statistiques** — No input parameters (returns fixed statistics)
  - **rgaa_types_audit** — No input parameters (returns fixed audit types)
  - **rgaa_criteres_audit** — Fixed audit types: [complet, rapide, complementaire]
  - **rgaa_taux_conformite** — Fixed statuses: [C, NC, NA]

---

## Quick Reference Table

| Tool | readOnly | destructive | idempotent | openWorld | Type |
|------|----------|-------------|-----------|-----------|------|
| rgaa_lister_criteres | ✅ | ✅ | ✅ | ❌ | Data Listing |
| rgaa_obtenir_critere | ✅ | ✅ | ✅ | ❌ | Detail Retrieval |
| rgaa_chercher | ✅ | ✅ | ✅ | ✅ | Search |
| rgaa_glossaire | ✅ | ✅ | ✅ | ❌ | Reference |
| rgaa_statistiques | ✅ | ✅ | ✅ | ❌ | Reference |
| rgaa_types_audit | ✅ | ✅ | ✅ | ❌ | Reference |
| rgaa_criteres_audit | ✅ | ✅ | ✅ | ❌ | Data Listing |
| rgaa_analyser | ✅ | ✅ | ❌ | ✅ | Analysis |
| rgaa_checklist | ✅ | ✅ | ✅ | ✅ | Generation |
| rgaa_taux_conformite | ✅ | ✅ | ✅ | ❌ | Calculation |

---

## Tool Groupings

### Data Reference Tools (Fixed Data)
Static RGAA reference data — all read-only, non-destructive, idempotent, closed-world:
- rgaa_lister_criteres
- rgaa_glossaire
- rgaa_statistiques
- rgaa_types_audit

### Data Retrieval Tools (Specific Lookups)
Retrieve specific items from fixed sets:
- rgaa_obtenir_critere (lookup by criterion ID)
- rgaa_criteres_audit (lookup by audit type)

### Search/Generation Tools (Flexible Input)
Accept flexible user input for search or generation:
- rgaa_chercher (any search term)
- rgaa_checklist (any theme/criteria combination)

### Analysis Tool (External Dependencies)
Analyzes external content, non-idempotent due to external dependencies:
- rgaa_analyser (URL content may change)

### Computation Tool (Specific Input Format)
Performs calculation on structured input:
- rgaa_taux_conformite (C/NC/NA statuses)

---

## Client Implementation Guide

### For MCP Clients (Claude Code, Copilot, etc.)

**Check tool safety before using:**
```javascript
const tool = mcp.tools.find(t => t.name === "rgaa_analyser");
if (tool.annotations.readOnlyHint && !tool.annotations.destructiveHint) {
  // Safe to use without transaction management
}
```

**Determine if input requires validation:**
```javascript
if (!tool.annotations.openWorldHint) {
  // Fixed input set — validate before calling
  validateCriteriaID(input);
} else {
  // Open-world — can pass through user input directly
}
```

**Implement retry logic for idempotent tools:**
```javascript
if (tool.annotations.idempotentHint) {
  // Safe to retry on network error
  return retry(() => callTool(tool, input), { maxAttempts: 3 });
}
```

---

## Migration Guide (v1.3 → v1.4)

### What Changed?

- **New:** All 10 tools now include MCP annotations
- **New:** Error messages improved with structured responses
- **Unchanged:** Tool parameters, return format, behavior

### Do I Need to Update?

- ✅ No breaking changes
- ✅ Existing code continues to work unchanged
- ✅ Annotations are additional metadata (optional)
- ✅ Updated error messages are backward compatible (still valid JSON)

### How to Adopt?

Use annotations to improve error handling and retry logic:

```python
# Before (v1.3)
try:
    result = client.call_tool("rgaa_analyser", {"url": user_url})
except ManagedError as e:
    # Retry might not be safe — don't know if tool is idempotent
    pass

# After (v1.4)
tool = client.get_tool("rgaa_analyser")
try:
    result = client.call_tool("rgaa_analyser", {"url": user_url})
except ManagedError as e:
    if tool.annotations.idempotentHint:
        # Safe to retry
        result = client.call_tool("rgaa_analyser", {"url": user_url})
```

---

## Support

For questions about annotations, MCP protocol support, or tool behavior, contact the rgaa-mcp maintainers.
