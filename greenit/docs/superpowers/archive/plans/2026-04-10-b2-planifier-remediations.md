# B2 — `planifier_remediations` Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `planifier_remediations` — an MCP tool that reads an audit JSON, re-crawls its pages to verify corrections, and generates a 3-phase remediation plan written to disk as JSON + markdown + HTML.

**Architecture:** Business logic lives in `files/remediation.py` (new). The MCP tool in `greenit_mcp_final.py` is a thin wrapper: reads from `rapport_path`, calls `_crawl` per URL, calls `build_remediation`, renders markdown + HTML, writes 3 files, returns markdown. A prerequisite step adds `get_metric_value` to `checklist.py` so `remediation.py` can extract measured values without duplicating `_METRIC_MAP`.

**Tech Stack:** Python 3.11, FastMCP, pytest. No new dependencies. Requires A1 (checklist.py) and A2 (report.py for `render_html` pattern reference).

**Prerequisite:** A1 must be implemented — `files/checklist.py` must exist with `_auto_validate`, `_METRIC_MAP`, `STATUTS_POSSIBLES`.

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `files/checklist.py` | Modify (add function) | Add `get_metric_value(fiche_id, metrics)` |
| `files/remediation.py` | Create | `_verify_fiches`, `_compute_score`, `_build_phases`, `build_remediation`, `render_remediation_markdown`, `render_remediation_html` |
| `files/greenit_mcp_final.py` | Modify | Add `planifier_remediations` MCP tool; import `remediation` |
| `tests/test_tools.py` | Modify | Add `TestGetMetricValue`, `TestVerifyFiches`, `TestBuildPhases`, `TestBuildRemediation`, `TestPlanifierRemediations` |

---

## Task 1: Add `get_metric_value` to `checklist.py`

**Context:** `checklist.py` has a private `_METRIC_MAP` dict of lambdas used inside `_auto_validate`. `remediation.py` needs to extract the actual measured value (for `valeur_mesuree`) without duplicating that mapping. This task adds a thin public accessor.

**Files:**
- Modify: `files/checklist.py`
- Test: `tests/test_tools.py`

- [ ] **Step 1: Write the failing test**

Add `TestGetMetricValue` at the end of `tests/test_tools.py` (after existing test classes):

```python
# ============================================================================
# checklist — get_metric_value
# ============================================================================

class TestGetMetricValue:
    def test_rweb_0047_returns_requests(self):
        assert checklist.get_metric_value("RWEB_0047", {"requests": 50}) == 50

    def test_rweb_0032_returns_font_count(self):
        assert checklist.get_metric_value("RWEB_0032", {"fonts": ["A", "B"]}) == 2

    def test_unknown_fiche_returns_none(self):
        assert checklist.get_metric_value("RWEB_9999", {"requests": 50}) is None

    def test_missing_metric_key_returns_zero_for_fonts(self):
        # fonts defaults to [] in _METRIC_MAP → len([]) = 0
        assert checklist.get_metric_value("RWEB_0032", {}) == 0

    def test_missing_metric_key_returns_none_for_requests(self):
        # requests not in metrics → dict.get returns None
        assert checklist.get_metric_value("RWEB_0047", {}) is None
```

- [ ] **Step 2: Run to verify the test fails**

```bash
cd /Users/renaudheluin/DEV/DEV_GREENIT/refs/mcp-115-greenit
pytest tests/test_tools.py::TestGetMetricValue -v
```

Expected: `FAILED — AttributeError: module 'checklist' has no attribute 'get_metric_value'`

- [ ] **Step 3: Add `get_metric_value` to `files/checklist.py`**

Append after `_auto_validate` (before `map_metrics_to_fiches`):

```python
def get_metric_value(fiche_id: str, metrics: dict):
    """
    Return the measured metric value for a fiche from the page metrics dict.

    Returns None if the fiche has no metric mapping.
    Uses the same _METRIC_MAP as _auto_validate.

    Used by remediation.py to populate valeur_mesuree during re-verification.
    """
    metric_fn = _METRIC_MAP.get(fiche_id)
    if metric_fn is None:
        return None
    return metric_fn(metrics)
```

- [ ] **Step 4: Run to verify the tests pass**

```bash
pytest tests/test_tools.py::TestGetMetricValue -v
```

Expected: all 5 tests PASS.

- [ ] **Step 5: Run the full test suite to check for regressions**

```bash
pytest tests/test_tools.py -v
```

Expected: all existing tests still PASS.

- [ ] **Step 6: Commit**

```bash
git add files/checklist.py tests/test_tools.py
git commit -m "feat(checklist): add get_metric_value — exposes metric extraction for remediation"
```

---

## Task 2: Create `files/remediation.py`

**Context:** This module contains all business logic for `planifier_remediations`. `_verify_fiches` re-validates auto-testable fiches against re-crawled metrics (first page wins). `_compute_score` tallies the 5 statuts. `_build_phases` splits Non-conforme + Indéterminé fiches into 3 tercile phases with cumulative delta. `build_remediation` orchestrates everything and returns the full structure. `render_remediation_markdown` and `render_remediation_html` produce human-readable output.

