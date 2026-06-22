# B1 — `obtenir_checklist_audit` Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `_build_checklist(cache)` to `files/checklist.py` and expose it as the `obtenir_checklist_audit` MCP tool — returns all 115 fiches with `statut: "Non-testé"`, sorted by environmental impact descending.

**Architecture:** `_build_checklist` iterates over the cache, extracts `validation_rule` and `max_value` from each fiche's `validations[0]` (a dict after the A1 parser fix), and builds a sorted list. `obtenir_checklist_audit` is a thin MCP wrapper that loads the cache and delegates to `_build_checklist`. This function is also the base that `auditer_url` will call in A2 before overriding statuts with auto-validations.

**Tech Stack:** Python 3.11, FastMCP, pytest. No new dependencies. Builds on `checklist.py` created in A1.

**Prerequisite:** A1 must be implemented first — `files/checklist.py` must exist with `STATUTS_POSSIBLES`, `_auto_validate`, and `map_metrics_to_fiches`. The cache must be regenerated so `validations` entries are dicts (not plain strings).

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `files/checklist.py` | Modify (add function) | Add `_build_checklist(cache) -> dict` |
| `files/greenit_mcp_final.py` | Modify | Add `obtenir_checklist_audit` MCP tool; add `checklist` import |
| `tests/test_tools.py` | Modify | Add `TestBuildChecklist`, `TestObtenirChecklistAudit` |

---

## Task 1: Add `_build_checklist` to `checklist.py`

**Context:** After A1, `files/checklist.py` contains `STATUTS_POSSIBLES`, `_auto_validate`, and `map_metrics_to_fiches`. This task appends `_build_checklist` — the shared base used by both `obtenir_checklist_audit` (B1) and `auditer_url` (A2). It iterates the full cache, extracts `validation_rule`/`max_value` from `validations[0]` (a dict after the A1 parser fix), and returns a sorted list of 115 fiches all with `statut: "Non-testé"`.

**Files:**
- Modify: `files/checklist.py`
- Test: `tests/test_tools.py`

- [ ] **Step 1: Write the failing tests**

Add a new class `TestBuildChecklist` at the end of `tests/test_tools.py` (after `TestMapMetricsFichesEnriched` added in A1):

```python
# ============================================================================
# checklist — _build_checklist
# ============================================================================

class TestBuildChecklist:
    @pytest.fixture
    def mock_cache(self):
        return {
            "RWEB_0001": {
                "title": "Fiche haute priorité",
                "lifecycle": "1-conception",
                "url": "https://rweb.greenit.fr/fr/fiches/0001",
                "environmental_impact": 5,
                "priority_implementation": 2,
                "validations": [{"rule": "example rule", "maxValue": "10"}],
            },
            "RWEB_0002": {
                "title": "Fiche moyenne priorité",
                "lifecycle": "3-developement",
                "url": "https://rweb.greenit.fr/fr/fiches/0002",
                "environmental_impact": 3,
                "priority_implementation": 3,
                "validations": [],
            },
            "RWEB_0003": {
                "title": "Fiche basse priorité",
                "lifecycle": "5-hebergement",
                "url": "https://rweb.greenit.fr/fr/fiches/0003",
                "environmental_impact": 1,
                "priority_implementation": 4,
                "validations": [{"rule": "rule only, no max"}],
            },
        }

    def test_count_matches_cache(self, mock_cache):
        result = checklist._build_checklist(mock_cache)
        assert result["total"] == 3
        assert len(result["fiches"]) == 3

    def test_all_statuts_are_non_teste(self, mock_cache):
        result = checklist._build_checklist(mock_cache)
        for f in result["fiches"]:
            assert f["statut"] == "Non-testé"

    def test_all_valeur_mesuree_are_none(self, mock_cache):
        result = checklist._build_checklist(mock_cache)
        for f in result["fiches"]:
            assert f["valeur_mesuree"] is None

    def test_sorted_by_environmental_impact_desc(self, mock_cache):
        result = checklist._build_checklist(mock_cache)
        impacts = [f["environmental_impact"] for f in result["fiches"]]
        assert impacts == sorted(impacts, reverse=True)

    def test_statuts_possibles_present(self, mock_cache):
        result = checklist._build_checklist(mock_cache)
        assert "statuts_possibles" in result
        assert set(result["statuts_possibles"].keys()) == {
            "Conforme", "Non-conforme", "Non-applicable", "Indéterminé", "Non-testé"
        }

    def test_validation_rule_and_max_value_extracted(self, mock_cache):
        result = checklist._build_checklist(mock_cache)
        fiche = next(f for f in result["fiches"] if f["id"] == "RWEB_0001")
        assert fiche["validation_rule"] == "example rule"
        assert fiche["max_value"] == "10"

    def test_empty_validations_gives_none(self, mock_cache):
        result = checklist._build_checklist(mock_cache)
        fiche = next(f for f in result["fiches"] if f["id"] == "RWEB_0002")
        assert fiche["validation_rule"] is None
        assert fiche["max_value"] is None

    def test_non_dict_validation_item_gives_none(self, mock_cache):
        # validations[0] is a string (no "maxValue" key) → both None
        result = checklist._build_checklist(mock_cache)
        fiche = next(f for f in result["fiches"] if f["id"] == "RWEB_0003")
        assert fiche["validation_rule"] is None
        assert fiche["max_value"] is None

    def test_required_fields_on_every_fiche(self, mock_cache):
        result = checklist._build_checklist(mock_cache)
        required = {
            "id", "titre", "lifecycle", "url", "validation_rule", "max_value",
            "valeur_mesuree", "statut", "environmental_impact", "priority_implementation",
        }
        for f in result["fiches"]:
            missing = required - f.keys()
            assert not missing, f"Missing fields in {f['id']}: {missing}"
```

