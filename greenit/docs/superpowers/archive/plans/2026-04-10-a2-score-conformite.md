# A2 — Score de conformité Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create `files/report.py` with an enhanced `build_report` that adds `score_conformite` and `audit_complet` (115 fiches) to the audit dict; add `render_markdown` and `render_html`; update `auditer_url` in `greenit_mcp_final.py` to use the new report module and write 3 files to disk via an `output_dir` parameter.

**Architecture:** `report.py::build_report(pages, start_url, cache) -> dict` always returns a dict. It calls `_build_checklist(cache)` (B1) for the 115-fiche base, then calls `checklist.map_metrics_to_fiches` per page to override statuts for auto-testable fiches. `render_markdown` and `render_html` take the dict and produce formatted output. `auditer_url` in `greenit_mcp_final.py` calls these three functions, writes the 3 output files, and returns markdown. The old `audit_url.py::build_report` is kept untouched to avoid breaking existing tests.

**Tech Stack:** Python 3.11, FastMCP, pytest. No new dependencies. Builds on `checklist.py` from A1/B1.

**Prerequisites:** A1 (checklist.py with `_auto_validate`, `map_metrics_to_fiches`, `STATUTS_POSSIBLES`) and B1 (`_build_checklist`) must be implemented first.

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `files/report.py` | Create | `build_report` (dict), `render_markdown`, `render_html` |
| `files/greenit_mcp_final.py` | Modify | `auditer_url`: import from `report.py`, add `output_dir`, write 3 files |
| `tests/test_tools.py` | Modify | Add `TestReportBuildReport`, `TestRenderMarkdown`, `TestAuditerUrlOutputDir` |

---

## Task 1: Create `files/report.py`

**Context:** `audit_url.py::build_report` returns str or dict based on `format` param, and has no `score_conformite` or `audit_complet`. The new `report.py::build_report` always returns a dict, adds `score_conformite` and `audit_complet`, and delegates rendering to separate functions. `audit_url.py` is not modified — its `build_report` keeps working for existing tests.

**Files:**
- Create: `files/report.py`
- Test: `tests/test_tools.py`

- [ ] **Step 1: Write the failing tests**

Add a new class `TestReportBuildReport` at the end of `tests/test_tools.py` (after `TestObtenirChecklistAudit` added in B1). Note: `import report` must be added to the imports at the top of the test file alongside `import audit_url`, `import checklist`, etc.

