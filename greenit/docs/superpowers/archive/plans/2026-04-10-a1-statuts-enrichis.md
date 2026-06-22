# A1 — Statuts enrichis dans auditer_url — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the MDX parser so `maxValue` survives into the cache, then create `files/checklist.py` with an enriched `map_metrics_to_fiches` that assigns `validation_rule`, `max_value`, `statut`, and `valeur_mesuree` to each fiche.

**Architecture:** The MDX parser in `preparer_donnees_final.py` currently treats nested YAML list objects as plain strings, losing `maxValue`. Fix adds `current_dict` tracking for 4-space-indented properties. `checklist.py` wraps the existing `audit_url.map_metrics_to_fiches` and enriches each returned fiche using the corrected cache. Auto-validation uses a static metric-mapping table for the two currently auto-testable fiches (RWEB_0047, RWEB_0032).

**Tech Stack:** Python 3.11, pytest, no new dependencies.

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `files/preparer_donnees_final.py` | Modify | Fix `parser_mdx` to parse nested YAML objects in list items |
| `files/greenit_cache.json` | Regenerate | Rebuilt after parser fix via `--github` mode |
| `files/checklist.py` | Create | `_auto_validate`, `map_metrics_to_fiches` (enriched), `STATUTS_POSSIBLES` |
| `tests/test_tools.py` | Modify | Add `TestParserMdx`, `TestAutoValidate`, `TestMapMetricsFichesEnriched` |

---

## Task 1: Fix the MDX Parser

**Context:** `preparer_donnees_final.py::parser_mdx` (lines 144–175) parses GitHub MDX frontmatter with a hand-rolled loop. The YAML structure for validations is:

```yaml
validations:
  - rule: de requêtes HTTP    ← 2-space indent, a key-value list item
    maxValue: '40'            ← 4-space indent, a property of the dict above
```

Current code captures `"rule: de requêtes HTTP"` as a plain string and silently drops the `maxValue` line (4-space indent matches no pattern).

**Files:**
- Modify: `files/preparer_donnees_final.py`
- Test: `tests/test_tools.py`

- [ ] **Step 1: Write the failing test**

Add a new class `TestParserMdx` at the end of `tests/test_tools.py` (before the last existing class or at the bottom):

```python
# ============================================================================
# preparer_donnees_final — parser_mdx
# ============================================================================

import preparer_donnees_final as prep_module


class TestParserMdx:
    def _make_mdx(self, validations_block: str) -> str:
        return (
            "---\n"
            "refID: 47\n"
            "refType: RWEB\n"
            "title: Test\n"
            "lifecycle: 3-developement\n"
            "environmental_impact: 4\n"
            "priority_implementation: 4\n"
            "saved_resources:\n"
            "  - network\n"
            f"{validations_block}"
            "---\n"
            "## Description\n\n"
            "Test description.\n"
        )

    def test_nested_validation_extracts_rule_and_max_value(self):
        mdx = self._make_mdx(
            "validations:\n"
            "  - rule: de requêtes HTTP\n"
            "    maxValue: '40'\n"
        )
        result = prep_module.parser_mdx(mdx)
        assert result["validations"] == [{"rule": "de requêtes HTTP", "maxValue": "40"}]

    def test_simple_list_items_unchanged(self):
        mdx = self._make_mdx(
            "saved_resources:\n"
            "  - network\n"
            "  - images\n"
            "validations:\n"
            "  - rule: something\n"
        )
        result = prep_module.parser_mdx(mdx)
        # saved_resources stays a flat list of strings
        assert result["saved_resources"] == ["network", "images"]

    def test_missing_mdx_returns_empty(self):
        result = prep_module.parser_mdx("no frontmatter here")
        assert result == {}

    def test_multiple_nested_properties(self):
        mdx = self._make_mdx(
            "validations:\n"
            "  - rule: de polices\n"
            "    maxValue: '2'\n"
        )
        result = prep_module.parser_mdx(mdx)
        assert result["validations"][0]["maxValue"] == "2"
```

- [ ] **Step 2: Run to verify the test fails**

```bash
cd /Users/renaudheluin/DEV/DEV_GREENIT/refs/mcp-115-greenit
pytest tests/test_tools.py::TestParserMdx -v
```

