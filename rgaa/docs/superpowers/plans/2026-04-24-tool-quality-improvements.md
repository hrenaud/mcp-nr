# MCP-RGAA Tool Quality Improvements

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add proper MCP annotations and outputSchema definitions to all 10 tools to improve client discoverability, error messaging, and structured response handling.

**Architecture:** Each tool receives four annotations (readOnlyHint, destructiveHint, idempotentHint, openWorldHint) and appropriate outputSchema definitions. Read-only tools are explicitly marked. Analysis and calculation tools receive special care for error handling. Error messages are reviewed and made actionable with specific next steps.

**Tech Stack:** FastMCP (Python), Zod-equivalent schema validation via dict descriptors, MCP Inspector for testing.

---

## File Structure

**Modified Files:**
- `files/rgaa_mcp.py` — Add annotations and outputSchema to all 10 tools, improve error messages
- `tests/test_tools.py` — Add tests for annotation presence and outputSchema validity
- `docs/api_reference.md` — Document annotation and schema definitions (new)

---

## Task 1: Add Annotations and OutputSchema to Data Listing Tools

**Files:**
- Modify: `files/rgaa_mcp.py:73-105` (rgaa_lister_criteres), `files/rgaa_mcp.py:222-246` (rgaa_types_audit)
- Test: `tests/test_tools.py`

These tools list collections of entities. Both are fully read-only, idempotent, and open-world (number of criteria can change).

- [ ] **Step 1: Read current rgaa_lister_criteres tool definition**

Current state: Located at lines 73-105. Has basic description but no annotations. Returns dict with "total" and "criteres" keys.

- [ ] **Step 2: Add annotations and outputSchema to rgaa_lister_criteres**

Replace the `@mcp.tool()` decorator and docstring with:

```python
@mcp.tool()
def rgaa_lister_criteres(theme: Optional[int] = None, niveau_wcag: Optional[Literal["A", "AA", "AAA"]] = None) -> dict:
    """
    Liste les critères RGAA avec filtres optionnels par thème et/ou niveau WCAG.

    Args:
        theme: Numéro de thème (1-13). None = tous les thèmes.
        niveau_wcag: Niveau WCAG à filtrer. None = tous les niveaux.

    Returns:
        {"total": N, "criteres": [{"id": "1.1", "theme": 1, "titre": "...", "automatisable": true, "niveau": "A"}]}
    """
    # ... existing implementation unchanged ...
```

Add to mcp instance after all tools are defined (at end of file, before prompts section):

```python
# Annotations for rgaa_lister_criteres
mcp.set_tool_options(
    "rgaa_lister_criteres",
    readOnlyHint=True,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=True,
)
```

- [ ] **Step 3: Add annotations and outputSchema to rgaa_types_audit**

Same pattern — add annotations after tool definition:

```python
mcp.set_tool_options(
    "rgaa_types_audit",
    readOnlyHint=True,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=False,
)
```

- [ ] **Step 4: Write test for annotation presence**

In `tests/test_tools.py`, add:

```python
def test_listing_tools_have_annotations():
    """Verify that listing tools have proper annotations set."""
    from fastmcp import FastMCP
    # After server init
    assert mcp.get_tool_options("rgaa_lister_criteres").readOnlyHint == True
    assert mcp.get_tool_options("rgaa_types_audit").readOnlyHint == True
```

- [ ] **Step 5: Run test**

```bash
pytest tests/test_tools.py::test_listing_tools_have_annotations -v
```

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add files/rgaa_mcp.py tests/test_tools.py
git commit -m "feat: add annotations to listing tools (rgaa_lister_criteres, rgaa_types_audit)"
```

---

## Task 2: Add Annotations to Detail Retrieval Tools

**Files:**
- Modify: `files/rgaa_mcp.py:107-123` (rgaa_obtenir_critere), `files/rgaa_mcp.py:162-190` (rgaa_glossaire)
- Test: `tests/test_tools.py`

These tools retrieve specific entities by ID. Both are read-only and idempotent.

- [ ] **Step 1: Add annotations to rgaa_obtenir_critere**

```python
mcp.set_tool_options(
    "rgaa_obtenir_critere",
    readOnlyHint=True,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=False,
)
```

- [ ] **Step 2: Improve error message in rgaa_obtenir_critere**

Current error: `{"erreur": f"Critère '{id}' introuvable"}`

Replace with actionable message:

```python
if critere is None:
    return {
        "erreur": f"Critère '{id}' introuvable",
        "conseil": f"Utilisez rgaa_lister_criteres() pour voir les identifiants valides",
        "id_demande": id,
    }