**Files:**
- Create: `files/remediation.py`
- Test: `tests/test_tools.py`

- [ ] **Step 1: Write the failing tests**

Add the following classes at the end of `tests/test_tools.py`. Note: `remediation` is imported under a `sys.path` already set up by the test infrastructure (same `files/` dir as `checklist`).

```python
# ============================================================================
# remediation — _verify_fiches, _compute_score, _build_phases, build_remediation
# ============================================================================

import sys as _sys
import os as _os
_sys.path.insert(0, _os.path.join(_os.path.dirname(__file__), "..", "files"))
import remediation


class TestVerifyFiches:
    @pytest.fixture
    def fiche_auto(self):
        """Auto-testable fiche (has max_value for RWEB_0047 = requests ≤ 40)."""
        return {
            "id": "RWEB_0047",
            "titre": "Limiter les requêtes",
            "lifecycle": "3-developement",
            "url": "https://rweb.greenit.fr/fr/fiches/0047",
            "validation_rule": "de requêtes HTTP",
            "max_value": "40",
            "valeur_mesuree": 65,
            "statut": "Non-conforme",
            "environmental_impact": 4,
            "priority_implementation": 4,
        }

    @pytest.fixture
    def fiche_manual(self):
        """Non-auto-testable fiche (no METRIC_MAP entry). Manual statut."""
        return {
            "id": "RWEB_0081",
            "titre": "Cache HTTP",
            "lifecycle": "4-production",
            "url": "https://rweb.greenit.fr/fr/fiches/0081",
            "validation_rule": None,
            "max_value": None,
            "valeur_mesuree": None,
            "statut": "Conforme",
            "environmental_impact": 4,
            "priority_implementation": 3,
        }

    @pytest.fixture
    def metrics_conforme(self):
        return {"url": "https://example.com", "requests": 30, "fonts": []}

    @pytest.fixture
    def metrics_non_conforme(self):
        return {"url": "https://example.com", "requests": 55, "fonts": []}

    def test_auto_testable_fiche_overridden_to_conforme(self, fiche_auto, metrics_conforme):
        result = remediation._verify_fiches([fiche_auto], [metrics_conforme])
        assert result[0]["statut"] == "Conforme"
        assert result[0]["valeur_mesuree"] == 30
        assert result[0]["correction_verifiee"] is True

    def test_auto_testable_fiche_still_non_conforme(self, fiche_auto, metrics_non_conforme):
        result = remediation._verify_fiches([fiche_auto], [metrics_non_conforme])
        assert result[0]["statut"] == "Non-conforme"
        assert result[0]["valeur_mesuree"] == 55
        assert result[0]["correction_verifiee"] is False

    def test_manual_fiche_keeps_statut(self, fiche_manual, metrics_conforme):
        result = remediation._verify_fiches([fiche_manual], [metrics_conforme])
        assert result[0]["statut"] == "Conforme"
        assert result[0]["correction_verifiee"] is None

    def test_manual_fiche_keeps_valeur_mesuree(self, fiche_manual, metrics_conforme):
        result = remediation._verify_fiches([fiche_manual], [metrics_conforme])
        assert result[0]["valeur_mesuree"] is None

    def test_first_page_wins_for_auto_testable(self, fiche_auto):
        pages = [
            {"url": "https://example.com", "requests": 30, "fonts": []},   # Conforme
            {"url": "https://example.com/about", "requests": 55, "fonts": []},  # Non-conforme
        ]
        result = remediation._verify_fiches([fiche_auto], pages)
        # First page (30 requests ≤ 40) wins
        assert result[0]["statut"] == "Conforme"
        assert result[0]["valeur_mesuree"] == 30

    def test_no_pages_gives_correction_verifiee_none(self, fiche_auto):
        result = remediation._verify_fiches([fiche_auto], [])
        assert result[0]["correction_verifiee"] is None
        assert result[0]["statut"] == "Non-conforme"  # original statut preserved

    def test_does_not_mutate_input(self, fiche_auto, metrics_conforme):
        original_statut = fiche_auto["statut"]
        remediation._verify_fiches([fiche_auto], [metrics_conforme])
        assert fiche_auto["statut"] == original_statut  # input not mutated


class TestComputeScore:
    def _fiches(self, statuts):
        return [{"statut": s, "id": f"RWEB_{i:04d}"} for i, s in enumerate(statuts)]

    def test_score_pct(self):
        fiches = self._fiches(["Conforme"] * 14 + ["Non-conforme"] * 101)
        result = remediation._compute_score(fiches)
        assert result["score_pct"] == round(14 / 115 * 100, 1)

    def test_all_counts_sum_to_total(self):
        fiches = self._fiches(["Conforme", "Non-conforme", "Non-applicable", "Indéterminé", "Non-testé"])
        result = remediation._compute_score(fiches)
        assert (
            result["conforme"] + result["non_conforme"] + result["non_applicable"]
            + result["indetermine"] + result["non_teste"]
            == result["total"]
        )

    def test_total_equals_fiche_count(self):
        fiches = self._fiches(["Conforme", "Non-conforme", "Non-testé"])
        result = remediation._compute_score(fiches)
        assert result["total"] == 3


class TestBuildPhases:
    def _fiche(self, fiche_id, statut, ei, pi):
        return {
            "id": fiche_id,
            "titre": f"Fiche {fiche_id}",
            "lifecycle": "3-developement",
            "url": "https://rweb.greenit.fr",
            "validation_rule": None,
            "max_value": None,
            "valeur_mesuree": None,
            "statut": statut,
            "environmental_impact": ei,
            "priority_implementation": pi,
            "correction_verifiee": False,
        }

    def test_three_phases_always_returned(self):
        fiches = [self._fiche(f"RWEB_{i:04d}", "Non-conforme", 3, 2) for i in range(6)]
        phases = remediation._build_phases(fiches, score_apres_conforme=10, total=115)
        assert len(phases) == 3

    def test_non_conforme_and_indetermine_included(self):
        fiches = [
            self._fiche("RWEB_0001", "Non-conforme", 4, 2),
            self._fiche("RWEB_0002", "Indéterminé", 3, 2),
            self._fiche("RWEB_0003", "Conforme", 5, 1),   # excluded
            self._fiche("RWEB_0004", "Non-testé", 4, 1),  # excluded
        ]
        phases = remediation._build_phases(fiches, score_apres_conforme=10, total=115)
        total_fiches = sum(p["delta"]["fiches_a_corriger"] for p in phases)
        assert total_fiches == 2

    def test_sorted_by_priority_score(self):
        fiches = [
            self._fiche("RWEB_0001", "Non-conforme", 2, 4),  # score = 2*2-4 = 0
            self._fiche("RWEB_0002", "Non-conforme", 5, 1),  # score = 5*2-1 = 9
            self._fiche("RWEB_0003", "Non-conforme", 3, 2),  # score = 3*2-2 = 4
        ]
        phases = remediation._build_phases(fiches, score_apres_conforme=10, total=115)
        all_fiches = [f for p in phases for f in p["fiches"]]
        scores = [f["score"] for f in all_fiches]
        assert scores == sorted(scores, reverse=True)

    def test_delta_is_cumulative(self):
        # 3 fiches → phase1=1, phase2=1, phase3=1
        fiches = [self._fiche(f"RWEB_{i:04d}", "Non-conforme", 3, 1) for i in range(3)]
        phases = remediation._build_phases(fiches, score_apres_conforme=10, total=100)
        # score_base = 10/100 = 10%
        # phase1: (10+1)/100 = 11%
        # phase2: (10+2)/100 = 12%
        # phase3: (10+3)/100 = 13%
        assert phases[0]["delta"]["score_apres"] == 11.0
        assert phases[1]["delta"]["score_apres"] == 12.0
        assert phases[2]["delta"]["score_apres"] == 13.0

    def test_phase_labels(self):
        fiches = [self._fiche(f"RWEB_{i:04d}", "Non-conforme", 3, 2) for i in range(3)]
        phases = remediation._build_phases(fiches, score_apres_conforme=10, total=100)
        labels = [p["label"] for p in phases]
        assert labels == ["Court terme", "Moyen terme", "Long terme"]

    def test_each_fiche_has_score_field(self):
        fiches = [self._fiche("RWEB_0001", "Non-conforme", 4, 2)]
        phases = remediation._build_phases(fiches, score_apres_conforme=10, total=100)
        fiche = phases[0]["fiches"][0]
        assert fiche["score"] == 4 * 2 - 2  # = 6


class TestBuildRemediation:
    @pytest.fixture
    def mock_rapport(self):
        return {
            "pages": [{"url": "https://example.com", "requests": 30, "fonts": []}],
            "score_conformite": {
                "score_pct": 50.0,
                "conforme": 1,
                "non_conforme": 1,
                "non_applicable": 0,
                "indetermine": 0,
                "non_teste": 0,
                "total": 2,
            },
            "audit_complet": [
                {
                    "id": "RWEB_0047",
                    "titre": "Limiter les requêtes",
                    "lifecycle": "3-developement",
                    "url": "https://rweb.greenit.fr/fr/fiches/0047",
                    "validation_rule": "de requêtes HTTP",
                    "max_value": "40",
                    "valeur_mesuree": 65,
                    "statut": "Non-conforme",
                    "environmental_impact": 4,
                    "priority_implementation": 4,
                },
                {
                    "id": "RWEB_0081",
                    "titre": "Cache HTTP",
                    "lifecycle": "4-production",
                    "url": "https://rweb.greenit.fr/fr/fiches/0081",
                    "validation_rule": None,
                    "max_value": None,
                    "valeur_mesuree": None,
                    "statut": "Conforme",
                    "environmental_impact": 4,
                    "priority_implementation": 3,
                },
            ],
        }

    def test_top_level_keys_present(self, mock_rapport):
        result = remediation.build_remediation(mock_rapport, [])
        for key in ("pages_verifiees", "score_apres_verification", "corrections_verifiees",
                    "total_a_remedier", "phases", "rapport_mis_a_jour"):
            assert key in result, f"Missing key: {key}"

    def test_score_original_absent_when_no_pages(self, mock_rapport):
        result = remediation.build_remediation(mock_rapport, [])
        assert "score_original" not in result

    def test_score_original_present_when_pages_given(self, mock_rapport):
        pages_metrics = [{"url": "https://example.com", "requests": 30, "fonts": []}]
        result = remediation.build_remediation(mock_rapport, pages_metrics)
        assert "score_original" in result
        assert result["score_original"]["score_pct"] == 50.0

    def test_auto_testable_fiche_re_verified(self, mock_rapport):
        pages_metrics = [{"url": "https://example.com", "requests": 30, "fonts": []}]
        result = remediation.build_remediation(mock_rapport, pages_metrics)
        rapport_updated = result["rapport_mis_a_jour"]
        fiche = next(f for f in rapport_updated["audit_complet"] if f["id"] == "RWEB_0047")
        assert fiche["statut"] == "Conforme"

    def test_rapport_mis_a_jour_has_required_keys(self, mock_rapport):
        result = remediation.build_remediation(mock_rapport, [])
        rmu = result["rapport_mis_a_jour"]
        assert "pages" in rmu
        assert "score_conformite" in rmu
        assert "audit_complet" in rmu

    def test_rapport_mis_a_jour_audit_no_correction_verifiee(self, mock_rapport):
        result = remediation.build_remediation(mock_rapport, [])
        for fiche in result["rapport_mis_a_jour"]["audit_complet"]:
            assert "correction_verifiee" not in fiche

    def test_three_phases(self, mock_rapport):
        result = remediation.build_remediation(mock_rapport, [])
        assert len(result["phases"]) == 3
```