```python
# ============================================================================
# report — build_report + render_markdown + render_html
# ============================================================================

import report as report_module


def _fake_page(url="https://example.com", requests=20, dom_nodes=100,
               size_kb=200.0, grade="A", fonts=None):
    """Minimal valid page metrics dict matching what crawl() produces."""
    return {
        "url": url,
        "dom_nodes": dom_nodes,
        "requests": requests,
        "size_kb": size_kb,
        "images_sans_lazy": 0,
        "images_sans_alt": 0,
        "iframes": 0,
        "fonts": fonts or [],
        "compression": True,
        "cache_headers": True,
        "tracking_scripts": [],
        "ttfb_ms": 50,
        "fcp_ms": 300,
        "lcp_ms": None,
        "ecoindex_score": 75.0,
        "grade": grade,
        "resource_types": {},
    }


class TestReportBuildReport:
    @pytest.fixture
    def small_cache(self):
        """3-fiche cache — enough to test score logic without 115-fiche overhead."""
        return {
            "RWEB_0047": {
                "title": "Limiter le nombre de requêtes HTTP",
                "lifecycle": "3-developement",
                "url": "https://rweb.greenit.fr/fr/fiches/0047",
                "environmental_impact": 4,
                "priority_implementation": 4,
                "saved_resources": ["requests", "network"],
                "validations": [{"rule": "de requêtes HTTP", "maxValue": "40"}],
            },
            "RWEB_0002": {
                "title": "Fiche B",
                "lifecycle": "2-concept",
                "url": "https://rweb.greenit.fr/fr/fiches/0002",
                "environmental_impact": 3,
                "priority_implementation": 3,
                "saved_resources": ["cpu"],
                "validations": [],
            },
            "RWEB_0003": {
                "title": "Fiche C",
                "lifecycle": "5-hebergement",
                "url": "https://rweb.greenit.fr/fr/fiches/0003",
                "environmental_impact": 1,
                "priority_implementation": 2,
                "saved_resources": ["storage"],
                "validations": [],
            },
        }

    def test_score_conformite_present(self, small_cache):
        pages = [_fake_page()]
        data = report_module.build_report(pages, "https://example.com", small_cache)
        assert "score_conformite" in data
        sc = data["score_conformite"]
        assert "score_pct" in sc
        assert sc["total"] == 3  # small_cache has 3 fiches

    def test_score_pct_formula(self, small_cache):
        # requests=20 ≤ 40 → RWEB_0047 is Conforme; others Non-testé
        pages = [_fake_page(requests=20)]
        data = report_module.build_report(pages, "https://example.com", small_cache)
        sc = data["score_conformite"]
        assert sc["conforme"] == 1
        assert sc["score_pct"] == round(1 / 3 * 100, 1)

    def test_score_pct_non_conforme(self, small_cache):
        # requests=50 > 40 → RWEB_0047 is Non-conforme
        pages = [_fake_page(requests=50)]
        data = report_module.build_report(pages, "https://example.com", small_cache)
        sc = data["score_conformite"]
        assert sc["conforme"] == 0
        assert sc["non_conforme"] == 1

    def test_audit_complet_count_matches_cache(self, small_cache):
        pages = [_fake_page()]
        data = report_module.build_report(pages, "https://example.com", small_cache)
        assert len(data["audit_complet"]) == 3

    def test_audit_complet_sort_non_conforme_first(self, small_cache):
        # requests=50 → RWEB_0047 Non-conforme; others Non-testé
        pages = [_fake_page(requests=50)]
        data = report_module.build_report(pages, "https://example.com", small_cache)
        statuts = [f["statut"] for f in data["audit_complet"]]
        assert statuts[0] == "Non-conforme"

    def test_audit_complet_conforme_before_non_teste(self, small_cache):
        # requests=20 → RWEB_0047 Conforme; others Non-testé
        pages = [_fake_page(requests=20)]
        data = report_module.build_report(pages, "https://example.com", small_cache)
        statuts = [f["statut"] for f in data["audit_complet"]]
        assert statuts[0] == "Conforme"
        assert all(s == "Non-testé" for s in statuts[1:])

    def test_pages_key_contains_urls(self, small_cache):
        pages = [_fake_page("https://example.com"), _fake_page("https://example.com/about")]
        data = report_module.build_report(pages, "https://example.com", small_cache)
        urls = [p["url"] for p in data["pages"]]
        assert "https://example.com" in urls
        assert "https://example.com/about" in urls

    def test_returns_dict_not_str(self, small_cache):
        data = report_module.build_report([_fake_page()], "https://example.com", small_cache)
        assert isinstance(data, dict)

    def test_valeur_mesuree_set_for_auto_validated(self, small_cache):
        pages = [_fake_page(requests=50)]
        data = report_module.build_report(pages, "https://example.com", small_cache)
        fiche = next(f for f in data["audit_complet"] if f["id"] == "RWEB_0047")
        assert fiche["valeur_mesuree"] == 50


class TestRenderMarkdown:
    @pytest.fixture
    def sample_data(self):
        cache = {
            "RWEB_0047": {
                "title": "Limiter requêtes HTTP",
                "lifecycle": "3-developement",
                "url": "https://rweb.greenit.fr/fr/fiches/0047",
                "environmental_impact": 4,
                "priority_implementation": 4,
                "saved_resources": ["requests"],
                "validations": [{"rule": "de requêtes HTTP", "maxValue": "40"}],
            }
        }
        return report_module.build_report([_fake_page(requests=50)], "https://example.com", cache)

    def test_contains_score_section(self, sample_data):
        md = report_module.render_markdown(sample_data)
        assert "Score de conformité" in md

    def test_contains_audit_complet_section(self, sample_data):
        md = report_module.render_markdown(sample_data)
        assert "Audit complet" in md
        assert "RWEB_0047" in md

    def test_contains_url(self, sample_data):
        md = report_module.render_markdown(sample_data)
        assert "example.com" in md


class TestRenderHtml:
    @pytest.fixture
    def sample_data(self):
        cache = {
            "RWEB_0047": {
                "title": "Limiter requêtes HTTP",
                "lifecycle": "3-developement",
                "url": "https://rweb.greenit.fr/fr/fiches/0047",
                "environmental_impact": 4,
                "priority_implementation": 4,
                "saved_resources": ["requests"],
                "validations": [{"rule": "de requêtes HTTP", "maxValue": "40"}],
            }
        }
        return report_module.build_report([_fake_page(requests=50)], "https://example.com", cache)

    def test_valid_html_structure(self, sample_data):
        html = report_module.render_html(sample_data)
        assert "<!DOCTYPE html>" in html
        assert "<html" in html
        assert "</html>" in html

    def test_no_external_dependencies(self, sample_data):
        html = report_module.render_html(sample_data)
        assert "cdn." not in html
        assert 'src="http' not in html
        assert 'href="http' not in html

    def test_contains_fiche_id(self, sample_data):
        html = report_module.render_html(sample_data)
        assert "RWEB_0047" in html
```