```

- [ ] **Step 3: Add annotations to rgaa_glossaire**

```python
mcp.set_tool_options(
    "rgaa_glossaire",
    readOnlyHint=True,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=False,
)
```

- [ ] **Step 4: Improve error message in rgaa_glossaire**

Current error: `{"erreur": f"Terme '{terme}' introuvable dans le glossaire"}`

Replace with:

```python
return {
    "erreur": f"Terme '{terme}' introuvable dans le glossaire",
    "conseil": "Utilisez rgaa_chercher() pour chercher par mot-clé",
    "terme_demande": terme,
}
```

- [ ] **Step 5: Write test for detail tools**

```python
def test_detail_retrieval_tools_have_annotations():
    """Verify detail retrieval tools are marked read-only."""
    assert mcp.get_tool_options("rgaa_obtenir_critere").readOnlyHint == True
    assert mcp.get_tool_options("rgaa_glossaire").readOnlyHint == True
```

- [ ] **Step 6: Run test**

```bash
pytest tests/test_tools.py::test_detail_retrieval_tools_have_annotations -v
```

Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add files/rgaa_mcp.py tests/test_tools.py
git commit -m "feat: add annotations and improve error messages for detail tools"
```

---

## Task 3: Add Annotations to Search and Reference Tools

**Files:**
- Modify: `files/rgaa_mcp.py:125-160` (rgaa_chercher), `files/rgaa_mcp.py:192-220` (rgaa_statistiques)
- Test: `tests/test_tools.py`

Search and statistics tools are read-only utilities.

- [ ] **Step 1: Add annotations to rgaa_chercher**

```python
mcp.set_tool_options(
    "rgaa_chercher",
    readOnlyHint=True,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=True,
)
```

- [ ] **Step 2: Add annotations to rgaa_statistiques**

```python
mcp.set_tool_options(
    "rgaa_statistiques",
    readOnlyHint=True,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=False,
)
```

- [ ] **Step 3: Write test for search and statistics tools**

```python
def test_search_and_stats_tools_have_annotations():
    """Verify search and statistics tools are marked read-only."""
    assert mcp.get_tool_options("rgaa_chercher").readOnlyHint == True
    assert mcp.get_tool_options("rgaa_statistiques").readOnlyHint == True
```

- [ ] **Step 4: Run test**

```bash
pytest tests/test_tools.py::test_search_and_stats_tools_have_annotations -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add files/rgaa_mcp.py tests/test_tools.py
git commit -m "feat: add annotations to search and statistics tools"
```

---

## Task 4: Add Annotations to Audit Criteria Tool

**Files:**
- Modify: `files/rgaa_mcp.py:248-285` (rgaa_criteres_audit)
- Test: `tests/test_tools.py`

Tool that retrieves filtered criteria set by audit type.

- [ ] **Step 1: Add annotations to rgaa_criteres_audit**

```python
mcp.set_tool_options(
    "rgaa_criteres_audit",
    readOnlyHint=True,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=False,
)
```

- [ ] **Step 2: Improve error message in rgaa_criteres_audit**

Current error: `{"erreur": f"Type '{type}' inconnu. Valeurs acceptées : complet, rapide, complementaire"}`

This is already good, but make it consistent:

```python
if type not in audit_types:
    return {
        "erreur": f"Type '{type}' inconnu",
        "valeurs_acceptees": ["complet", "rapide", "complementaire"],
        "conseil": "Utilisez rgaa_types_audit() pour voir les types disponibles",
        "type_demande": type,
    }
```

- [ ] **Step 3: Write test**

```python
def test_audit_criteria_tool_has_annotations():
    """Verify audit criteria tool is marked read-only."""
    assert mcp.get_tool_options("rgaa_criteres_audit").readOnlyHint == True
```

- [ ] **Step 4: Run test**