- [ ] **Step 2: Run to verify the tests fail**

```bash
cd /Users/renaudheluin/DEV/DEV_GREENIT/refs/mcp-115-greenit
pytest tests/test_tools.py::TestVerifyFiches tests/test_tools.py::TestComputeScore tests/test_tools.py::TestBuildPhases tests/test_tools.py::TestBuildRemediation -v
```

Expected: `ModuleNotFoundError: No module named 'remediation'`

- [ ] **Step 3: Create `files/remediation.py`**

```python
"""
GreenIT remediation — re-verification and remediation plan generation.

Provides:
  - _verify_fiches(audit_complet, pages_metrics): re-validate auto-testable fiches
  - _compute_score(fiches): tally statuts into a score dict
  - _build_phases(verified, score_base_conforme, total): 3-phase tercile plan with cumulative delta
  - build_remediation(rapport, pages_metrics): full remediation plan dict
  - render_remediation_markdown(data): markdown string
  - render_remediation_html(data): self-contained HTML string

Used by: planifier_remediations (greenit_mcp_final.py)
"""

from __future__ import annotations

import math
from checklist import _auto_validate, get_metric_value


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------


def _verify_fiches(audit_complet: list, pages_metrics_list: list) -> list:
    """
    Re-verify fiches against re-crawled page metrics.

    For each fiche:
    - Auto-testable (has max_value AND fiche_id in _METRIC_MAP): uses "first page wins"
      to determine statut. Sets correction_verifiee to True (Conforme) or False (Non-conforme).
    - Non-testable: keeps the manual statut from audit_complet. Sets correction_verifiee to None.

    Does not mutate input dicts.
    Returns a new list with correction_verifiee added to each fiche.
    """
    result = []
    for fiche in audit_complet:
        fiche_id = fiche["id"]
        max_value = fiche.get("max_value")

        new_statut = None
        new_valeur = None
        for page_metrics in pages_metrics_list:
            statut = _auto_validate(fiche_id, max_value, page_metrics)
            if statut != "Non-testé":
                new_statut = statut
                new_valeur = get_metric_value(fiche_id, page_metrics)
                break

        if new_statut is not None:
            result.append({
                **fiche,
                "statut": new_statut,
                "valeur_mesuree": new_valeur,
                "correction_verifiee": new_statut == "Conforme",
            })
        else:
            result.append({
                **fiche,
                "correction_verifiee": None,
            })

    return result


# ---------------------------------------------------------------------------
# Score
# ---------------------------------------------------------------------------


def _compute_score(fiches: list) -> dict:
    """
    Tally fiche statuts into a score dict.

    Returns: {score_pct, conforme, non_conforme, non_applicable, indetermine, non_teste, total}
    """
    counts = {"Conforme": 0, "Non-conforme": 0, "Non-applicable": 0, "Indéterminé": 0, "Non-testé": 0}
    for f in fiches:
        s = f.get("statut", "Non-testé")
        if s in counts:
            counts[s] += 1
    total = len(fiches)
    conforme = counts["Conforme"]
    return {
        "score_pct": round(conforme / total * 100, 1) if total else 0.0,
        "conforme": conforme,
        "non_conforme": counts["Non-conforme"],
        "non_applicable": counts["Non-applicable"],
        "indetermine": counts["Indéterminé"],
        "non_teste": counts["Non-testé"],
        "total": total,
    }


# ---------------------------------------------------------------------------
# Phases
# ---------------------------------------------------------------------------


def _build_phases(verified_fiches: list, score_apres_conforme: int, total: int) -> list:
    """
    Build 3 remediation phases (terciles) from Non-conforme and Indéterminé fiches.

    Fiches sorted by score = environmental_impact * 2 - priority_implementation descending.
    Delta is cumulative: each phase's score_apres assumes all prior phases were corrected.

    Returns a list of 3 phase dicts (Court terme / Moyen terme / Long terme).
    """
    a_remedier = [
        f for f in verified_fiches
        if f.get("statut") in ("Non-conforme", "Indéterminé")
    ]
    a_remedier.sort(
        key=lambda f: f["environmental_impact"] * 2 - f["priority_implementation"],
        reverse=True,
    )

    n = len(a_remedier)
    size1 = math.ceil(n / 3)
    size2 = math.ceil((n - size1) / 2)
    size3 = n - size1 - size2

    splits = [
        (1, "Court terme", a_remedier[:size1]),
        (2, "Moyen terme", a_remedier[size1:size1 + size2]),
        (3, "Long terme", a_remedier[size1 + size2:]),
    ]

    phases = []
    prev_score_pct = round(score_apres_conforme / total * 100, 1) if total else 0.0
    cumul_conforme = score_apres_conforme

    for phase_num, label, fiches in splits:
        cumul_conforme += len(fiches)
        score_apres = round(cumul_conforme / total * 100, 1) if total else 0.0
        gain_pct = round(score_apres - prev_score_pct, 1)
        prev_score_pct = score_apres

        phases.append({
            "phase": phase_num,
            "label": label,
            "delta": {
                "fiches_a_corriger": len(fiches),
                "score_apres": score_apres,
                "gain_pct": gain_pct,
            },
            "fiches": [
                {
                    **{k: v for k, v in f.items() if k != "correction_verifiee"},
                    "score": f["environmental_impact"] * 2 - f["priority_implementation"],
                    "correction_verifiee": f.get("correction_verifiee"),
                }
                for f in fiches
            ],
        })

    return phases


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def build_remediation(rapport: dict, pages_metrics_list: list) -> dict:
    """
    Build the full remediation plan from an audit rapport and re-crawled metrics.

    Args:
        rapport: dict loaded from a greenit-audit-{domain}.json file
        pages_metrics_list: list of page metric dicts from re-crawl (may be empty)

    Returns:
        Full plan dict matching the B2 spec structure.
        score_original is absent when pages_metrics_list is empty.
    """
    audit_complet = rapport.get("audit_complet", [])
    verified = _verify_fiches(audit_complet, pages_metrics_list)

    score_dict = _compute_score(verified)
    score_apres = {
        "score_pct": score_dict["score_pct"],
        "conforme": score_dict["conforme"],
        "total": score_dict["total"],
    }

    verifiable = [f for f in verified if f["correction_verifiee"] is not None]
    corrigees = sum(1 for f in verifiable if f["correction_verifiee"])
    encore_non_conformes = sum(1 for f in verifiable if not f["correction_verifiee"])
    non_testables = sum(1 for f in verified if f["correction_verifiee"] is None)

    phases = _build_phases(verified, score_dict["conforme"], score_dict["total"])
    total_a_remedier = sum(p["delta"]["fiches_a_corriger"] for p in phases)

    rapport_mis_a_jour = {
        "pages": rapport.get("pages", []),
        "score_conformite": score_dict,
        "audit_complet": [
            {k: v for k, v in f.items() if k != "correction_verifiee"}
            for f in verified
        ],
    }

    result = {
        "pages_verifiees": [p["url"] for p in pages_metrics_list],
        "score_apres_verification": score_apres,
        "corrections_verifiees": {
            "corrigees": corrigees,
            "encore_non_conformes": encore_non_conformes,
            "non_testables_en_front": non_testables,
        },
        "total_a_remedier": total_a_remedier,
        "phases": phases,
        "rapport_mis_a_jour": rapport_mis_a_jour,
    }

    if pages_metrics_list:
        sc = rapport.get("score_conformite", {})
        result["score_original"] = {
            "score_pct": sc.get("score_pct", 0.0),
            "conforme": sc.get("conforme", 0),
            "total": sc.get("total", 0),
        }
        # Insert score_original before score_apres_verification
        result = {
            "pages_verifiees": result["pages_verifiees"],
            "score_original": result["score_original"],
            **{k: v for k, v in result.items() if k not in ("pages_verifiees", "score_original")},
        }

    return result


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def render_remediation_markdown(data: dict) -> str:
    """Render a remediation plan dict as a markdown string."""
    lines = ["# Plan de remédiation GreenIT\n"]

    if "score_original" in data:
        so = data["score_original"]
        sav = data["score_apres_verification"]
        lines.append(f"**Score original :** {so['score_pct']}% ({so['conforme']}/{so['total']} fiches conformes)")
        lines.append(f"**Score après vérification :** {sav['score_pct']}% ({sav['conforme']}/{sav['total']} fiches conformes)\n")
    else:
        sav = data["score_apres_verification"]
        lines.append(f"**Score :** {sav['score_pct']}% ({sav['conforme']}/{sav['total']} fiches conformes)\n")

    cv = data["corrections_verifiees"]
    lines.append(f"**Corrections vérifiées :** {cv['corrigees']} corrigées, "
                 f"{cv['encore_non_conformes']} encore non-conformes, "
                 f"{cv['non_testables_en_front']} non-testables en front\n")

    lines.append(f"**Total à remédier :** {data['total_a_remedier']} fiches\n")

    for phase in data["phases"]:
        delta = phase["delta"]
        lines.append(f"## Phase {phase['phase']} — {phase['label']}")
        lines.append(
            f"*{delta['fiches_a_corriger']} fiches · "
            f"Score après correction : {delta['score_apres']}% (+{delta['gain_pct']}%)*\n"
        )
        lines.append("| ID | Titre | Impact | Effort | Score | Statut |")
        lines.append("|----|----|----|----|----|----|")
        for f in phase["fiches"]:
            lines.append(
                f"| {f['id']} | {f['titre']} | {f['environmental_impact']} "
                f"| {f['priority_implementation']} | {f['score']} | {f['statut']} |"
            )
        lines.append("")

    return "\n".join(lines)


def render_remediation_html(data: dict) -> str:
    """Render a remediation plan dict as a self-contained HTML string."""
    sav = data["score_apres_verification"]
    score_pct = sav["score_pct"]

    phase_rows = ""
    for phase in data["phases"]:
        delta = phase["delta"]
        phase_rows += (
            f"<h2>Phase {phase['phase']} — {phase['label']}</h2>"
            f"<p>{delta['fiches_a_corriger']} fiches · Score après correction : "
            f"{delta['score_apres']}% (+{delta['gain_pct']}%)</p>"
            "<table><thead><tr><th>ID</th><th>Titre</th><th>Impact</th><th>Effort</th>"
            "<th>Score</th><th>Statut</th></tr></thead><tbody>"
        )
        for f in phase["fiches"]:
            phase_rows += (
                f"<tr><td>{f['id']}</td><td>{f['titre']}</td>"
                f"<td>{f['environmental_impact']}</td><td>{f['priority_implementation']}</td>"
                f"<td>{f['score']}</td><td>{f['statut']}</td></tr>"
            )
        phase_rows += "</tbody></table>"

    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Plan de remédiation GreenIT</title>
<style>
body{{font-family:system-ui,sans-serif;max-width:960px;margin:0 auto;padding:2rem;color:#1a1a1a}}
h1{{color:#2d7a2d}}h2{{color:#3a6ea5;margin-top:2rem}}
table{{border-collapse:collapse;width:100%;margin:1rem 0}}
th,td{{border:1px solid #ddd;padding:8px 12px;text-align:left}}
th{{background:#f4f4f4}}
.score{{font-size:2rem;font-weight:bold;color:#2d7a2d}}
</style>
</head>
<body>
<h1>Plan de remédiation GreenIT</h1>
<p>Score après vérification : <span class="score">{score_pct}%</span>
({sav['conforme']}/{sav['total']} fiches conformes)</p>
{phase_rows}
</body>
</html>"""
```