- [ ] **Step 2: Run to verify the tests fail**

```bash
cd /Users/renaudheluin/DEV/DEV_GREENIT/refs/mcp-115-greenit
pytest tests/test_tools.py::TestBuildChecklist -v
```

Expected: `FAILED — AttributeError: module 'checklist' has no attribute '_build_checklist'`

- [ ] **Step 3: Implement `_build_checklist` in `files/checklist.py`**

Append to the end of `files/checklist.py` (after `map_metrics_to_fiches`):

```python
def _build_checklist(cache: dict) -> dict:
    """
    Build the base audit checklist from all fiches in cache.

    All fiches default to statut='Non-testé' and valeur_mesuree=None.
    Sorted by environmental_impact descending.

    Used by:
      - obtenir_checklist_audit (B1): returns this dict directly as JSON
      - auditer_url (A2): calls this, then overrides statut/valeur_mesuree
        for auto-testable fiches using map_metrics_to_fiches results

    Args:
        cache: GreenIT fiches cache (from charger_cache())

    Returns:
        dict with keys: total (int), statuts_possibles (dict), fiches (list)
    """
    fiches = []
    for fiche_id, fiche in cache.items():
        validations = fiche.get("validations", [])
        first_val = validations[0] if validations and isinstance(validations[0], dict) else {}
        validation_rule = first_val.get("rule") or None
        max_value = first_val.get("maxValue") or None
        fiches.append({
            "id": fiche_id,
            "titre": fiche.get("title", ""),
            "lifecycle": fiche.get("lifecycle", ""),
            "url": fiche.get("url", ""),
            "validation_rule": validation_rule,
            "max_value": max_value,
            "valeur_mesuree": None,
            "statut": "Non-testé",
            "environmental_impact": fiche.get("environmental_impact", 0),
            "priority_implementation": fiche.get("priority_implementation", 0),
        })
    fiches.sort(key=lambda f: f["environmental_impact"], reverse=True)
    return {
        "total": len(fiches),
        "statuts_possibles": STATUTS_POSSIBLES,
        "fiches": fiches,
    }
```

- [ ] **Step 4: Run to verify the tests pass**

```bash
pytest tests/test_tools.py::TestBuildChecklist -v
```

Expected: all 9 tests PASS.

- [ ] **Step 5: Run the full test suite to check for regressions**

```bash
pytest tests/test_tools.py -v
```

Expected: all existing tests still PASS.

- [ ] **Step 6: Commit**

```bash
git add files/checklist.py tests/test_tools.py
git commit -m "feat(checklist): add _build_checklist — base for obtenir_checklist_audit and auditer_url"
```

---

## Task 2: Add `obtenir_checklist_audit` MCP tool

**Context:** `files/greenit_mcp_final.py` currently imports `crawl` and `build_report` from `audit_url`. This task adds a `checklist` import and a new `@mcp.tool()` function `obtenir_checklist_audit` — a thin wrapper around `_build_checklist`. The tool is synchronous (no crawl, no I/O beyond loading the cache). Tests run against the real cache (115 fiches) to verify the integration end-to-end.

