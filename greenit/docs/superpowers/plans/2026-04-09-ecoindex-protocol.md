# EcoIndex Protocol Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implémenter le protocole officiel EcoIndex (load → wait 3s → scroll progressif → wait 3s → mesurer) dans `extract_page_metrics`, avec viewport 1920×1080 et mesure en deux phases.

**Architecture:** On extrait le scroll progressif dans une fonction helper testable `_scroll_to_bottom_progressive(page, step_delay)`. `extract_page_metrics` est refactorisée en deux phases : phase 1 (métriques code quality sur DOM initial), protocole EcoIndex, phase 2 (dom_nodes final pour le score). L'interface publique (`crawl`, `build_report`) est inchangée.

**Tech Stack:** Python asyncio, Playwright async API, pytest + unittest.mock.AsyncMock

---

## Fichiers

- Modify: `files/audit_url.py` — ajout viewport, extraction helper scroll, refactor deux phases
- Modify: `tests/test_tools.py` — tests pour `_scroll_to_bottom_progressive`

---

### Task 1: Extraire et tester `_scroll_to_bottom_progressive`

**Files:**
- Modify: `files/audit_url.py` — ajouter la fonction helper après les imports
- Modify: `tests/test_tools.py` — ajouter `TestScrollToBottomProgressive`

- [ ] **Step 1: Écrire le test qui échoue**

Dans `tests/test_tools.py`, ajouter à la fin du fichier (après `class TestAuditerUrlTool`) :

```python
# ============================================================================
# audit_url — Scroll Protocol
# ============================================================================

import asyncio
from unittest.mock import AsyncMock, MagicMock


class TestScrollToBottomProgressive:
    def test_scrolls_four_steps(self):
        """Helper doit appeler evaluate() exactement 4 fois (25/50/75/100%)."""
        page = MagicMock()
        page.evaluate = AsyncMock()
        asyncio.run(audit_url._scroll_to_bottom_progressive(page, step_delay=0))
        assert page.evaluate.call_count == 4

    def test_scroll_percentages_in_order(self):
        """Les pourcentages doivent être 0.25, 0.5, 0.75, 1.0 dans cet ordre."""
        page = MagicMock()
        page.evaluate = AsyncMock()
        asyncio.run(audit_url._scroll_to_bottom_progressive(page, step_delay=0))
        calls = [c[0][0] for c in page.evaluate.call_args_list]
        assert "0.25" in calls[0]
        assert "0.5" in calls[1]
        assert "0.75" in calls[2]
        assert "1.0" in calls[3]

    def test_each_step_scrolls_to_correct_fraction(self):
        """Chaque appel contient window.scrollTo et scrollHeight."""
        page = MagicMock()
        page.evaluate = AsyncMock()
        asyncio.run(audit_url._scroll_to_bottom_progressive(page, step_delay=0))
        for call in page.evaluate.call_args_list:
            js = call[0][0]
            assert "window.scrollTo" in js
            assert "scrollHeight" in js
```

- [ ] **Step 2: Vérifier que les tests échouent**

```bash
cd /Users/renaudheluin/DEV/DEV_GREENIT/refs/mcp-115-greenit
pytest tests/test_tools.py::TestScrollToBottomProgressive -v
```

Résultat attendu : `AttributeError: module 'audit_url' has no attribute '_scroll_to_bottom_progressive'`

- [ ] **Step 3: Implémenter `_scroll_to_bottom_progressive` dans `audit_url.py`**

Dans `files/audit_url.py`, ajouter après la ligne `from urllib.parse import urlparse` et avant `# ============================================================================` :

```python
import asyncio
```

Puis ajouter la fonction suivante juste avant `# ============================================================================\n# ECOINDEX` :

```python
# ============================================================================
# SCROLL PROTOCOL
# ============================================================================


async def _scroll_to_bottom_progressive(page, step_delay: float = 0.25) -> None:
    """
    Scroll progressively to trigger all IntersectionObserver callbacks.

    Scrolls in 4 steps (25%/50%/75%/100%) with a short pause between each,
    ensuring lazy-loaded elements at all scroll depths are triggered.

    Args:
        page:       Playwright Page object
        step_delay: Seconds to wait between scroll steps (default 0.25s)
    """
    for pct in [0.25, 0.5, 0.75, 1.0]:
        await page.evaluate(f"window.scrollTo(0, document.body.scrollHeight * {pct})")
        await asyncio.sleep(step_delay)
```

- [ ] **Step 4: Vérifier que les tests passent**

```bash
pytest tests/test_tools.py::TestScrollToBottomProgressive -v
```

Résultat attendu :
```
PASSED tests/test_tools.py::TestScrollToBottomProgressive::test_scrolls_four_steps
PASSED tests/test_tools.py::TestScrollToBottomProgressive::test_scroll_percentages_in_order
PASSED tests/test_tools.py::TestScrollToBottomProgressive::test_each_step_scrolls_to_correct_fraction
```