Expected: `FAILED — AssertionError: assert ['rule: de requêtes HTTP'] == [{'rule': 'de requêtes HTTP', 'maxValue': '40'}]`

- [ ] **Step 3: Fix the parser**

In `files/preparer_donnees_final.py`, replace the `parser_mdx` function body (the variables and loop, lines 145–175) with the version below. The change: add `current_dict = None` before the loop, reset it on top-level key events, and add two new branches — one to detect a list item that is itself a key-value pair, and one to absorb 4-space-indented properties into `current_dict`.

```python
def parser_mdx(contenu: str) -> Dict:
    """Parse un fichier MDX et retourne les données structurées."""
    match = re.match(r'^---\n(.*?)\n---\n(.*)$', contenu, re.DOTALL)
    if not match:
        return {}

    frontmatter_raw = match.group(1)
    body = match.group(2).strip()

    frontmatter = {}
    current_key = None
    current_list = None
    current_dict = None  # tracks the current dict object within a list

    for line in frontmatter_raw.splitlines():
        # Clé: valeur simple
        kv = re.match(r'^(\w+):\s*(.+)$', line)
        if kv:
            current_list = None
            current_dict = None
            key, val = kv.group(1), kv.group(2).strip().strip("'\"")
            try:
                val = int(val)
            except ValueError:
                pass
            frontmatter[key] = val
            current_key = key
            continue

        # Clé sans valeur (début de liste)
        key_only = re.match(r'^(\w+):\s*$', line)
        if key_only:
            current_key = key_only.group(1)
            frontmatter[current_key] = []
            current_list = frontmatter[current_key]
            current_dict = None
            continue

        # Élément de liste (2-space indent: "  - ...")
        list_item = re.match(r'^  - (.+)$', line)
        if list_item and current_list is not None:
            content = list_item.group(1).strip()
            nested_kv = re.match(r'^(\w+):\s*(.*)$', content)
            if nested_kv:
                # List item is itself a key-value → start a dict
                k, v = nested_kv.group(1), nested_kv.group(2).strip().strip("'\"")
                current_dict = {k: v}
                current_list.append(current_dict)
            else:
                current_dict = None
                current_list.append(content.strip("'\""))
            continue

        # Propriété d'un objet de liste (4-space indent: "    key: value")
        nested_item = re.match(r'^    (\w+):\s*(.*)$', line)
        if nested_item and current_dict is not None:
            k, v = nested_item.group(1), nested_item.group(2).strip().strip("'\"")
            current_dict[k] = v
            continue

    # Extraire la description courte (première phrase du body)
    description_match = re.search(r'## Description\s*\n\n(.+?)(?:\n\n|\Z)', body, re.DOTALL)
    short_desc = ""
    if description_match:
        first_para = description_match.group(1).strip().split('\n')[0]
        sentence_end = re.search(r'\.\s', first_para)
        short_desc = first_para[:sentence_end.end()-1] if sentence_end else first_para[:200]

    ref_id = str(frontmatter.get("refID", "")).zfill(4)
    ref_type = frontmatter.get("refType", "RWEB")

    return {
        "num": f"{ref_type}_{ref_id}",
        "refID": ref_id,
        "title": frontmatter.get("title", ""),
        "shortDescription": short_desc,
        "description": body,
        "lifecycle": frontmatter.get("lifecycle", ""),
        "environmental_impact": frontmatter.get("environmental_impact", ""),
        "priority_implementation": frontmatter.get("priority_implementation", ""),
        "saved_resources": frontmatter.get("saved_resources", []),
        "validations": frontmatter.get("validations", []),
        "url": f"https://rweb.greenit.fr/fr/fiches/{ref_id}",
        "source": "github"
    }
```

- [ ] **Step 4: Run to verify the test passes**

```bash
pytest tests/test_tools.py::TestParserMdx -v
```