- [ ] **Step 2: Run to verify the tests fail**

```bash
cd /Users/renaudheluin/DEV/DEV_GREENIT/refs/mcp-115-greenit
pytest tests/test_tools.py::TestReportBuildReport tests/test_tools.py::TestRenderMarkdown tests/test_tools.py::TestRenderHtml -v
```

Expected: `ModuleNotFoundError: No module named 'report'`

- [ ] **Step 3: Create `files/report.py`**

```python
"""
GreenIT audit report builder.

Provides:
  - build_report(pages, start_url, cache) -> dict
  - render_markdown(data: dict) -> str
  - render_html(data: dict) -> str

Used by: auditer_url (A2), planifier_remediations (B2).
"""

from __future__ import annotations
from collections import Counter
from urllib.parse import urlparse


def build_report(pages: list, start_url: str, cache: dict) -> dict:
    """
    Build an audit report dict from crawled page metrics.

    Combines EcoIndex analysis with a full GreenIT conformity assessment
    across all 115 best-practice fiches.

    Args:
        pages:     List of page metrics dicts from crawl()
        start_url: The URL that was audited
        cache:     GreenIT fiches cache from charger_cache()

    Returns:
        dict with keys: url, pages_analysees, ecoindex_moyen, grade_moyen,
        pages, recommandations, score_conformite, audit_complet
    """
    from audit_url import compute_ecoindex
    from checklist import _build_checklist, map_metrics_to_fiches as checklist_map

    valid_pages = [p for p in pages if "error" not in p]

    # ── EcoIndex average ──────────────────────────────────────────────────────
    scores = [p["ecoindex_score"] for p in valid_pages if "ecoindex_score" in p]
    if scores:
        ecoindex_moyen = round(sum(scores) / len(scores), 2)
        avg_dom  = int(sum(p["dom_nodes"] for p in valid_pages) / len(valid_pages))
        avg_req  = int(sum(p["requests"] for p in valid_pages) / len(valid_pages))
        avg_size = sum(p["size_kb"] for p in valid_pages) / len(valid_pages)
        grade_moyen = compute_ecoindex(avg_dom, avg_req, avg_size)["grade"]
    else:
        ecoindex_moyen = None
        grade_moyen = None

    # ── Global recommendations (top 10 fiches by occurrence) ─────────────────
    fiche_counter: Counter = Counter()
    fiche_map: dict = {}
    for page in valid_pages:
        metrics = dict(page, ecoindex={"grade": page.get("grade", "A")})
        for f in checklist_map(metrics, cache):
            fiche_counter[f["id"]] += 1
            fiche_map[f["id"]] = f

    recommandations = [
        {**fiche_map[fid], "occurrences": count}
        for fid, count in fiche_counter.most_common(10)
    ]

    # ── Pages enriched with per-page fiches ───────────────────────────────────
    pages_out = []
    for page in valid_pages:
        p = {k: v for k, v in page.items() if k != "_links"}
        metrics = dict(page, ecoindex={"grade": page.get("grade", "A")})
        p["fiches_greenit"] = checklist_map(metrics, cache)
        pages_out.append(p)
    for page in pages:
        if "error" in page:
            pages_out.append(page)

    # ── Audit complet: 115-fiche checklist with auto-validation overrides ─────
    checklist_data = _build_checklist(cache)
    fiches_by_id: dict = {f["id"]: dict(f) for f in checklist_data["fiches"]}

    for page in valid_pages:
        metrics = dict(page, ecoindex={"grade": page.get("grade", "A")})
        for enriched in checklist_map(metrics, cache):
            fid = enriched["id"]
            if fid in fiches_by_id and fiches_by_id[fid]["statut"] == "Non-testé":
                fiches_by_id[fid]["statut"] = enriched["statut"]
                fiches_by_id[fid]["valeur_mesuree"] = enriched["valeur_mesuree"]

    _order = {"Non-conforme": 0, "Conforme": 1, "Indéterminé": 2, "Non-applicable": 3, "Non-testé": 4}
    audit_complet = sorted(
        fiches_by_id.values(),
        key=lambda f: (_order.get(f["statut"], 99), -f["environmental_impact"]),
    )

    # ── Score de conformité ───────────────────────────────────────────────────
    total = len(audit_complet)
    conformes     = sum(1 for f in audit_complet if f["statut"] == "Conforme")
    non_conformes = sum(1 for f in audit_complet if f["statut"] == "Non-conforme")
    non_applicables = sum(1 for f in audit_complet if f["statut"] == "Non-applicable")
    indetermines  = sum(1 for f in audit_complet if f["statut"] == "Indéterminé")
    non_testes    = sum(1 for f in audit_complet if f["statut"] == "Non-testé")

    score_conformite = {
        "score_pct": round(conformes / total * 100, 1) if total else 0.0,
        "conforme": conformes,
        "non_conforme": non_conformes,
        "non_applicable": non_applicables,
        "indetermine": indetermines,
        "non_teste": non_testes,
        "total": total,
    }

    return {
        "url": start_url,
        "pages_analysees": len(pages),
        "ecoindex_moyen": ecoindex_moyen,
        "grade_moyen": grade_moyen,
        "pages": pages_out,
        "recommandations": recommandations,
        "score_conformite": score_conformite,
        "audit_complet": audit_complet,
    }


def render_markdown(data: dict) -> str:
    """Render audit data dict as a markdown report string."""
    url = data.get("url", "")
    score = data.get("score_conformite", {})
    pages = data.get("pages", [])
    recommandations = data.get("recommandations", [])
    audit_complet = data.get("audit_complet", [])

    lines = [
        f"# Audit GreenIT — {url}",
        "",
        f"**Pages analysées :** {data.get('pages_analysees')}  ",
        f"**EcoIndex moyen :** {data.get('ecoindex_moyen')} / 100  ",
        f"**Grade moyen :** {data.get('grade_moyen')}",
        "",
        "## Score de conformité",
        "",
        f"**Score :** {score.get('score_pct')}% ({score.get('conforme')}/{score.get('total')} fiches conformes)",
        "",
        "| Statut | Nombre |",
        "|--------|--------|",
        f"| Conforme | {score.get('conforme', 0)} |",
        f"| Non-conforme | {score.get('non_conforme', 0)} |",
        f"| Non-applicable | {score.get('non_applicable', 0)} |",
        f"| Indéterminé | {score.get('indetermine', 0)} |",
        f"| Non-testé | {score.get('non_teste', 0)} |",
        "",
        "---",
        "",
    ]

    for page in pages:
        if "error" in page:
            lines.append(f"## {page['url']} ⚠️ Erreur")
            lines.append(f"> {page['error']}")
            lines.append("")
            continue
        lines.append(f"## {page['url']}")
        lines.append("")
        lines.append(f"**EcoIndex :** {page.get('ecoindex_score')} / 100 — Grade **{page.get('grade')}**")
        lines.append("")
        lines.append("| Métrique | Valeur |")
        lines.append("|---|---|")
        lines.append(f"| Nœuds DOM | {page.get('dom_nodes')} |")
        lines.append(f"| Requêtes | {page.get('requests')} |")
        lines.append(f"| Poids total | {page.get('size_kb')} KB |")
        lines.append(f"| Images sans lazy | {page.get('images_sans_lazy')} |")
        lines.append(f"| Compression | {'✓' if page.get('compression') else '✗'} |")
        lines.append(f"| Cache headers | {'✓' if page.get('cache_headers') else '✗'} |")
        lines.append(f"| Scripts tracking | {', '.join(page.get('tracking_scripts', [])) or 'aucun'} |")
        lines.append(f"| TTFB | {page.get('ttfb_ms')} ms |")
        lines.append(f"| FCP | {page.get('fcp_ms')} ms |")
        lines.append("")

    lines += [
        "---",
        "",
        "## Recommandations globales",
        "",
    ]
    for r in recommandations:
        lines.append(
            f"- **{r['titre']}** — {r.get('occurrences', 1)} page(s) · "
            f"impact: {r['environmental_impact']}, priorité: {r['priority_implementation']}"
        )

    lines += [
        "",
        "---",
        "",
        f"## Audit complet — {len(audit_complet)} fiches",
        "",
        "| ID | Titre | Lifecycle | Statut | Valeur mesurée | Max | Impact | Priorité |",
        "|----|-------|-----------|--------|---------------|-----|--------|---------|",
    ]
    for f in audit_complet:
        val = f["valeur_mesuree"] if f["valeur_mesuree"] is not None else "—"
        mx  = f["max_value"] if f["max_value"] is not None else "—"
        lines.append(
            f"| {f['id']} | {f['titre']} | {f['lifecycle']} | {f['statut']}"
            f" | {val} | {mx} | {f['environmental_impact']} | {f['priority_implementation']} |"
        )

    return "\n".join(lines)


def render_html(data: dict) -> str:
    """Render audit data dict as a self-contained HTML file (no external deps)."""
    url      = data.get("url", "")
    score    = data.get("score_conformite", {})
    audit_complet = data.get("audit_complet", [])

    badge_color = {
        "Conforme":       "#22c55e",
        "Non-conforme":   "#ef4444",
        "Non-applicable": "#94a3b8",
        "Indéterminé":    "#f59e0b",
        "Non-testé":      "#6b7280",
    }

    audit_rows = ""
    for f in audit_complet:
        color = badge_color.get(f["statut"], "#6b7280")
        val   = f["valeur_mesuree"] if f["valeur_mesuree"] is not None else "—"
        mx    = f["max_value"] if f["max_value"] is not None else "—"
        audit_rows += (
            f'<tr>'
            f'<td><a href="{f["url"]}" target="_blank">{f["id"]}</a></td>'
            f'<td>{f["titre"]}</td>'
            f'<td><span style="color:{color};font-weight:bold">{f["statut"]}</span></td>'
            f'<td>{val}</td><td>{mx}</td>'
            f'<td>{f["environmental_impact"]}</td>'
            f'</tr>\n'
        )

    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Audit GreenIT \u2014 {url}</title>
<style>
body{{font-family:system-ui,sans-serif;max-width:1200px;margin:0 auto;padding:1rem 2rem;color:#1e293b}}
h1{{color:#166534}}h2{{color:#15803d;border-bottom:1px solid #d1fae5;padding-bottom:.25rem}}
.score-box{{display:flex;gap:2rem;flex-wrap:wrap;background:#f0fdf4;border:1px solid #bbf7d0;border-radius:8px;padding:1.5rem;margin:1rem 0}}
.score-item{{text-align:center}}.score-value{{font-size:2rem;font-weight:bold;color:#15803d}}
.score-label{{font-size:.875rem;color:#64748b}}
table{{border-collapse:collapse;width:100%;margin:1rem 0;font-size:.875rem}}
th{{background:#f8fafc;font-weight:600;text-align:left;padding:.5rem .75rem;border:1px solid #e2e8f0}}
td{{padding:.4rem .75rem;border:1px solid #e2e8f0}}tr:hover{{background:#f8fafc}}
a{{color:#15803d}}
</style>
</head>
<body>
<h1>Audit GreenIT</h1>
<p><strong>URL :</strong> <a href="{url}">{url}</a></p>
<div class="score-box">
  <div class="score-item"><div class="score-value">{score.get("score_pct", 0)}%</div><div class="score-label">Score de conformit\u00e9</div></div>
  <div class="score-item"><div class="score-value">{score.get("conforme", 0)}/{score.get("total", 115)}</div><div class="score-label">Fiches conformes</div></div>
  <div class="score-item"><div class="score-value">{data.get("grade_moyen", "\u2014")}</div><div class="score-label">Grade EcoIndex moyen</div></div>
  <div class="score-item"><div class="score-value">{data.get("ecoindex_moyen", "\u2014")}</div><div class="score-label">EcoIndex moyen</div></div>
</div>
<h2>Score de conformit\u00e9</h2>
<table>
<tr><th>Statut</th><th>Nombre</th></tr>
<tr><td>Conforme</td><td>{score.get("conforme", 0)}</td></tr>
<tr><td>Non-conforme</td><td>{score.get("non_conforme", 0)}</td></tr>
<tr><td>Non-applicable</td><td>{score.get("non_applicable", 0)}</td></tr>
<tr><td>Ind\u00e9termin\u00e9</td><td>{score.get("indetermine", 0)}</td></tr>
<tr><td>Non-test\u00e9</td><td>{score.get("non_teste", 0)}</td></tr>
</table>
<h2>Audit complet \u2014 {len(audit_complet)} fiches</h2>
<table>
<tr><th>ID</th><th>Titre</th><th>Statut</th><th>Valeur mesur\u00e9e</th><th>Max</th><th>Impact</th></tr>
{audit_rows}
</table>
</body>
</html>"""
```