- [ ] **Step 5: Commit**

```bash
git add files/audit_url.py tests/test_tools.py
git commit -m "feat(audit): add _scroll_to_bottom_progressive helper with tests"
```

---

### Task 2: Ajouter le viewport 1920×1080 dans `crawl()`

**Files:**
- Modify: `files/audit_url.py:417-421` — `browser.new_context()` call dans `crawl()`

- [ ] **Step 1: Écrire le test qui échoue**

Dans `tests/test_tools.py`, ajouter dans `class TestScrollToBottomProgressive` (ou comme nouvelle classe juste après) :

```python
class TestCrawlViewport:
    def test_crawl_sets_1920x1080_viewport(self, monkeypatch):
        """crawl() doit créer le contexte browser avec viewport 1920x1080."""
        import asyncio
        from unittest.mock import AsyncMock, MagicMock, patch

        # Mock context qui enregistre les kwargs de new_context
        captured = {}

        async def fake_new_context(**kwargs):
            captured.update(kwargs)
            ctx = MagicMock()
            ctx.close = AsyncMock()
            page = MagicMock()
            page.close = AsyncMock()
            page.on = MagicMock()
            page.goto = AsyncMock(side_effect=Exception("stop"))
            ctx.new_page = AsyncMock(return_value=page)
            return ctx

        async def fake_launch(**kwargs):
            browser = MagicMock()
            browser.close = AsyncMock()
            browser.new_context = AsyncMock(side_effect=fake_new_context)
            return browser

        with patch("audit_url.async_playwright") as mock_pw:
            mock_p = AsyncMock()
            mock_p.__aenter__ = AsyncMock(return_value=mock_p)
            mock_p.__aexit__ = AsyncMock(return_value=False)
            mock_p.chromium.launch = AsyncMock(side_effect=fake_launch)
            mock_pw.return_value = mock_p
            asyncio.run(audit_url.crawl("https://example.com", max_pages=1))

        assert captured.get("viewport") == {"width": 1920, "height": 1080}, \
            f"Expected viewport 1920x1080, got: {captured.get('viewport')}"
```

- [ ] **Step 2: Vérifier que le test échoue**

```bash
pytest tests/test_tools.py::TestCrawlViewport -v
```

Résultat attendu : `AssertionError: Expected viewport 1920x1080, got: None`

- [ ] **Step 3: Modifier `crawl()` pour ajouter le viewport**

Dans `files/audit_url.py`, trouver le bloc `browser.new_context(` (environ ligne 419) et remplacer :

```python
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (compatible; GreenIT-Auditor/1.0)"
        )
```

par :

```python
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (compatible; GreenIT-Auditor/1.0)",
            viewport={"width": 1920, "height": 1080},
        )
```

- [ ] **Step 4: Vérifier que le test passe**

```bash
pytest tests/test_tools.py::TestCrawlViewport -v
```

Résultat attendu : `PASSED`

- [ ] **Step 5: Commit**

```bash
git add files/audit_url.py tests/test_tools.py
git commit -m "feat(audit): set viewport 1920x1080 per EcoIndex spec"
```

---

### Task 3: Refactorer `extract_page_metrics` en deux phases

**Files:**
- Modify: `files/audit_url.py:292-391` — refactor de `extract_page_metrics`

Cette tâche refactorise la fonction principale. Les tests existants de `TestBuildReport` et `TestMapMetricsToFiches` valident indirectement que la structure de retour reste identique.

- [ ] **Step 1: Vérifier que les tests existants passent avant de modifier**

```bash
pytest tests/test_tools.py -v --ignore-glob="*playwright*" -k "not TestCrawlViewport"
```

Résultat attendu : tous les tests passent (les tests Playwright sont ignorés si absent).

- [ ] **Step 2: Remplacer le corps de `extract_page_metrics` dans `files/audit_url.py`**

Remplacer la fonction entière `async def extract_page_metrics(page, url: str) -> dict:` (lignes ~292-391) par :