Expected: all 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add files/preparer_donnees_final.py tests/test_tools.py
git commit -m "fix(parser): extract nested YAML objects (rule+maxValue) in MDX list items"
```

---

## Task 2: Regenerate the Cache

**Context:** The existing `files/greenit_cache.json` was generated with the broken parser — all `validations` entries are flat strings. Regenerating via `--github` will rebuild with the fixed parser, populating `maxValue` on fiches that have it (RWEB_0047, RWEB_0032, and others).

**Files:**
- Regenerate: `files/greenit_cache.json`

- [ ] **Step 1: Regenerate the cache from GitHub**

```bash
cd /Users/renaudheluin/DEV/DEV_GREENIT/refs/mcp-115-greenit/files
python3 preparer_donnees_final.py --github
```

Expected output: `115 fichiers trouvés`, `115 fiches chargées`, `✅ Cache sauvegardé`.

- [ ] **Step 2: Verify RWEB_0047 and RWEB_0032 now have maxValue**

```bash
python3 -c "
import json
with open('greenit_cache.json') as f:
    cache = json.load(f)
for k in ['RWEB_0047', 'RWEB_0032']:
    print(k, cache[k].get('validations'))
"
```

Expected:
```
RWEB_0047 [{'rule': 'de requêtes HTTP', 'maxValue': '40'}]
RWEB_0032 [{'rule': 'de polices téléchargées', 'maxValue': '2'}]
```

- [ ] **Step 3: Commit updated cache**

```bash
cd /Users/renaudheluin/DEV/DEV_GREENIT/refs/mcp-115-greenit
git add files/greenit_cache.json
git commit -m "chore: regenerate cache with corrected MDX parser (maxValue now present)"
```

---

## Task 3: Create `files/checklist.py`

**Context:** This new file exposes `_auto_validate` (pure function, no I/O) and an enriched `map_metrics_to_fiches` that wraps the existing one in `audit_url.py` and adds `validation_rule`, `max_value`, `statut`, and `valeur_mesuree` to each fiche. It also exports `STATUTS_POSSIBLES` (used by B1, A2, and E1). Only two fiches are currently auto-testable; all others default to `"Non-testé"`.

**Files:**
- Create: `files/checklist.py`
- Test: `tests/test_tools.py`

- [ ] **Step 1: Write the failing tests**

Add after `TestParserMdx` in `tests/test_tools.py`:

```python
# ============================================================================
# checklist — _auto_validate + map_metrics_to_fiches (enriched)
# ============================================================================

import checklist


class TestAutoValidate:
    def test_rweb_0047_conforme_at_boundary(self):
        assert checklist._auto_validate("RWEB_0047", "40", {"requests": 40}) == "Conforme"

    def test_rweb_0047_conforme_below_max(self):
        assert checklist._auto_validate("RWEB_0047", "40", {"requests": 35}) == "Conforme"

    def test_rweb_0047_non_conforme_above_max(self):
        assert checklist._auto_validate("RWEB_0047", "40", {"requests": 50}) == "Non-conforme"

    def test_rweb_0032_conforme_one_font(self):
        assert checklist._auto_validate("RWEB_0032", "2", {"fonts": ["Arial"]}) == "Conforme"

    def test_rweb_0032_non_conforme_three_fonts(self):
        assert checklist._auto_validate("RWEB_0032", "2", {"fonts": ["A", "B", "C"]}) == "Non-conforme"

    def test_no_max_value_returns_non_teste(self):
        assert checklist._auto_validate("RWEB_0047", None, {"requests": 35}) == "Non-testé"

    def test_range_max_value_returns_non_teste(self):
        # "3 et 10" cannot be cast to float → Non-testé
        assert checklist._auto_validate("RWEB_0047", "3 et 10", {"requests": 5}) == "Non-testé"

    def test_unknown_fiche_returns_non_teste(self):
        # No entry in _METRIC_MAP for RWEB_9999
        assert checklist._auto_validate("RWEB_9999", "40", {"requests": 35}) == "Non-testé"

    def test_missing_metric_returns_non_teste(self):
        # metrics dict doesn't contain "requests"
        assert checklist._auto_validate("RWEB_0047", "40", {}) == "Non-testé"


