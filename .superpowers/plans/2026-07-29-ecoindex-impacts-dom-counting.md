# EcoIndex Impacts And DOM Counting Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Return EcoIndex greenhouse-gas and water impacts and prescribe an SVG-aware, Shadow-DOM-aware DOM measurement for Playwright callers.

**Architecture:** Keep the EcoIndex calculation pure in `greenit/files/data.py`; derive impact values from its unclamped, computed score and pass them through the existing MCP tool. The server continues to receive browser metrics rather than adding a Playwright dependency; its guide, tool documentation, and prompt provide the same client-side DOM-counting algorithm.

**Tech Stack:** Python 3.11+, FastMCP, pytest, JavaScript executed with Playwright `page.evaluate()`.

## Global Constraints

- Do not add a URL-measurement tool, a browser dependency, or a network call.
- Return numeric `greenhouse_gases_g` (g CO2e) and `water_consumption_cl` (cl), rounded to two decimal places.
- Count `<svg>` elements but not their descendants; recursively count accessible open Shadow DOM roots.
- Keep all Superpowers files under `.superpowers/`, never under `docs/`.
- Run tests from `greenit/files/` using `pytest ../tests/ -v`.

---

## File Structure

- Modify `greenit/files/data.py`: calculate and return the two impacts with the existing EcoIndex result.
- Modify `greenit/files/greenit_mcp.py`: declare and serialize impact fields; document the browser measurement protocol.
- Modify `greenit/tests/test_ecoindex.py`: cover pure calculation output.
- Modify `greenit/tests/test_tools.py`: cover the serialized MCP result.
- Modify `greenit/tests/test_prompts.py`: cover the prescribed DOM-counting semantics.
- Modify `greenit/tests/test_routes_http.py`: cover the guide’s measurement semantics.
- Modify `greenit/README.md`, `greenit/docs/GUIDE_DEVELOPPEMENT.md`, `greenit/CHANGELOG.md`, and `CHANGELOG.md`: document the changed EcoIndex response and release it.

### Task 1: Return EcoIndex Impact Values

**Files:**
- Modify: `greenit/tests/test_ecoindex.py:25-30`
- Modify: `greenit/tests/test_tools.py:579-584`
- Modify: `greenit/files/data.py:76-88`
- Modify: `greenit/files/greenit_mcp.py:823-878`

**Interfaces:**
- Consumes: `calculer_ecoindex(dom: int, requests: int, size_kb: float) -> dict`.
- Produces: a result with `score: float`, `grade: str`, `greenhouse_gases_g: float`, and `water_consumption_cl: float`.
- Produces: `greenit_calculer_ecoindex(...) -> str` JSON with the same four result fields plus input metrics and URL.

- [ ] **Step 1: Write the failing calculator regression test**

Add this method to `TestEcoIndex` in `greenit/tests/test_ecoindex.py`:

```python
def test_retourne_les_impacts_ecoindex(self):
    result = calculer_ecoindex(0, 0, 0.0)

    assert result["greenhouse_gases_g"] == 1.0
    assert result["water_consumption_cl"] == 1.5
```

- [ ] **Step 2: Write the failing MCP response regression test**

Add this method to `TestCalculerEcoindex` in `greenit/tests/test_tools.py`:

```python
def test_returns_ecological_impacts(self):
    result = json.loads(mcp_module.greenit_calculer_ecoindex(0, 0, 0))

    assert result["greenhouse_gases_g"] == 1.0
    assert result["water_consumption_cl"] == 1.5
```

- [ ] **Step 3: Run the new tests to verify they fail**

Run from `greenit/files/`:

```bash
pytest ../tests/test_ecoindex.py ../tests/test_tools.py::TestCalculerEcoindex::test_returns_ecological_impacts -v
```

Expected: both tests fail with `KeyError` for the missing impact fields.

- [ ] **Step 4: Implement the minimal calculator changes**

In `greenit/files/data.py`, calculate impacts from the computed `score` before rounding the returned score:

```python
greenhouse_gases_g = round(2 + 2 * (50 - score) / 100, 2)
water_consumption_cl = round(3 + 3 * (50 - score) / 100, 2)

return {
    "score": round(score, 2),
    "grade": grade,
    "greenhouse_gases_g": greenhouse_gases_g,
    "water_consumption_cl": water_consumption_cl,
}
```

In `greenit/files/greenit_mcp.py`, add numeric schema properties with the descriptions `Émissions de GES estimées en grammes CO2e` and `Consommation d'eau estimée en centilitres`, then add the same keys from `result` to the serialized dictionary.

- [ ] **Step 5: Run the targeted tests to verify they pass**

Run from `greenit/files/`:

```bash
pytest ../tests/test_ecoindex.py ../tests/test_tools.py::TestCalculerEcoindex -v
```

Expected: all selected tests pass.

- [ ] **Step 6: Commit the completed impact calculation task**

```bash
git add greenit/files/data.py greenit/files/greenit_mcp.py greenit/tests/test_ecoindex.py greenit/tests/test_tools.py
git commit -m "fix(greenit): return EcoIndex impacts"
```

### Task 2: Document SVG- And Shadow-DOM-Aware Measurement

**Files:**
- Modify: `greenit/tests/test_prompts.py:22-33`
- Modify: `greenit/tests/test_routes_http.py:643-653`
- Modify: `greenit/files/greenit_mcp.py:114-132,838-858,903-917`
- Modify: `greenit/README.md:19`
- Modify: `greenit/docs/GUIDE_DEVELOPPEMENT.md:121-125`

