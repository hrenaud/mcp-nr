# Design — Protocole EcoIndex officiel dans `extract_page_metrics`

**Date :** 2026-04-09  
**Fichier concerné :** `files/audit_url.py`  
**Fonction concernée :** `extract_page_metrics(page, url)`

---

## Contexte

La mesure EcoIndex officielle impose un protocole précis pour capturer les ressources déclenchées par le scroll (lazy loading, IntersectionObserver, contenu JS injecté). Le code actuel mesure immédiatement après le chargement de la page, ce qui sous-estime le nombre de requêtes et le poids réel.

## Protocole EcoIndex (spec officielle)

1. Charger la page
2. Attendre 3 secondes
3. Scroller jusqu'en bas
4. Attendre 3 secondes
5. Mesurer

## Décisions de design

### Viewport standardisé

`browser.new_context()` fixe le viewport à **1920×1080** conformément à la spec EcoIndex.  
Actuellement, aucun viewport n'est défini explicitement.

### Scroll progressif (non saut direct)

Certains éléments lazy utilisent `IntersectionObserver`, qui ne se déclenche que lorsque l'élément passe dans le viewport. Un saut direct `scrollTo(0, scrollHeight)` saute tous les éléments intermédiaires.

Solution : **4 étapes** (25 % / 50 % / 75 % / 100 %) avec 250 ms entre chaque. Cela déclenche tous les IntersectionObservers sans simuler un défilement humain frame-by-frame. Coût estimé : ~1-2 s par page (acceptable pour des audits de 50 pages).

### Mesure en deux phases (résout le conflit lazy loading)

| Métrique | Phase | Raison |
|---|---|---|
| `images_sans_lazy` | Avant scroll | Check code quality sur le DOM source |
| `fonts`, `iframes`, `links` | Avant scroll | Attributs HTML statiques |
| `dom_nodes` | Après scroll | Compte final incluant éléments injectés par JS |
| `requests`, `size_kb` | Accumulé tout au long | Listener response actif depuis le début |
| `ecoindex_score`, `grade` | Après scroll | Calculé sur les métriques post-scroll |

`images_sans_lazy` reste un check de **qualité de code** (présence de l'attribut `loading='lazy'`), indépendant du fait que l'image ait chargé ou non. Il doit donc être capturé sur le DOM initial.

## Implémentation

```python
# Dans crawl() — context creation
context = await browser.new_context(
    user_agent="Mozilla/5.0 (compatible; GreenIT-Auditor/1.0)",
    viewport={"width": 1920, "height": 1080},
)

# Dans extract_page_metrics() — après goto()

# PHASE 1 : snapshot code quality (DOM initial, avant scroll)
dom_initial = await page.evaluate("""() => { ... }""")  # images_sans_lazy, fonts, iframes, links

# Protocole EcoIndex
await asyncio.sleep(3)
for pct in [0.25, 0.50, 0.75, 1.0]:
    await page.evaluate(f"window.scrollTo(0, document.body.scrollHeight * {pct})")
    await asyncio.sleep(0.25)
await asyncio.sleep(3)

# PHASE 2 : métriques EcoIndex (post-scroll)
dom_nodes = await page.evaluate("document.querySelectorAll('*').length")
# requests_data et total_bytes sont accumulés par le listener depuis le début
ecoindex = compute_ecoindex(dom_nodes, len(requests_data), size_kb)
```

## Interface publique

Aucun changement de signature. `crawl()` et `build_report()` sont inchangés.

## Impact performance

| Scenario | Temps par page (avant) | Temps par page (après) |
|---|---|---|
| Page simple | ~3-5 s | ~9-11 s (+6s wait + ~1s scroll) |
| Audit 5 pages | ~15-25 s | ~45-55 s |
| Audit 50 pages | ~2-4 min | ~8-10 min |

Acceptable car la mesure est désormais conforme au protocole officiel.