- [ ] **Step 4: Run to verify the tests pass**

```bash
pytest tests/test_tools.py::TestVerifyFiches tests/test_tools.py::TestComputeScore tests/test_tools.py::TestBuildPhases tests/test_tools.py::TestBuildRemediation -v
```

Expected: all tests PASS.

- [ ] **Step 5: Run the full test suite to check for regressions**

```bash
pytest tests/test_tools.py -v
```

Expected: all existing tests still PASS.

- [ ] **Step 6: Commit**

```bash
git add files/remediation.py tests/test_tools.py
git commit -m "feat(remediation): add _verify_fiches, _build_phases, build_remediation, render functions"
```

---

## Task 3: Add `planifier_remediations` MCP tool

**Context:** `files/greenit_mcp_final.py` has `_crawl` imported from `audit_url`. This task adds the `planifier_remediations` tool that reads `rapport_path` from disk, re-crawls each URL in `rapport["pages"]`, delegates to `remediation.build_remediation`, writes 3 files to `{output_dir}/{YYYY-MM-DD}/greenit-remediation-{domain}.{json,md,html}`, and returns markdown + footer. The domain is extracted from the first page URL.

**Files:**
- Modify: `files/greenit_mcp_final.py`
- Test: `tests/test_tools.py`

- [ ] **Step 1: Write the failing test**