```bash
pytest tests/test_tools.py::test_audit_criteria_tool_has_annotations -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add files/rgaa_mcp.py tests/test_tools.py
git commit -m "feat: add annotations and improve error handling for rgaa_criteres_audit"
```

---

## Task 5: Add Annotations to Analysis Tool

**Files:**
- Modify: `files/rgaa_mcp.py:291-310` (rgaa_analyser)
- Test: `tests/test_tools.py`

The analyzer is special: it's read-only (no side effects) but performs HTTP requests. Mark appropriately.

- [ ] **Step 1: Add annotations to rgaa_analyser**

```python
mcp.set_tool_options(
    "rgaa_analyser",
    readOnlyHint=True,
    destructiveHint=False,
    idempotentHint=False,  # Not idempotent: page content may change
    openWorldHint=True,     # Open world: any URL possible
)
```

- [ ] **Step 2: Add error handling for network failures**

At the start of rgaa_analyser, wrap the fetcher call:

```python
try:
    html = fetcher_html(url)
    result = analyser_html(html, themes)
except Exception as e:
    return {
        "erreur": f"Analyse impossible pour {url}",
        "raison": str(e),
        "conseil": "Vérifiez que l'URL est accessible et valide",
        "url": url,
    }
```

- [ ] **Step 3: Write test**

```python
def test_analyser_tool_has_correct_annotations():
    """Verify analyzer tool has correct annotations for network operations."""
    opts = mcp.get_tool_options("rgaa_analyser")
    assert opts.readOnlyHint == True
    assert opts.destructiveHint == False
    assert opts.idempotentHint == False
    assert opts.openWorldHint == True
```

- [ ] **Step 4: Run test**

```bash
pytest tests/test_tools.py::test_analyser_tool_has_correct_annotations -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add files/rgaa_mcp.py tests/test_tools.py
git commit -m "feat: add annotations and error handling to rgaa_analyser"
```

---

## Task 6: Add Annotations to Checklist Tool

**Files:**
- Modify: `files/rgaa_mcp.py:333-386` (rgaa_checklist)
- Test: `tests/test_tools.py`

Checklist generator is read-only, idempotent, and open-world (any combination of themes/criteria).

- [ ] **Step 1: Add annotations to rgaa_checklist**

```python
mcp.set_tool_options(
    "rgaa_checklist",
    readOnlyHint=True,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=True,
)
```

- [ ] **Step 2: Improve error message in rgaa_checklist**

Current error: `{"erreur": "Au moins un paramètre requis : themes ou criteres"}`

Replace with:

```python
if not themes and not criteres:
    return {
        "erreur": "Au moins un paramètre requis",
        "conseil": "Passez 'themes' (liste d'entiers 1-13) ou 'criteres' (liste de chaînes '1.1', '6.1', etc.)",
        "exemple_themes": [1, 6, 11],
        "exemple_criteres": ["1.1", "6.1"],
    }
```

- [ ] **Step 3: Write test**

```python
def test_checklist_tool_has_annotations():
    """Verify checklist tool is marked read-only and open-world."""
    opts = mcp.get_tool_options("rgaa_checklist")
    assert opts.readOnlyHint == True
    assert opts.openWorldHint == True
```

- [ ] **Step 4: Run test**

```bash
pytest tests/test_tools.py::test_checklist_tool_has_annotations -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add files/rgaa_mcp.py tests/test_tools.py
git commit -m "feat: add annotations and improve error message for rgaa_checklist"
```

---

## Task 7: Add Annotations to Conformity Calculation Tool

**Files:**
- Modify: `files/rgaa_mcp.py:392-424` (rgaa_taux_conformite)
- Test: `tests/test_tools.py`

The conformity calculator is a pure calculation tool: read-only, no network, idempotent, closed-world (known status values).

- [ ] **Step 1: Add annotations to rgaa_taux_conformite**

```python
mcp.set_tool_options(
    "rgaa_taux_conformite",
    readOnlyHint=True,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=False,
)
```

- [ ] **Step 2: Improve error message for invalid status**

Current error: `{"erreur": f"Statut invalide pour '{cid}' : '{statut}'. Valeurs acceptées : C, NC, NA"}`

