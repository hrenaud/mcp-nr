# Design : Tool `auditer_url`

## Contexte

Le MCP GreenIT expose des tools basés sur un cache local de fiches GreenIT. Il n'existe pas de tool capable d'analyser une URL réelle. Ce document spécifie l'ajout du tool `auditer_url` qui crawle un site, capture des métriques techniques, calcule l'EcoIndex, et croise les résultats avec les fiches GreenIT.

---

## Signature du tool

```python
def auditer_url(
    url: str,
    format: str = "markdown",  # "markdown" | "json"
    max_pages: int = 5,
) -> str | dict
```

**Paramètres :**
- `url` : URL de départ à auditer
- `format` : format de sortie (`"markdown"` par défaut, `"json"`)
- `max_pages` : nombre maximum de pages à crawler (défaut: 5, même domaine uniquement)

---

## Architecture

```
auditer_url(url, format, max_pages)
    └── CrawlEngine (Playwright Python)
          ├── visiter page → extraire métriques techniques
          ├── extraire liens (même domaine) → enqueue si < max_pages
          └── loop jusqu'à max_pages
    └── compute_ecoindex(dom, req, size_kb)
          └── score (0-100) + grade (A→G)
    └── GreenITMapper
          └── pour chaque métrique → trouver fiches GreenIT correspondantes (cache local)
    └── ReportBuilder
          ├── format="markdown" → rapport Markdown structuré
          └── format="json" → dict structuré
```

Le tool est ajouté dans `files/greenit_mcp_final.py`. Il est `async` (requis par Playwright).

---

## Métriques capturées par page

### Réseau (via `page.on("request"/"response")`)
- Nombre total de requêtes
- Poids total transféré (KB)
- Répartition par type : HTML, CSS, JS, images, fonts, vidéos, autres
- Présence de scripts tiers / tracking (Google Analytics, GTM, Facebook Pixel, etc.)

### DOM (via `page.evaluate()`)
- Taille du DOM (nombre de nœuds)
- Présence d'`<iframe>`
- Images sans `loading="lazy"`
- Images sans attribut `alt`
- Fonts chargées

### Performance (via `window.performance`)
- LCP, FCP, TTFB (si disponibles via PerformanceObserver)
- CLS, FID si disponibles (null sinon)

### Headers HTTP
- Compression (`Content-Encoding: gzip` / `br`)
- Cache (`Cache-Control`, `ETag`)

---

## Calcul EcoIndex

Adapté depuis [cnumr/ecoindex_js](https://github.com/cnumr/ecoindex_js) et [cnumr/ecoindex_reference](https://github.com/cnumr/ecoindex_reference).

**Inputs :** `dom` (nœuds), `req` (nb requêtes), `size_kb` (poids total en KB)

**Formule :**
```
ecoindex = 100 - 5 * (3 * q_dom + 2 * q_req + q_size) / 6
```

Où `q_x` est la position interpolée dans les quantiles de référence.

**Grades :** A (>80), B (>70), C (>55), D (>40), E (>25), F (>10), G (≤10)

**Sortie par page :** `ecoindex_score` (float, 0-100) + `grade` (str, A→G)

Les quantiles de référence sont embarqués directement dans le code (pas de dépendance externe).

---

## GreenIT Mapper

Mapping des métriques sur les fiches du cache local (`charger_cache()`).

| Condition | Saved resources / mots-clés ciblés |
|---|---|
| Images sans `lazy` | `network`, `images` |
| DOM > 1500 nœuds | `cpu` |
| Nb requêtes > 40 | `requests`, `network` |
| Poids > 1024 KB | `network`, `storage` |
| Scripts tiers / tracking | `javascript`, `cpu` |
| Pas de compression gzip/br | `network`, `server` |
| Pas de cache headers | `storage`, `server` |
| Fonts > 2 familles | `network`, `css` |
| Iframes présents | `javascript`, `network` |
| EcoIndex grade D/E/F/G | fiches prioritaires (impact ≥ 4 ET priorité ≥ 4) |

Chaque fiche retournée inclut : `id`, `titre`, `environmental_impact`, `priority_implementation`, `url`.

---

## Format de sortie

### JSON

```json
{
  "url": "https://example.com",
  "pages_analysees": 5,
  "ecoindex_moyen": 62.3,
  "grade_moyen": "C",
  "pages": [
    {
      "url": "https://example.com/",
      "ecoindex_score": 68.1,
      "grade": "B",
      "dom_nodes": 842,
      "requests": 34,
      "size_kb": 712,
      "images_sans_lazy": 4,
      "compression": true,
      "cache_headers": false,
      "tracking_scripts": ["gtm"],
      "lcp_ms": 1200,
      "fcp_ms": 800,
      "ttfb_ms": 210,
      "iframes": 0,
      "fonts": ["Inter", "Arial"],
      "fiches_greenit": [
        {"id": "RWEB_0049", "titre": "...", "environmental_impact": 4, "priority_implementation": 5, "url": "..."}
      ]
    }
  ],
  "recommandations_globales": [
    {"id": "RWEB_0049", "titre": "...", "occurrences": 3}
  ]
}
```

### Markdown

Rapport structuré avec :
- En-tête : URL, nb pages, EcoIndex moyen, grade moyen
- Section par page : tableau des métriques, EcoIndex, fiches GreenIT associées
- Section finale : recommandations globales triées par occurrences

---

## Dépendances

- `playwright` (Python) — à ajouter dans `requirements.txt` / `Dockerfile`
- `playwright install chromium` — à ajouter dans le setup

---

## Contraintes

- Crawl limité au même domaine que l'URL de départ
- `max_pages` max recommandé : 50 (pas de limite hard imposée par le tool)
- Timeout par page : 30s
- Le tool est `async` — compatible avec FastMCP async