**Interfaces:**
- Consumes: the existing `audit_ecoindex(url: str, focus: str = "all") -> str` prompt and `/guide` route.
- Produces: client instructions that execute `countDomNodes(document)` in Playwright before calling `greenit_calculer_ecoindex`.

- [ ] **Step 1: Write the failing prompt test**

Add this method to `TestGreenITPrompts` in `greenit/tests/test_prompts.py`:

```python
def test_audit_ecoindex_prescribes_svg_and_shadow_dom_counting(self):
    result = mcp_module.audit_ecoindex("https://example.com")

    assert "countDomNodes" in result
    assert "shadowRoot" in result
    assert "svg" in result
```

- [ ] **Step 2: Write the failing guide test**

Add this method to `TestGuideGreenItEcoIndex` in `greenit/tests/test_routes_http.py`:

```python
def test_guide_ecoindex_prescribes_svg_and_shadow_dom_counting(self):
    import asyncio

    req = MagicMock()
    req.headers = {"accept": "text/html"}
    response = asyncio.run(routes._http_guide(req))
    body = response.body.decode()

    assert "countDomNodes" in body
    assert "shadowRoot" in body
    assert "svg" in body
```

`MagicMock` and `routes` are already imported by this test module; this matches
the neighboring guide test setup.

- [ ] **Step 3: Run the new tests to verify they fail**

Run from `greenit/files/`:

```bash
pytest ../tests/test_prompts.py::TestGreenITPrompts::test_audit_ecoindex_prescribes_svg_and_shadow_dom_counting ../tests/test_routes_http.py::TestGuideGreenItEcoIndex::test_guide_ecoindex_prescribes_svg_and_shadow_dom_counting -v
```

Expected: both tests fail because the current instructions do not mention `countDomNodes`, `shadowRoot`, or SVG handling.

- [ ] **Step 4: Add the exact measurement protocol**

Add this JavaScript block to the `/guide` EcoIndex protocol, the `greenit_calculer_ecoindex` docstring, and the `audit_ecoindex` prompt:

```js
const countDomNodes = (root) =>
  [...root.querySelectorAll('*')].reduce((total, element) => {
    if (element.parentElement?.closest('svg')) return total;
    return total + 1 + (element.shadowRoot ? countDomNodes(element.shadowRoot) : 0);
  }, 0);

return countDomNodes(document);
```

State beside it that `<svg>` is counted, its descendants are excluded, and closed Shadow DOM cannot be measured. Update `greenit/README.md` and `greenit/docs/GUIDE_DEVELOPPEMENT.md` to state that the result includes GES and water impacts and that callers must use this DOM protocol.

- [ ] **Step 5: Run the targeted tests to verify they pass**

Run from `greenit/files/`:

```bash
pytest ../tests/test_prompts.py ../tests/test_routes_http.py -v
```

Expected: all prompt and HTTP guide tests pass.

- [ ] **Step 6: Commit the completed measurement documentation task**

```bash
git add greenit/files/greenit_mcp.py greenit/tests/test_prompts.py greenit/tests/test_routes_http.py greenit/README.md greenit/docs/GUIDE_DEVELOPPEMENT.md
git commit -m "docs(greenit): specify EcoIndex DOM measurement"
```

### Task 3: Verify And Prepare The Required Patch Release

**Files:**
- Modify: `CHANGELOG.md`
- Modify: `greenit/CHANGELOG.md`

**Interfaces:**
- Consumes: the implementation from Tasks 1 and 2 and the repository release process.
- Produces: a tested patch-release candidate whose changelogs describe the returned impacts and DOM protocol.

- [ ] **Step 1: Run the full GreenIT test suite**

Run from `greenit/files/`:

```bash
pytest ../tests/ -v
```

Expected: all tests pass; existing Docker integration skips remain unchanged if Docker is unavailable.

- [ ] **Step 2: Add changelog entries for version 2.3.2**

Replace each current empty `Unreleased` section with `## [2.3.2] — 2026-07-29`
and add these entries under `Corrigé`:

```markdown
- Retourne les impacts estimés de GES et de consommation d'eau avec chaque calcul EcoIndex.
- Documente un comptage DOM qui exclut les descendants SVG et parcourt les Shadow DOM ouverts.
```

Update both `CHANGELOG.md` and `greenit/CHANGELOG.md`.

- [ ] **Step 3: Verify documentation and changelog diffs**

Run from the repository root:

```bash
git diff --check
git diff -- CHANGELOG.md greenit/CHANGELOG.md greenit/README.md greenit/docs/GUIDE_DEVELOPPEMENT.md
```

Expected: no whitespace errors; the output describes only the approved EcoIndex behavior.

- [ ] **Step 4: Commit the release documentation task**

```bash
git add CHANGELOG.md greenit/CHANGELOG.md
git commit -m "docs(greenit): prepare EcoIndex impact release"
```

- [ ] **Step 5: Follow the repository release checklist after merge approval**

Run only after the branch is merged with explicit authorization:

```bash
./release.sh 2.3.2
git push origin v2.3.2
```

Expected: `release.sh` reruns tests, creates the release commit and tag; the tag exists remotely after the push.

## Plan Review

- Spec coverage: Task 1 implements and tests both reference formulas and their MCP serialization. Task 2 implements and tests the SVG and Shadow DOM protocol. Task 3 verifies the full server and documents the production release.
- Placeholder scan: no unresolved requirements or implementation placeholders remain.
- Type consistency: calculator and MCP fields use the same numeric names: `greenhouse_gases_g` and `water_consumption_cl`.