Replace with:

```python
return {
    "erreur": f"Statut invalide pour le critère '{cid}'",
    "valeur_reçue": statut,
    "valeurs_acceptees": ["C", "NC", "NA"],
    "definition": {
        "C": "Conforme",
        "NC": "Non-Conforme",
        "NA": "Non-Applicable"
    },
    "critere": cid,
}
```

- [ ] **Step 3: Write test**

```python
def test_conformity_tool_has_annotations():
    """Verify conformity calculator has correct annotations."""
    opts = mcp.get_tool_options("rgaa_taux_conformite")
    assert opts.readOnlyHint == True
    assert opts.idempotentHint == True
    assert opts.openWorldHint == False
```

- [ ] **Step 4: Run test**

```bash
pytest tests/test_tools.py::test_conformity_tool_has_annotations -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add files/rgaa_mcp.py tests/test_tools.py
git commit -m "feat: add annotations and improve error messaging for rgaa_taux_conformite"
```

---

## Task 8: Verify All Annotations and Run Integration Tests

**Files:**
- Test: `tests/test_tools.py`

Verify that all 10 tools have proper annotations set and the server starts correctly.

- [ ] **Step 1: Write comprehensive annotation test**

```python
def test_all_tools_have_required_annotations():
    """Verify all 10 tools have proper annotations."""
    tools = [
        "rgaa_lister_criteres",
        "rgaa_obtenir_critere",
        "rgaa_chercher",
        "rgaa_glossaire",
        "rgaa_statistiques",
        "rgaa_types_audit",
        "rgaa_criteres_audit",
        "rgaa_analyser",
        "rgaa_checklist",
        "rgaa_taux_conformite",
    ]
    
    for tool_name in tools:
        opts = mcp.get_tool_options(tool_name)
        assert opts is not None, f"Tool {tool_name} has no annotations"
        assert opts.readOnlyHint in [True, False], f"Tool {tool_name} missing readOnlyHint"
        assert opts.destructiveHint in [True, False], f"Tool {tool_name} missing destructiveHint"
        assert opts.idempotentHint in [True, False], f"Tool {tool_name} missing idempotentHint"
        assert opts.openWorldHint in [True, False], f"Tool {tool_name} missing openWorldHint"
```

- [ ] **Step 2: Write server startup test**

```python
def test_mcp_server_starts_with_annotations():
    """Verify server initializes successfully with all annotations."""
    from rgaa_mcp import mcp
    assert mcp is not None
    # Verify server has all 10 tools registered
    tool_count = len([t for t in mcp._tools.values()])
    assert tool_count >= 10, f"Expected at least 10 tools, found {tool_count}"
```

- [ ] **Step 3: Run all annotation tests**

```bash
pytest tests/test_tools.py -k "annotation" -v
```

Expected: All tests PASS

- [ ] **Step 4: Run full test suite**

```bash
pytest tests/ -v
```

Expected: All existing tests PASS, new annotation tests PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_tools.py
git commit -m "test: add comprehensive annotation verification tests for all 10 tools"
```

---

## Task 9: Test with MCP Inspector

**Files:**
- No code changes; manual testing step

Verify that all tools are discoverable and work correctly with MCP Inspector.

- [ ] **Step 1: Start MCP Inspector**

```bash
npx @modelcontextprotocol/inspector python files/rgaa_mcp.py
```

- [ ] **Step 2: Verify all 10 tools appear**

Check the Tools list in the inspector. Verify all tool names are present.

- [ ] **Step 3: Verify annotations display**

For each tool, check that annotations appear in the inspector UI:
- readOnlyHint should be visible
- destructiveHint should show False for all tools
- idempotentHint varies by tool
- openWorldHint varies by tool

- [ ] **Step 4: Test error messages**

Call `rgaa_obtenir_critere` with invalid ID like "999.999" and verify the error response includes actionable advice.

- [ ] **Step 5: Test analyzer error handling**

Call `rgaa_analyser` with an invalid URL like "not-a-url" and verify error response with helpful message.

- [ ] **Step 6: Take screenshot or note results**

Document that MCP Inspector shows all annotations and error messages correctly.

- [ ] **Step 7: No commit needed for this task**

This is manual verification.

---

## Task 10: Document API Changes and Create User Guide

**Files:**
- Create: `docs/api_reference.md`
- Modify: `README.md`

Document the new annotations and improved error messages.

- [ ] **Step 1: Create api_reference.md**

```markdown
# RGAA MCP API Reference

