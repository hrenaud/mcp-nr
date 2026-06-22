# C1 — `lister_lifecycles` & `lister_ressources` Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add two MCP tools — `lister_lifecycles` (7 lifecycle phases, ordered by numeric prefix) and `lister_ressources` (8 resource types, sorted by count descending) — to `files/greenit_mcp_final.py`.

**Architecture:** Both tools are thin read-only wrappers: labels are hardcoded dicts derived from `i18n/ui.ts`, counts are computed at call time from the live cache. No new files needed. `lister_fiches` already supports `saved_resource` filtering, so no change required there.

**Tech Stack:** Python 3.11, FastMCP, pytest. No new dependencies.

**Prerequisite:** None — this is independent of A1/A2/B1 and can be implemented at any point.

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `files/greenit_mcp_final.py` | Modify (add 2 tools) | `lister_lifecycles`, `lister_ressources` |
| `tests/test_tools.py` | Modify (add 2 test classes) | `TestListerLifecycles`, `TestListerRessources` |

---

## Task 1: Add `lister_lifecycles` MCP tool

**Context:** The cache contains a `lifecycle` field on each fiche with values like `"3-developement"`. This tool returns 7 entries with hardcoded labels (from `i18n/ui.ts`) and live counts. Ordered by numeric prefix (the integer before the dash).

**Files:**
- Modify: `files/greenit_mcp_final.py`
- Test: `tests/test_tools.py`

- [ ] **Step 1: Write the failing tests**

Add `TestListerLifecycles` at the end of `tests/test_tools.py` (after the existing test classes):

```python
# ============================================================================
# greenit_mcp_final — lister_lifecycles
# ============================================================================

class TestListerLifecycles:
    def test_returns_seven_entries(self):
        result = json.loads(greenit_mcp_final.lister_lifecycles())
        assert len(result) == 7

    def test_ordered_by_numeric_prefix(self):
        result = json.loads(greenit_mcp_final.lister_lifecycles())
        ids = [entry["id"] for entry in result]
        assert ids == sorted(ids, key=lambda x: int(x.split("-")[0]))

    def test_labels_match_i18n(self):
        result = json.loads(greenit_mcp_final.lister_lifecycles())
        expected_labels = {
            "1-specification": "Spécification",
            "2-concept": "Conception",
            "3-developement": "Développement",
            "4-production": "Production",
            "5-utilization": "Utilisation",
            "6-support": "Support",
            "7-retirement": "Fin de vie",
        }
        for entry in result:
            assert entry["label"] == expected_labels[entry["id"]], (
                f"{entry['id']}: expected {expected_labels[entry['id']]!r}, got {entry['label']!r}"
            )

    def test_counts_are_positive_integers(self):
        result = json.loads(greenit_mcp_final.lister_lifecycles())
        for entry in result:
            assert isinstance(entry["count"], int)
            assert entry["count"] >= 0

    def test_total_count_equals_cache_size(self):
        result = json.loads(greenit_mcp_final.lister_lifecycles())
        total = sum(entry["count"] for entry in result)
        # All 115 fiches have a lifecycle — total must equal cache size
        assert total == 115

    def test_ids_are_valid_lister_fiches_filters(self):
        result = json.loads(greenit_mcp_final.lister_lifecycles())
        for entry in result:
            fiches = greenit_mcp_final.lister_fiches(lifecycle=entry["id"])
            assert len(fiches) == entry["count"], (
                f"lister_fiches(lifecycle={entry['id']!r}) returned {len(fiches)}, "
                f"but lister_lifecycles says count={entry['count']}"
            )

    def test_required_fields_on_every_entry(self):
        result = json.loads(greenit_mcp_final.lister_lifecycles())
        for entry in result:
            assert "id" in entry
            assert "label" in entry
            assert "count" in entry
```

- [ ] **Step 2: Run to verify the tests fail**

```bash
cd /Users/renaudheluin/DEV/DEV_GREENIT/refs/mcp-115-greenit
pytest tests/test_tools.py::TestListerLifecycles -v
```

Expected: `FAILED — AttributeError: module 'greenit_mcp_final' has no attribute 'lister_lifecycles'`

- [ ] **Step 3: Implement `lister_lifecycles` in `greenit_mcp_final.py`**

In `files/greenit_mcp_final.py`, locate `obtenir_checklist_audit` or `auditer_url` (whichever comes first around line 1073). Insert the new tool **before** it:

```python
_LIFECYCLE_LABELS = {
    "1-specification": "Spécification",
    "2-concept": "Conception",
    "3-developement": "Développement",
    "4-production": "Production",
    "5-utilization": "Utilisation",
    "6-support": "Support",
    "7-retirement": "Fin de vie",
}


@mcp.tool()
def lister_lifecycles() -> str:
    """
    Liste les 7 phases du cycle de vie du référentiel GreenIT.

    Les ids retournés sont directement utilisables comme valeur du filtre
    `lifecycle` dans `lister_fiches`.

    Returns:
        JSON : liste de 7 entrées {id, label, count}, ordonnées par préfixe numérique.
    """
    cache = charger_cache()
    counts: dict[str, int] = {lc: 0 for lc in _LIFECYCLE_LABELS}
    for fiche in cache.values():
        lc = fiche.get("lifecycle")
        if lc in counts:
            counts[lc] += 1
    result = [
        {"id": lc, "label": label, "count": counts[lc]}
        for lc, label in _LIFECYCLE_LABELS.items()
    ]
    result.sort(key=lambda e: int(e["id"].split("-")[0]))
    return json.dumps(result, ensure_ascii=False, indent=2)


```