- [ ] **Step 4: Run to verify the tests pass**

```bash
pytest tests/test_tools.py::TestReportBuildReport tests/test_tools.py::TestRenderMarkdown tests/test_tools.py::TestRenderHtml -v
```

Expected: all tests PASS.

- [ ] **Step 5: Run the full test suite to check for regressions**

```bash
pytest tests/test_tools.py -v
```

Expected: all existing tests still PASS (the old `audit_url::build_report` is untouched).

- [ ] **Step 6: Commit**

```bash
git add files/report.py tests/test_tools.py
git commit -m "feat(report): create report.py with build_report, render_markdown, render_html"
```

---

## Task 2: Update `auditer_url` in `greenit_mcp_final.py`

**Context:** `greenit_mcp_final.py::auditer_url` currently imports `build_report` from `audit_url` (old version, returns str/dict based on `format` param). This task changes it to use `report.py::build_report` (always dict), adds an `output_dir: str = "."` parameter, and writes 3 files to `{output_dir}/{YYYY-MM-DD}/greenit-audit-{domain}.{json,md,html}`. The tool returns markdown with a footer listing the paths of the written files. The `format` parameter is removed (markdown is always the return format).

**Files:**
- Modify: `files/greenit_mcp_final.py`
- Test: `tests/test_tools.py`