```python
async def extract_page_metrics(page, url: str) -> dict:
    """
    Navigate to url with a Playwright page and extract all technical metrics.

    Follows the official EcoIndex protocol:
      1. Load page (networkidle or load)
      2. Phase 1: snapshot code-quality metrics on initial DOM
      3. Wait 3 seconds
      4. Scroll progressively to bottom (triggers IntersectionObserver lazy loads)
      5. Wait 3 seconds
      6. Phase 2: capture final DOM node count and compute EcoIndex

    Args:
        page: Playwright Page object (already created by caller)
        url:  URL to navigate to

    Returns:
        Metrics dict. Includes "_links" key (internal links found on page).
    """
    requests_data = []
    total_bytes = 0

    def on_response(response):
        nonlocal total_bytes
        try:
            cl = response.headers.get("content-length")
            if cl:
                total_bytes += int(cl)
        except Exception:
            pass
        requests_data.append({
            "url": response.url,
            "resource_type": response.request.resource_type,
            "headers": dict(response.headers),
        })

    page.on("response", on_response)

    try:
        await page.goto(url, timeout=30000, wait_until="networkidle")
    except Exception:
        await page.goto(url, timeout=30000, wait_until="load")

    # ── PHASE 1: code-quality snapshot (initial DOM, before scroll) ──────────
    # images_sans_lazy, fonts, iframes, links are attributes of the source code.
    # They must be captured before scroll to avoid inflation from JS-injected elements.
    dom_initial = await page.evaluate("""() => {
        const imgs = Array.from(document.querySelectorAll('img'));
        const fonts = [...new Set(
            Array.from(document.styleSheets)
                .flatMap(s => { try { return Array.from(s.cssRules); } catch(e) { return []; } })
                .filter(r => r instanceof CSSFontFaceRule)
                .map(r => r.style.getPropertyValue('font-family').replace(/['"]/g,'').trim())
                .filter(Boolean)
        )];
        return {
            images_sans_lazy: imgs.filter(i => i.getAttribute('loading') !== 'lazy').length,
            images_sans_alt: imgs.filter(i => !i.hasAttribute('alt')).length,
            iframes: document.querySelectorAll('iframe').length,
            fonts: fonts,
            links: Array.from(document.querySelectorAll('a[href]'))
                       .map(a => a.href)
                       .filter(h => h.startsWith('http')),
        };
    }""")

    # ── EcoIndex protocol ─────────────────────────────────────────────────────
    await asyncio.sleep(3)
    await _scroll_to_bottom_progressive(page)
    await asyncio.sleep(3)

    # ── PHASE 2: EcoIndex metrics (post-scroll final state) ───────────────────
    # dom_nodes is captured after scroll to include JS-injected elements.
    # requests_data and total_bytes have been accumulating since page.on("response").
    dom_nodes = await page.evaluate("document.querySelectorAll('*').length")

    perf = await page.evaluate("""() => {
        const nav = performance.getEntriesByType('navigation')[0] || {};
        const paint = {};
        performance.getEntriesByType('paint').forEach(e => { paint[e.name] = Math.round(e.startTime); });
        return {
            ttfb_ms: nav.responseStart ? Math.round(nav.responseStart - nav.requestStart) : null,
            fcp_ms: paint['first-contentful-paint'] || null,
        };
    }""")

    html_resp = next((r for r in requests_data if r["resource_type"] == "document"), None)
    compression = False
    cache_headers = False
    if html_resp:
        h = html_resp["headers"]
        enc = h.get("content-encoding", "")
        compression = "gzip" in enc or "br" in enc
        cache_headers = bool(h.get("cache-control") or h.get("etag"))

    all_urls = [r["url"] for r in requests_data]
    size_kb = round(total_bytes / 1024, 2) if total_bytes > 0 else 0
    nb_req = len(requests_data)
    ecoindex = compute_ecoindex(dom_nodes, nb_req, size_kb)

    return {
        "url": url,
        "dom_nodes": dom_nodes,
        "requests": nb_req,
        "size_kb": size_kb,
        "resource_types": dict(Counter(r["resource_type"] for r in requests_data)),
        "images_sans_lazy": dom_initial["images_sans_lazy"],
        "images_sans_alt": dom_initial["images_sans_alt"],
        "iframes": dom_initial["iframes"],
        "fonts": dom_initial["fonts"],
        "compression": compression,
        "cache_headers": cache_headers,
        "tracking_scripts": detect_tracking(all_urls),
        "ttfb_ms": perf["ttfb_ms"],
        "fcp_ms": perf["fcp_ms"],
        "lcp_ms": None,
        "ecoindex_score": ecoindex["score"],
        "grade": ecoindex["grade"],
        "_links": dom_initial["links"],
    }
```

- [ ] **Step 3: Vérifier que `asyncio` est bien importé en haut du fichier**

Ouvrir `files/audit_url.py` et vérifier que la ligne `import asyncio` est présente (ajoutée en Task 1). Si elle était déjà là, pas de doublon à créer.

- [ ] **Step 4: Lancer tous les tests**

```bash
pytest tests/test_tools.py -v
```

Résultat attendu : tous les tests passent. En particulier :
- `TestBuildReport` — structure de retour inchangée ✓
- `TestMapMetricsToFiches` — clés `images_sans_lazy`, `dom_nodes`, etc. identiques ✓
- `TestScrollToBottomProgressive` — helper fonctionne ✓
- `TestCrawlViewport` — viewport 1920×1080 ✓

- [ ] **Step 5: Commit**

```bash
git add files/audit_url.py
git commit -m "feat(audit): implement EcoIndex protocol with two-phase measurement

- Phase 1 (pre-scroll): capture images_sans_lazy, fonts, iframes, links
- EcoIndex protocol: wait 3s, scroll progressif 4 étapes, wait 3s
- Phase 2 (post-scroll): dom_nodes final, requests accumulés, compute EcoIndex
- Viewport fixé à 1920x1080 dans crawl()"
```