class TestMapMetricsFichesEnriched:
    @pytest.fixture
    def mock_cache(self):
        return {
            "RWEB_0047": {
                "title": "Limiter le nombre de requêtes HTTP",
                "saved_resources": ["requests", "network"],
                "environmental_impact": 4,
                "priority_implementation": 4,
                "url": "https://rweb.greenit.fr/fr/fiches/0047",
                "lifecycle": "3-developement",
                "validations": [{"rule": "de requêtes HTTP", "maxValue": "40"}],
            },
            "RWEB_0032": {
                "title": "Limiter le nombre de polices téléchargées",
                "saved_resources": ["network", "css"],
                "environmental_impact": 3,
                "priority_implementation": 3,
                "url": "https://rweb.greenit.fr/fr/fiches/0032",
                "lifecycle": "3-developement",
                "validations": [{"rule": "de polices téléchargées", "maxValue": "2"}],
            },
        }

    def _metrics(self, requests=50, fonts=None, grade="A"):
        return {
            "requests": requests,
            "fonts": fonts or [],
            "images_sans_lazy": 0,
            "dom_nodes": 100,
            "size_kb": 100,
            "tracking_scripts": [],
            "compression": True,
            "cache_headers": True,
            "iframes": 0,
            "ecoindex": {"grade": grade},
        }

    def test_enriched_fields_present(self, mock_cache):
        # requests=50 triggers RWEB_0047 (saved_resources includes "requests")
        result = checklist.map_metrics_to_fiches(self._metrics(requests=50), mock_cache)
        fiche = next(f for f in result if f["id"] == "RWEB_0047")
        for field in ("validation_rule", "max_value", "statut", "valeur_mesuree"):
            assert field in fiche, f"Field '{field}' missing"

    def test_non_conforme_when_above_max(self, mock_cache):
        result = checklist.map_metrics_to_fiches(self._metrics(requests=50), mock_cache)
        fiche = next(f for f in result if f["id"] == "RWEB_0047")
        assert fiche["statut"] == "Non-conforme"
        assert fiche["valeur_mesuree"] == 50
        assert fiche["max_value"] == "40"

    def test_conforme_when_within_limit(self, mock_cache):
        # grade=D → RWEB_0047 (ei=4, pi=4) qualifies as prioritaire even with requests=35
        result = checklist.map_metrics_to_fiches(self._metrics(requests=35, grade="D"), mock_cache)
        fiche = next((f for f in result if f["id"] == "RWEB_0047"), None)
        assert fiche is not None, "RWEB_0047 should appear as prioritaire for grade D"
        assert fiche["statut"] == "Conforme"

    def test_fonts_statut_correct(self, mock_cache):
        # 3 fonts → triggers css/network match → RWEB_0032 appears; 3 > 2 → Non-conforme
        result = checklist.map_metrics_to_fiches(
            self._metrics(fonts=["Arial", "Helvetica", "Georgia"]), mock_cache
        )
        fiche = next((f for f in result if f["id"] == "RWEB_0032"), None)
        assert fiche is not None
        assert fiche["statut"] == "Non-conforme"
        assert fiche["valeur_mesuree"] == 3

    def test_statuts_possibles_exported(self):
        assert "Conforme" in checklist.STATUTS_POSSIBLES
        assert "Non-conforme" in checklist.STATUTS_POSSIBLES
        assert "Non-applicable" in checklist.STATUTS_POSSIBLES
        assert "Indéterminé" in checklist.STATUTS_POSSIBLES
        assert "Non-testé" in checklist.STATUTS_POSSIBLES