- [ ] **Step 4: Run to verify the tests pass**

```bash
pytest tests/test_tools.py::TestListerLifecycles -v
```

Expected: all 7 tests PASS.

- [ ] **Step 5: Run the full test suite to check for regressions**

```bash
pytest tests/test_tools.py -v
```

Expected: all existing tests still PASS.

- [ ] **Step 6: Commit**

```bash
git add files/greenit_mcp_final.py tests/test_tools.py
git commit -m "feat(mcp): add lister_lifecycles tool — 7 lifecycle phases with counts"
```

---

## Task 2: Add `lister_ressources` MCP tool

**Context:** The cache contains a `saved_resources` list on each fiche with values like `"network"`, `"cpu"`. This tool returns 8 resource types with hardcoded labels (from `i18n/ui.ts`) and live counts, sorted by count descending (most-represented first). The `id` values are compatible with `lister_fiches(saved_resource=...)`.

**Files:**
- Modify: `files/greenit_mcp_final.py`
- Test: `tests/test_tools.py`

- [ ] **Step 1: Write the failing tests**

Add `TestListerRessources` at the end of `tests/test_tools.py` (after `TestListerLifecycles`):

```python
# ============================================================================
# greenit_mcp_final — lister_ressources
# ============================================================================

class TestListerRessources:
    def test_returns_eight_entries(self):
        result = json.loads(greenit_mcp_final.lister_ressources())
        assert len(result) == 8

    def test_sorted_by_count_descending(self):
        result = json.loads(greenit_mcp_final.lister_ressources())
        counts = [entry["count"] for entry in result]
        assert counts == sorted(counts, reverse=True)

    def test_labels_match_i18n(self):
        result = json.loads(greenit_mcp_final.lister_ressources())
        expected_labels = {
            "network":     "Réseau",
            "cpu":         "Processeur",
            "ram":         "Mémoire vive",
            "storage":     "Stockage",
            "requests":    "Requêtes",
            "electricity": "Consommation électrique",
            "ghg":         "Émissions de gaz à effet de serre",
            "e-waste":     "Déchets électroniques",
        }
        for entry in result:
            assert entry["label"] == expected_labels[entry["id"]], (
                f"{entry['id']}: expected {expected_labels[entry['id']]!r}, got {entry['label']!r}"
            )

    def test_counts_are_positive_integers(self):
        result = json.loads(greenit_mcp_final.lister_ressources())
        for entry in result:
            assert isinstance(entry["count"], int)
            assert entry["count"] >= 0

    def test_required_fields_on_every_entry(self):
        result = json.loads(greenit_mcp_final.lister_ressources())
        for entry in result:
            assert "id" in entry
            assert "label" in entry
            assert "count" in entry

    def test_ids_are_valid_lister_fiches_filters(self):
        result = json.loads(greenit_mcp_final.lister_ressources())
        for entry in result:
            fiches = greenit_mcp_final.lister_fiches(saved_resource=entry["id"])
            assert len(fiches) == entry["count"], (
                f"lister_fiches(saved_resource={entry['id']!r}) returned {len(fiches)}, "
                f"but lister_ressources says count={entry['count']}"
            )
```

- [ ] **Step 2: Run to verify the tests fail**

```bash
cd /Users/renaudheluin/DEV/DEV_GREENIT/refs/mcp-115-greenit
pytest tests/test_tools.py::TestListerRessources -v
```

Expected: `FAILED — AttributeError: module 'greenit_mcp_final' has no attribute 'lister_ressources'`

- [ ] **Step 3: Implement `lister_ressources` in `greenit_mcp_final.py`**

Immediately after the `lister_lifecycles` tool (after its closing blank line), add:

```python
_RESSOURCE_LABELS = {
    "network":     "Réseau",
    "cpu":         "Processeur",
    "ram":         "Mémoire vive",
    "storage":     "Stockage",
    "requests":    "Requêtes",
    "electricity": "Consommation électrique",
    "ghg":         "Émissions de gaz à effet de serre",
    "e-waste":     "Déchets électroniques",
}


@mcp.tool()
def lister_ressources() -> str:
    """
    Liste les 8 types de ressources sauvegardées du référentiel GreenIT.

    Les ids retournés sont directement utilisables comme valeur du filtre
    `saved_resource` dans `lister_fiches`.

    Returns:
        JSON : liste de 8 entrées {id, label, count}, triées par count décroissant.
    """
    cache = charger_cache()
    counts: dict[str, int] = {r: 0 for r in _RESSOURCE_LABELS}
    for fiche in cache.values():
        for r in fiche.get("saved_resources", []):
            if r in counts:
                counts[r] += 1
    result = [
        {"id": r, "label": label, "count": counts[r]}
        for r, label in _RESSOURCE_LABELS.items()
    ]
    result.sort(key=lambda e: e["count"], reverse=True)
    return json.dumps(result, ensure_ascii=False, indent=2)


```

- [ ] **Step 4: Run to verify the tests pass**

```bash
pytest tests/test_tools.py::TestListerRessources -v
```

Expected: all 6 tests PASS.

- [ ] **Step 5: Run the full test suite to check for regressions**

```bash
pytest tests/test_tools.py -v
```

Expected: all existing tests still PASS.

- [ ] **Step 6: Commit**

```bash
git add files/greenit_mcp_final.py tests/test_tools.py
git commit -m "feat(mcp): add lister_ressources tool — 8 resource types with counts"
```
