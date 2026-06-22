# D1 — Persistance des rapports Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ensure every report-producing tool writes JSON + MD + HTML to disk under `{output_dir}/{YYYY-MM-DD}/greenit-{type}-{domain}.{ext}`.

**Architecture:** D1 is a crosscutting concern fully implemented across two other plans — no new files or functions are needed beyond what A2 and B2 define. This plan maps each spec requirement to its implementing task.

**Tech Stack:** Python 3.11, FastMCP, pytest. No new dependencies.

**Prerequisites:** A2 and B2 must both be implemented.

---

## Coverage Map

| D1 Spec Requirement | Implementing Plan | Task |
|---------------------|-------------------|------|
| `files/report.py` with `render_html` | A2 | Task 1 |
| `auditer_url` — `output_dir` param, 3-file write, footer | A2 | Task 2 |
| `files/remediation.py` with `render_remediation_html` | B2 | Task 2 |
| `planifier_remediations` — `rapport_path`, `output_dir`, 3-file write | B2 | Task 3 |

---

## File Map

All D1 work is distributed across existing plan tasks. No additional files are created.

| File | Plan | Responsibility |
|------|------|----------------|
| `files/report.py` | A2 Task 1 | `build_report`, `render_markdown`, `render_html` for audit reports |
| `files/greenit_mcp_final.py` | A2 Task 2 | `auditer_url` with `output_dir`, 3-file disk write, markdown footer |
| `files/remediation.py` | B2 Task 2 | `render_remediation_markdown`, `render_remediation_html` |
| `files/greenit_mcp_final.py` | B2 Task 3 | `planifier_remediations` with `rapport_path`, `output_dir`, 3-file disk write |

---

## Task 1: Verify D1 requirements are met after A2 + B2

**Context:** After A2 and B2 are implemented, this task verifies the disk-writing policy is complete end-to-end. No code to write — run the relevant tests and confirm file structure.

- [ ] **Step 1: Confirm `auditer_url` disk-writing tests pass**

```bash
cd /Users/renaudheluin/DEV/DEV_GREENIT/refs/mcp-115-greenit
pytest tests/test_tools.py::TestAuditerUrlOutputDir -v
```

Expected: all tests pass, including:
- Three files created under `{output_dir}/{YYYY-MM-DD}/`
- File names match `greenit-audit-{domain}.{json,md,html}`
- Markdown footer lists the three file paths

- [ ] **Step 2: Confirm `planifier_remediations` disk-writing tests pass**

```bash
pytest tests/test_tools.py::TestPlanifierRemediations -v
```

Expected: all tests pass, including:
- Three files created under `{output_dir}/{YYYY-MM-DD}/`
- File names match `greenit-remediation-{domain}.{json,md,html}`
- Markdown footer lists the three file paths
- `rapport_mis_a_jour` in the JSON output is usable as `rapport_path` for the next cycle

- [ ] **Step 3: Run full test suite**

```bash
pytest tests/test_tools.py -v
```

Expected: all existing tests still pass.

- [ ] **Step 4: Commit**

```bash
git commit --allow-empty -m "docs(plan): D1 — persistance rapports crosscutting coverage confirmed"
```

---

## Disk Writing Policy (reference)

Both tools follow the same convention — implemented in their respective plan tasks:

```
{output_dir}/
  {YYYY-MM-DD}/
    greenit-{type}-{domain}.json    ← source de vérité, éditable
    greenit-{type}-{domain}.md      ← lecture humaine
    greenit-{type}-{domain}.html    ← partage / présentation (CSS embarqué)
```

- `{type}` is `audit` for `auditer_url`, `remediation` for `planifier_remediations`
- `{domain}` is extracted via `urllib.parse.urlparse(url).netloc`
- `output_dir` is created automatically if it does not exist (`pathlib.Path.mkdir(parents=True, exist_ok=True)`)
- Existing files in the same dated subdirectory are overwritten
- The tool returns markdown; file paths appear in the footer