Add `TestPlanifierRemediations` at the end of `tests/test_tools.py` (after `TestBuildRemediation`):

```python
# ============================================================================
# greenit_mcp_final — planifier_remediations
# ============================================================================

class TestPlanifierRemediations:
    @pytest.fixture
    def audit_json(self, tmp_path):
        """Minimal valid audit JSON on disk."""
        rapport = {
            "pages": [],
            "score_conformite": {
                "score_pct": 50.0,
                "conforme": 1,
                "non_conforme": 1,
                "non_applicable": 0,
                "indetermine": 0,
                "non_teste": 0,
                "total": 2,
            },
            "audit_complet": [
                {
                    "id": "RWEB_0047",
                    "titre": "Limiter les requêtes",
                    "lifecycle": "3-developement",
                    "url": "https://rweb.greenit.fr/fr/fiches/0047",
                    "validation_rule": "de requêtes HTTP",
                    "max_value": "40",
                    "valeur_mesuree": 65,
                    "statut": "Non-conforme",
                    "environmental_impact": 4,
                    "priority_implementation": 4,
                },
                {
                    "id": "RWEB_0081",
                    "titre": "Cache HTTP",
                    "lifecycle": "4-production",
                    "url": "https://rweb.greenit.fr/fr/fiches/0081",
                    "validation_rule": None,
                    "max_value": None,
                    "valeur_mesuree": None,
                    "statut": "Conforme",
                    "environmental_impact": 4,
                    "priority_implementation": 3,
                },
            ],
        }
        p = tmp_path / "greenit-audit-example.com.json"
        p.write_text(json.dumps(rapport))
        return str(p)

    def test_creates_three_output_files(self, audit_json, tmp_path, monkeypatch):
        monkeypatch.setattr(greenit_mcp_final, "_crawl", lambda url, max_pages: [])
        output_dir = str(tmp_path / "out")
        greenit_mcp_final.planifier_remediations(rapport_path=audit_json, output_dir=output_dir)
        from pathlib import Path
        files = list(Path(output_dir).rglob("greenit-remediation-*"))
        exts = {f.suffix for f in files}
        assert ".json" in exts
        assert ".md" in exts
        assert ".html" in exts

    def test_json_output_has_phases(self, audit_json, tmp_path, monkeypatch):
        monkeypatch.setattr(greenit_mcp_final, "_crawl", lambda url, max_pages: [])
        output_dir = str(tmp_path / "out")
        greenit_mcp_final.planifier_remediations(rapport_path=audit_json, output_dir=output_dir)
        from pathlib import Path
        json_files = list(Path(output_dir).rglob("*.json"))
        assert json_files
        data = json.loads(json_files[0].read_text())
        assert "phases" in data
        assert len(data["phases"]) == 3

    def test_return_value_contains_file_paths(self, audit_json, tmp_path, monkeypatch):
        monkeypatch.setattr(greenit_mcp_final, "_crawl", lambda url, max_pages: [])
        output_dir = str(tmp_path / "out")
        result = greenit_mcp_final.planifier_remediations(rapport_path=audit_json, output_dir=output_dir)
        assert ".json" in result
        assert ".md" in result
        assert ".html" in result

    def test_creates_output_dir_automatically(self, audit_json, tmp_path, monkeypatch):
        monkeypatch.setattr(greenit_mcp_final, "_crawl", lambda url, max_pages: [])
        output_dir = str(tmp_path / "does" / "not" / "exist")
        greenit_mcp_final.planifier_remediations(rapport_path=audit_json, output_dir=output_dir)
        from pathlib import Path
        assert any(Path(output_dir).rglob("greenit-remediation-*"))

    def test_rapport_mis_a_jour_in_json(self, audit_json, tmp_path, monkeypatch):
        monkeypatch.setattr(greenit_mcp_final, "_crawl", lambda url, max_pages: [])
        output_dir = str(tmp_path / "out")
        greenit_mcp_final.planifier_remediations(rapport_path=audit_json, output_dir=output_dir)
        from pathlib import Path
        json_files = list(Path(output_dir).rglob("*.json"))
        data = json.loads(json_files[0].read_text())
        assert "rapport_mis_a_jour" in data
        assert "audit_complet" in data["rapport_mis_a_jour"]
```