- [ ] **Step 1: Write the failing test**

Add a new class `TestAuditerUrlOutputDir` at the end of `tests/test_tools.py`:

```python
# ============================================================================
# greenit_mcp_final — auditer_url with output_dir
# ============================================================================

import pytest
from unittest.mock import patch, AsyncMock


def _fake_page_full(url="https://example.com"):
    """Full page metrics dict as returned by crawl()."""
    return {
        "url": url,
        "dom_nodes": 100,
        "requests": 20,
        "size_kb": 150.0,
        "images_sans_lazy": 0,
        "images_sans_alt": 0,
        "iframes": 0,
        "fonts": [],
        "compression": True,
        "cache_headers": True,
        "tracking_scripts": [],
        "ttfb_ms": 50,
        "fcp_ms": 300,
        "lcp_ms": None,
        "ecoindex_score": 75.0,
        "grade": "B",
        "resource_types": {},
    }


class TestAuditerUrlOutputDir:
    @pytest.mark.asyncio
    async def test_creates_three_files(self, tmp_path):
        fake_pages = [_fake_page_full()]
        with patch("greenit_mcp_final._crawl", new=AsyncMock(return_value=fake_pages)):
            await greenit_mcp_final.auditer_url(
                url="https://example.com",
                output_dir=str(tmp_path),
            )
        date_dir = tmp_path / "2026-04-10"
        assert (date_dir / "greenit-audit-example.com.json").exists()
        assert (date_dir / "greenit-audit-example.com.md").exists()
        assert (date_dir / "greenit-audit-example.com.html").exists()

    @pytest.mark.asyncio
    async def test_json_file_contains_score_conformite(self, tmp_path):
        fake_pages = [_fake_page_full()]
        with patch("greenit_mcp_final._crawl", new=AsyncMock(return_value=fake_pages)):
            await greenit_mcp_final.auditer_url(
                url="https://example.com",
                output_dir=str(tmp_path),
            )
        import json as _json
        json_path = tmp_path / "2026-04-10" / "greenit-audit-example.com.json"
        data = _json.loads(json_path.read_text())
        assert "score_conformite" in data
        assert "audit_complet" in data

    @pytest.mark.asyncio
    async def test_return_value_is_markdown_with_paths(self, tmp_path):
        fake_pages = [_fake_page_full()]
        with patch("greenit_mcp_final._crawl", new=AsyncMock(return_value=fake_pages)):
            result = await greenit_mcp_final.auditer_url(
                url="https://example.com",
                output_dir=str(tmp_path),
            )
        assert "greenit-audit-example.com.json" in result
        assert "greenit-audit-example.com.md" in result
        assert "greenit-audit-example.com.html" in result

    @pytest.mark.asyncio
    async def test_creates_date_subdir_automatically(self, tmp_path):
        new_dir = tmp_path / "nonexistent"
        fake_pages = [_fake_page_full()]
        with patch("greenit_mcp_final._crawl", new=AsyncMock(return_value=fake_pages)):
            await greenit_mcp_final.auditer_url(
                url="https://example.com",
                output_dir=str(new_dir),
            )
        assert any(new_dir.iterdir())
```