## Tool Annotations

All tools in the RGAA MCP have standard annotations for client discoverability:

### Read-Only Tools
All tools are marked with `readOnlyHint: true` — they do not modify server state.

### Destructive Operations
No tools are destructive (`destructiveHint: false` for all).

### Idempotency

| Tool | Idempotent | Notes |
|------|-----------|-------|
| rgaa_lister_criteres | Yes | Deterministic result set |
| rgaa_obtenir_critere | Yes | Same criteria always return same data |
| rgaa_chercher | Yes | Search is consistent |
| rgaa_glossaire | Yes | Glossary is static |
| rgaa_statistiques | Yes | Stats are deterministic |
| rgaa_types_audit | Yes | Audit types are fixed |
| rgaa_criteres_audit | Yes | Fixed mapping |
| rgaa_analyser | No | Page content may change |
| rgaa_checklist | Yes | Consistent templates |
| rgaa_taux_conformite | Yes | Pure calculation |

### Open World

| Tool | Open World | Notes |
|------|-----------|-------|
| rgaa_lister_criteres | Yes | Criteria set can grow |
| rgaa_obtenir_critere | No | Closed set of criteria |
| rgaa_chercher | Yes | Search matches flexible |
| rgaa_glossaire | No | Glossary is fixed |
| rgaa_statistiques | No | Stats are deterministic |
| rgaa_types_audit | No | Types are fixed |
| rgaa_criteres_audit | No | Mappings are fixed |
| rgaa_analyser | Yes | Any URL possible |
| rgaa_checklist | Yes | Flexible combinations |
| rgaa_taux_conformite | No | Calculation is closed |

## Error Handling

All tools now return actionable error messages with guidance on next steps:

- **Detail tools** suggest using list tools when an ID is not found
- **Analyzer** provides helpful context on network failures
- **Checklist** explains required parameters with examples
- **Conformity** defines valid status values inline
```

- [ ] **Step 2: Update README**

Add a section to README.md:

```markdown
## Tool Annotations

All RGAA MCP tools include proper MCP annotations (readOnlyHint, destructiveHint, idempotentHint, openWorldHint) for client discoverability. See [API Reference](docs/api_reference.md) for details.

Error messages provide actionable guidance with examples and suggestions for next steps.
```

- [ ] **Step 3: Run test to verify README exists**

```bash
test -f README.md && echo "README exists"
```

Expected: README exists

- [ ] **Step 4: Commit**

```bash
git add docs/api_reference.md README.md
git commit -m "docs: add API reference with annotation and error handling guide"
```

---

## Task 11: Final Verification and Quality Check

**Files:**
- Code review of all changes

Ensure all changes are consistent and complete.

- [ ] **Step 1: Run git log to see all commits**

```bash
git log --oneline -11
```

Expected: See 11 commits from Tasks 1-10, ending with "feat: add annotations to listing tools"

- [ ] **Step 2: Run full test suite one final time**

```bash
pytest tests/ -v --tb=short
```

Expected: All tests PASS (including new annotation tests)

- [ ] **Step 3: Verify all tool annotations in code**

```bash
grep -n "mcp.set_tool_options" files/rgaa_mcp.py | wc -l
```

Expected: 10 lines (one for each tool)

- [ ] **Step 4: Check for error response consistency**

```bash
grep -n '"erreur":' files/rgaa_mcp.py
```

Expected: Each error now includes "conseil" or "valeurs_acceptees" or similar guidance field

- [ ] **Step 5: Verify no placeholders remain**

```bash
grep -i "TODO\|TBD\|FIXME\|XXX" files/rgaa_mcp.py
```

Expected: No matches (or only pre-existing ones from previous work)

- [ ] **Step 6: Final commit message summary**

```bash
git log --oneline | head -11
```

Expected: Clear progression from basic annotation addition through error message improvements to documentation

- [ ] **Step 7: No additional commit; verification only**

This task is a quality gate check.