- [ ] **Step 2: Run to verify the tests fail**

```bash
cd /Users/renaudheluin/DEV/DEV_GREENIT/refs/mcp-115-greenit
pytest tests/test_tools.py::TestPlanifierRemediations -v
```

Expected: `FAILED — AttributeError: module 'greenit_mcp_final' has no attribute 'planifier_remediations'`

- [ ] **Step 3: Add `remediation` import to `greenit_mcp_final.py`**

In `files/greenit_mcp_final.py`, locate the existing local import block:

```python
# Import local modules
import sys as _sys
_sys.path.insert(0, str(Path(__file__).parent))
from audit_url import crawl as _crawl
from checklist import _build_checklist
from report import build_report as _build_report, render_markdown as _render_markdown, render_html as _render_html
```

Replace with:

```python
# Import local modules
import sys as _sys
_sys.path.insert(0, str(Path(__file__).parent))
from audit_url import crawl as _crawl
from checklist import _build_checklist
from report import build_report as _build_report, render_markdown as _render_markdown, render_html as _render_html
from remediation import (
    build_remediation as _build_remediation,
    render_remediation_markdown as _render_remediation_markdown,
    render_remediation_html as _render_remediation_html,
)
```

Note: if the import block looks different at implementation time (A2 may not be done yet), add only the `from remediation import ...` line alongside the existing imports.