Note: the test uses `"2026-04-10"` as the date directory. If the real implementation uses `datetime.date.today()`, mock it:

```python
# Add to the test or use: monkeypatch.setenv / patch datetime
with patch("greenit_mcp_final.datetime") as mock_dt:
    mock_dt.now.return_value.strftime.return_value = "2026-04-10"
    ...
```

Adjust the test body to patch `datetime` if needed, based on how `greenit_mcp_final.py` gets the date string.

- [ ] **Step 2: Run to verify the test fails**

```bash
cd /Users/renaudheluin/DEV/DEV_GREENIT/refs/mcp-115-greenit
pytest tests/test_tools.py::TestAuditerUrlOutputDir -v
```

Expected: tests fail (wrong behavior — no files written, wrong return format, etc.)

- [ ] **Step 3: Update the import block in `greenit_mcp_final.py`**

Locate the import block around line 34:

```python
# Import local modules
import sys as _sys
_sys.path.insert(0, str(Path(__file__).parent))
from audit_url import crawl as _crawl, build_report as _build_report
from checklist import _build_checklist
```

Replace with:

```python
# Import local modules
import sys as _sys
_sys.path.insert(0, str(Path(__file__).parent))
from audit_url import crawl as _crawl
from checklist import _build_checklist
from report import build_report as _build_report, render_markdown as _render_markdown, render_html as _render_html
```

