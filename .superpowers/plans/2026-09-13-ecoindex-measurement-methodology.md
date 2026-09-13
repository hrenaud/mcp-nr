# EcoIndex Measurement Methodology Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a discoverable, structured, normative EcoIndex collection methodology and return calculator results as dictionaries.

**Architecture:** Keep browser collection outside the server and expose its exact rules through a parameterless read-only MCP tool. Keep `greenit_calculer_ecoindex` limited to its existing raw metrics and optional contextual URL, but return structured Python data instead of serialized JSON.

**Tech Stack:** Python 3.11, FastMCP, pytest, browser JavaScript Performance API

## Global Constraints

- `greenit_obtenir_methodologie_ecoindex` is the only normalized measurement method for comparable MCP EcoIndex scores.
- Count descendants of `document.body` without counting `body` itself.
- Recurse into open Shadow DOM roots and disclose that closed roots are not observable.
- Exclude only elements whose direct parent is an `<svg>`.
- Do not use Lighthouse or add a browser dependency to the server.
- Do not add measurement parameters to `greenit_calculer_ecoindex`.

---

### Task 1: Structured calculator response

**Files:**
- Modify: `greenit/tests/test_tools.py`
- Modify: `greenit/files/greenit_mcp.py`

**Interfaces:**
- Consumes: `_calculer_ecoindex_impl(dom_nodes: int, requests: int, size_kb: float) -> dict`
- Produces: `greenit_calculer_ecoindex(dom_nodes: int, requests: int, size_kb: float, url: str = "") -> dict`

- [ ] Add a test asserting `isinstance(greenit_calculer_ecoindex(...), dict)` and update calculator assertions to consume the dictionary directly.
- [ ] Run `pytest ../tests/test_tools.py -v -k "CalculerEcoindex"` from `greenit/files` and verify failure on the serialized string.
- [ ] Change the return annotation to `dict` and return the result mapping directly. Keep the three metric arguments and optional URL unchanged.
- [ ] Run the focused tests and verify they pass.

### Task 2: Normative methodology tool

**Files:**
- Modify: `greenit/tests/test_tools.py`
- Modify: `greenit/tests/test_routes_http.py`
- Modify: `greenit/tests/test_docker_integration.py`
- Modify: `greenit/files/greenit_mcp.py`

**Interfaces:**
- Produces: `greenit_obtenir_methodologie_ecoindex() -> dict`
- Returns: normative status, collection sequence, metric rules and limits, and `browser_javascript`.

- [ ] Add tests asserting registration, read-only annotations, a dictionary response, and an output schema.
- [ ] Assert the response says this is the only normalized MCP method and requires it for comparable scores.
- [ ] Assert the JavaScript contains `document.body`, `element.shadowRoot`, `element.parentElement?.localName !== "svg"`, Resource Timing entries, `transferSize`, and no Lighthouse dependency.
- [ ] Assert limits mention closed Shadow DOM, cache, and `Timing-Allow-Origin`.
- [ ] Update expected tool sets and counts from 9 to 10, then run the focused tests and verify they fail because the tool is absent.
- [ ] Implement the parameterless tool with a complete output schema and read-only, non-destructive, idempotent annotations.
- [ ] Update the calculator description to direct agents to the methodology tool and summarize the normalized DOM rule.
- [ ] Run the focused tool and route tests and verify they pass.

### Task 3: Documentation and skill alignment

**Files:**
- Modify: `greenit/README.md`
- Modify: `greenit/docs/GUIDE_DEVELOPPEMENT.md`
- Modify: `OUTILS.md`
- Modify: `greenit/CHANGELOG.md`
- Modify: `CHANGELOG.md`
- Modify: `~/.claude/skills/ecoconception-evaluation-ecoindex/SKILL.md`

**Interfaces:**
- Consumes: `greenit_obtenir_methodologie_ecoindex() -> dict`
- Produces: one documented source of truth with no competing skill formula.

- [ ] Add the methodology tool to both tool inventories and change their count to 10.
- [ ] Document the exact DOM, request, and transfer-size rules, full browser JavaScript, measurement limits, and comparability requirement in the GreenIT README and development guide.
- [ ] Update the HTTP guide to identify the methodology tool as the only normalized source and remove the older divergent DOM script.
- [ ] Add `[Unreleased]` changelog entries for the new tool and structured calculator response.
- [ ] Change the local EcoIndex skill workflow to call `greenit_obtenir_methodologie_ecoindex` before browser collection and remove its embedded `document.querySelectorAll('*').length` formula.
- [ ] Run `pytest ../tests/ -v` from `greenit/files` and verify the complete GreenIT suite passes.
- [ ] Run the repository lint and type-check commands detected from its configuration, then inspect `git diff --check`.