- [ ] **Step 4: Add `planifier_remediations` tool to `greenit_mcp_final.py`**

Locate `obtenir_checklist_audit` or `auditer_url` in `files/greenit_mcp_final.py`. Insert `planifier_remediations` immediately before `auditer_url`:

```python
@mcp.tool()
def planifier_remediations(
    rapport_path: str,
    output_dir: str = ".",
    inclure_toutes: bool = False,
) -> str:
    """
    Re-crawle les pages d'un audit et génère un plan de remédiation en 3 phases.

    Lit le rapport JSON produit par auditer_url ou un appel précédent de
    planifier_remediations. Re-crawle automatiquement les pages pour vérifier
    les corrections front-end. Accepte un fichier JSON édité manuellement.

    Args:
        rapport_path: Chemin vers le fichier JSON produit par auditer_url
                      ou un appel précédent de planifier_remediations.
        output_dir: Répertoire de sortie (défaut : répertoire courant).
                    Créé automatiquement si inexistant.
        inclure_toutes: Si True, inclut deja_conforme et a_tester dans la sortie.

    Returns:
        Plan de remédiation en markdown avec les chemins des fichiers écrits en pied.
    """
    import json as _json_local
    from pathlib import Path as _Path_local
    from urllib.parse import urlparse as _urlparse
    from datetime import datetime as _datetime

    with open(rapport_path, encoding="utf-8") as f:
        rapport = _json_local.load(f)

    urls = [p["url"] for p in rapport.get("pages", [])]
    pages_metrics: list = []
    for url in urls:
        pages_metrics.extend(_crawl(url, max_pages=1))

    result = _build_remediation(rapport, pages_metrics)

    if inclure_toutes:
        verified = {
            f["id"]: f
            for f in result["rapport_mis_a_jour"]["audit_complet"]
        }
        # correction_verifiee is stripped from rapport_mis_a_jour — rebuild from pages_metrics
        from remediation import _verify_fiches as _vf
        verified_with_cv = _vf(rapport.get("audit_complet", []), pages_metrics)
        cv_map = {f["id"]: f.get("correction_verifiee") for f in verified_with_cv}
        result["deja_conforme"] = [
            {
                "id": f["id"],
                "titre": f["titre"],
                "environmental_impact": f["environmental_impact"],
                "priority_implementation": f["priority_implementation"],
                "correction_verifiee": cv_map.get(f["id"]),
            }
            for f in result["rapport_mis_a_jour"]["audit_complet"]
            if f["statut"] == "Conforme"
        ]
        result["a_tester"] = [
            {
                "id": f["id"],
                "titre": f["titre"],
                "environmental_impact": f["environmental_impact"],
                "max_value": f.get("max_value"),
                "correction_verifiee": None,
            }
            for f in result["rapport_mis_a_jour"]["audit_complet"]
            if f["statut"] == "Non-testé"
        ]

    domain = _urlparse(urls[0]).netloc if urls else "unknown"
    date_str = _datetime.now().strftime("%Y-%m-%d")
    out_dir = _Path_local(output_dir) / date_str
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = f"greenit-remediation-{domain}"

    json_path = out_dir / f"{stem}.json"
    md_path = out_dir / f"{stem}.md"
    html_path = out_dir / f"{stem}.html"

    md = _render_remediation_markdown(result)
    html = _render_remediation_html(result)

    json_path.write_text(_json_local.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(md, encoding="utf-8")
    html_path.write_text(html, encoding="utf-8")

    footer = (
        "\n\n---\nRapport sauvegardé :\n"
        f"- `{json_path}`\n"
        f"- `{md_path}`\n"
        f"- `{html_path}`"
    )
    return md + footer


```

- [ ] **Step 5: Run to verify the tests pass**

```bash
pytest tests/test_tools.py::TestPlanifierRemediations -v
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
git commit -m "feat(mcp): add planifier_remediations tool — re-crawl, 3-phase plan, disk output"
```