- [ ] **Step 4: Replace the `auditer_url` tool in `greenit_mcp_final.py`**

Locate the existing `auditer_url` tool (around line 1073). Replace the entire function with:

```python
@mcp.tool()
async def auditer_url(
    url: str,
    max_pages: int = 5,
    output_dir: str = ".",
) -> str:
    """
    Audite un site web et génère un rapport complet d'éco-conception GreenIT.

    Crawle jusqu'à max_pages pages du même domaine, calcule l'EcoIndex par page,
    auto-valide les bonnes pratiques testables, calcule le score de conformité
    sur les 115 fiches du référentiel, et écrit 3 fichiers sur disque.

    Args:
        url:        URL du site à auditer (ex: "https://example.com")
        max_pages:  Nombre maximum de pages à analyser, même domaine (défaut: 5)
        output_dir: Répertoire de sortie pour les fichiers générés (défaut: ".")

    Returns:
        Rapport markdown incluant score de conformité, audit complet des 115 fiches,
        et chemins des 3 fichiers écrits sur disque (.json, .md, .html).
    """
    from urllib.parse import urlparse

    cache = charger_cache()
    pages = await _crawl(url, max_pages=max_pages)
    data  = _build_report(pages, url, cache)
    md    = _render_markdown(data)
    html  = _render_html(data)

    # Write files to disk
    domain   = urlparse(url).netloc or "unknown"
    date_str = datetime.now().strftime("%Y-%m-%d")
    out_dir  = Path(output_dir) / date_str
    out_dir.mkdir(parents=True, exist_ok=True)

    stem = f"greenit-audit-{domain}"
    json_path = out_dir / f"{stem}.json"
    md_path   = out_dir / f"{stem}.md"
    html_path = out_dir / f"{stem}.html"

    import json as _json
    json_path.write_text(_json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(md, encoding="utf-8")
    html_path.write_text(html, encoding="utf-8")

    footer = (
        "\n\n---\n"
        "Rapport sauvegardé :\n"
        f"- `{json_path}`\n"
        f"- `{md_path}`\n"
        f"- `{html_path}`\n"
    )
    return md + footer
```

- [ ] **Step 5: Run to verify the tests pass**

```bash
pytest tests/test_tools.py::TestAuditerUrlOutputDir -v
```

Expected: all 4 tests PASS. If the date mock is needed, adjust the test as described in Step 1.

- [ ] **Step 6: Run the full test suite to check for regressions**

```bash
pytest tests/test_tools.py -v
```

If `TestAuditerUrlTool` (from the existing test suite) fails because it relied on `_build_report` returning a string or the `format` parameter, update those tests to patch `greenit_mcp_final._build_report` and `greenit_mcp_final._render_markdown` instead. The existing tests should not be deleted — just updated to match the new behavior.

- [ ] **Step 7: Commit**

```bash
git add files/greenit_mcp_final.py tests/test_tools.py
git commit -m "feat(audit): auditer_url writes json+md+html to output_dir, adds score_conformite"
```