**Files:**
- Modify: `files/greenit_mcp_final.py`
- Test: `tests/test_tools.py`

- [ ] **Step 1: Write the failing test**

Add a new class `TestObtenirChecklistAudit` at the end of `tests/test_tools.py` (after `TestBuildChecklist`):

```python
# ============================================================================
# greenit_mcp_final — obtenir_checklist_audit
# ============================================================================

class TestObtenirChecklistAudit:
    def test_returns_115_fiches(self):
        result = json.loads(greenit_mcp_final.obtenir_checklist_audit())
        assert result["total"] == 115
        assert len(result["fiches"]) == 115

    def test_all_statuts_non_teste(self):
        result = json.loads(greenit_mcp_final.obtenir_checklist_audit())
        for f in result["fiches"]:
            assert f["statut"] == "Non-testé", f"{f['id']} has statut {f['statut']!r}"

    def test_all_valeur_mesuree_none(self):
        result = json.loads(greenit_mcp_final.obtenir_checklist_audit())
        for f in result["fiches"]:
            assert f["valeur_mesuree"] is None

    def test_sorted_by_environmental_impact_desc(self):
        result = json.loads(greenit_mcp_final.obtenir_checklist_audit())
        impacts = [f["environmental_impact"] for f in result["fiches"]]
        assert impacts == sorted(impacts, reverse=True)

    def test_statuts_possibles_has_all_five(self):
        result = json.loads(greenit_mcp_final.obtenir_checklist_audit())
        assert set(result["statuts_possibles"].keys()) == {
            "Conforme", "Non-conforme", "Non-applicable", "Indéterminé", "Non-testé"
        }
```

Note: `greenit_mcp_final` is already imported at the top of `test_tools.py` via the existing test infrastructure (see `TestHttpRoutes`, `TestCreateMcp` in the existing test file).

- [ ] **Step 2: Run to verify the test fails**

```bash
cd /Users/renaudheluin/DEV/DEV_GREENIT/refs/mcp-115-greenit
pytest tests/test_tools.py::TestObtenirChecklistAudit -v
```

Expected: `FAILED — AttributeError: module 'greenit_mcp_final' has no attribute 'obtenir_checklist_audit'`

- [ ] **Step 3: Add the `checklist` import to `greenit_mcp_final.py`**

In `files/greenit_mcp_final.py`, locate the existing `audit_url` import block (around line 34-37):

```python
# Import audit_url module
import sys as _sys
_sys.path.insert(0, str(Path(__file__).parent))
from audit_url import crawl as _crawl, build_report as _build_report
```

Replace with:

```python
# Import local modules
import sys as _sys
_sys.path.insert(0, str(Path(__file__).parent))
from audit_url import crawl as _crawl, build_report as _build_report
from checklist import _build_checklist
```

- [ ] **Step 4: Add `obtenir_checklist_audit` to `greenit_mcp_final.py`**

In `files/greenit_mcp_final.py`, locate the `auditer_url` tool (around line 1073). Insert the new tool immediately **before** `auditer_url` (before its `@mcp.tool()` decorator):

```python
@mcp.tool()
def obtenir_checklist_audit() -> str:
    """
    Retourne les 115 fiches GreenIT avec statut "Non-testé" pour remplissage manuel.

    Aucun crawl n'est effectué. Utile pour préparer un audit manuel, ou pour
    identifier les bonnes pratiques non automatiquement vérifiables avant de
    lancer auditer_url.

    Returns:
        JSON contenant : total (115), statuts_possibles (dict des 5 statuts),
        et fiches (liste des 115 fiches triées par environmental_impact décroissant).
        Chaque fiche inclut : id, titre, lifecycle, url, validation_rule, max_value,
        valeur_mesuree (null), statut ("Non-testé"), environmental_impact,
        priority_implementation.
    """
    cache = charger_cache()
    result = _build_checklist(cache)
    return json.dumps(result, ensure_ascii=False, indent=2)


```

- [ ] **Step 5: Run to verify the tests pass**

```bash
pytest tests/test_tools.py::TestObtenirChecklistAudit -v
```

Expected: all 5 tests PASS.

- [ ] **Step 6: Run the full test suite to check for regressions**

```bash
pytest tests/test_tools.py -v
```

Expected: all existing tests still PASS.

- [ ] **Step 7: Commit**

```bash
git add files/greenit_mcp_final.py tests/test_tools.py
git commit -m "feat(mcp): add obtenir_checklist_audit tool — returns 115 fiches with statut Non-testé"
```