```

- [ ] **Step 2: Run to verify the tests fail**

```bash
cd /Users/renaudheluin/DEV/DEV_GREENIT/refs/mcp-115-greenit
pytest tests/test_tools.py::TestAutoValidate tests/test_tools.py::TestMapMetricsFichesEnriched -v
```

Expected: `ModuleNotFoundError: No module named 'checklist'`

- [ ] **Step 3: Create `files/checklist.py`**

```python
"""
GreenIT checklist — fiche enrichment with auto-validation status.

Provides:
  - STATUTS_POSSIBLES: dict of all valid statut values and their meanings
  - _auto_validate(fiche_id, max_value, metrics): assign statut for one fiche
  - map_metrics_to_fiches(metrics, cache): enriched wrapper around audit_url's version

Used by: auditer_url (A2), _build_checklist (B1), planifier_remediations (B2).
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

STATUTS_POSSIBLES = {
    "Conforme": "La valeur mesurée respecte la limite définie",
    "Non-conforme": "La valeur mesurée dépasse la limite définie",
    "Non-applicable": "La bonne pratique ne s'applique pas à ce contexte",
    "Indéterminé": "Impossible de déterminer sans inspection manuelle",
    "Non-testé": "Pas de valeur limite définie ou métrique non mesurée",
}

# Mapping: fiche_id → lambda(metrics) -> numeric metric value (or None)
_METRIC_MAP: dict[str, object] = {
    "RWEB_0047": lambda m: m.get("requests"),
    "RWEB_0032": lambda m: len(m.get("fonts", [])),
}

# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------


def _auto_validate(fiche_id: str, max_value: str | None, metrics: dict) -> str:
    """
    Assign statut for a fiche given its max_value and the page metrics.

    Returns "Conforme", "Non-conforme", or "Non-testé".
    Never returns "Non-applicable" or "Indéterminé" — those require manual assignment.

    Rules:
    - max_value is None  → "Non-testé"
    - max_value is a non-numeric string (e.g. "3 et 10")  → "Non-testé"
    - fiche_id not in _METRIC_MAP  → "Non-testé"
    - metric value is None (missing from metrics)  → "Non-testé"
    - metric <= max_value  → "Conforme"
    - metric >  max_value  → "Non-conforme"
    """
    if max_value is None:
        return "Non-testé"
    try:
        max_val_num = float(max_value)
    except (ValueError, TypeError):
        return "Non-testé"
    metric_fn = _METRIC_MAP.get(fiche_id)
    if metric_fn is None:
        return "Non-testé"
    metric_val = metric_fn(metrics)
    if metric_val is None:
        return "Non-testé"
    return "Conforme" if metric_val <= max_val_num else "Non-conforme"


def map_metrics_to_fiches(metrics: dict, cache: dict) -> list:
    """
    Return matching GreenIT fiches enriched with validation metadata.

    Wraps audit_url.map_metrics_to_fiches and adds to each fiche:
      - validation_rule (str | None): human-readable rule from fiche["validations"][0]["rule"]
      - max_value (str | None): threshold from fiche["validations"][0]["maxValue"]
      - statut (str): auto-assigned or "Non-testé"
      - valeur_mesuree: the actual measured metric value, or None

    Args:
        metrics: Page metrics dict (requests, fonts, dom_nodes, …)
        cache:   GreenIT fiches cache (from charger_cache())

    Returns:
        Up to 20 enriched fiches sorted by combined score descending.
    """
    from audit_url import map_metrics_to_fiches as _base_map

    enriched = []
    for f in _base_map(metrics, cache):
        fiche_id = f["id"]
        fiche = cache.get(fiche_id, {})
        validations = fiche.get("validations", [])
        first_val = validations[0] if validations and isinstance(validations[0], dict) else {}
        validation_rule = first_val.get("rule") or None
        max_value = first_val.get("maxValue") or None

        statut = _auto_validate(fiche_id, max_value, metrics)

        metric_fn = _METRIC_MAP.get(fiche_id)
        valeur_mesuree = metric_fn(metrics) if metric_fn else None

        enriched.append({
            **f,
            "validation_rule": validation_rule,
            "max_value": max_value,
            "statut": statut,
            "valeur_mesuree": valeur_mesuree,
        })
    return enriched
```

- [ ] **Step 4: Run to verify all tests pass**

```bash
pytest tests/test_tools.py::TestAutoValidate tests/test_tools.py::TestMapMetricsFichesEnriched -v
```

Expected: all 14 tests PASS.

- [ ] **Step 5: Run the full test suite to check for regressions**

```bash
pytest tests/test_tools.py -v
```

Expected: all existing tests still PASS (no regressions in `TestMapMetricsToFiches`, `TestBuildReport`, etc.).

- [ ] **Step 6: Commit**

```bash
git add files/checklist.py tests/test_tools.py
git commit -m "feat(checklist): create checklist.py with enriched map_metrics_to_fiches and auto-validation"
```
