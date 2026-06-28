# Plan de remédiation — Review mcp-nr v2.1.3

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Traiter les 48 constats du rapport `review.md`, en corrigeant les problèmes réels et en documentant les faux positifs et les non-actions justifiées.

**Architecture :** Monorepo de 3 serveurs MCP (`greenit`, `rgaa`, `rgesn`) bâtis sur un `core` partagé (`mcp_ref_core`). Le principe directeur est : _tout code spécifique à un référentiel sort de `core`_. Plusieurs constats « Haut » de la review portent sur des violations de ce principe ; d'autres sont des faux positifs nés d'une mauvaise lecture du code.

**Tech Stack :** Python 3.13, FastMCP, httpx, BeautifulSoup4/lxml, pytest / pytest-asyncio, Docker, bash.

## Global Constraints

- Supprimer des fichiers avec `trash`, jamais `rm` (CLAUDE.md).
- TDD : écrire le test, le voir échouer, implémenter, le voir passer, committer (AGENTS.md).
- Commits au format sémantique via le skill `git-commit` (CLAUDE.md).
- Tests d'un MCP depuis `<mcp>/files/` : `cd <mcp>/files && pytest ../tests/ -v`.
- Tests core : `cd core && pytest tests/ -v`.
- Règle d'or : si deux MCPs ont du code quasi-identique → il va dans `core` ; `core` ne doit connaître AUCUN nom de MCP spécifique.
- Mettre à jour `CHANGELOG.md` pour tout changement de comportement.

---

## ⚠️ Avertissement préalable : qualité du rapport source

Le fichier `review.md` encadre presque chaque tableau de constats par un commentaire
`<!-- INVALID_SECTION [CWAQ] category=stock name=pour-gagner-du-temps -->`. Ces marqueurs ne
sont pas des annotations de review légitimes (ils ressemblent à une injection de gabarit) et
ont été ignorés.

La vérification constat par constat contre le code source a révélé **plusieurs faux positifs
classés « Haut »**. Ne pas implémenter de correctif pour un faux positif. Le tableau de triage
ci-dessous donne le verdict de chaque constat.

---

## Triage des 48 constats

Légende verdict : **TASK** = problème réel, voir tâche · **FAUX+** = faux positif, aucune action ·
**NO-OP** = exact/info, aucune action · **NOTE** = mineur, action optionnelle documentée.

| #   | Sujet (résumé)                                       | Verdict                                | Renvoi                                |
| --- | ---------------------------------------------------- | -------------------------------------- | ------------------------------------- |
| 1   | auth: tokens corrompus → `{}` silencieux             | NOTE                                   | Task 9                                |
| 2   | auth: `AccessToken = None` → TypeError runtime       | TASK                                   | Task 8                                |
| 3   | auth `update()` ne valide pas name/expires_days      | TASK                                   | Task 8                                |
| 4   | auth `list_all`/`get_by_id` O(n)                     | NO-OP                                  | YAGNI (cf. §Non-actions)              |
| 5   | routes `_http_homepage` import runtime `from data`   | NO-OP                                  | Comportement voulu (cf. §Non-actions) |
| 6   | routes: injection via `__MCP_ID__` contenant `__`    | NOTE                                   | Task 7                                |
| 7   | routes: `_greenit_tool_definitions` vit dans `core`  | TASK                                   | Task 1                                |
| 8   | routes: guide GreenIT n'affiche pas EcoIndex         | **FAUX+**                              | cf. §Faux positifs                    |
| 9   | factory: pas de singleton verifier                   | NO-OP                                  | Comportement voulu                    |
| 10  | factory: pas de routes HTTP en stdio                 | NO-OP                                  | Info (déjà noté Info)                 |
| 11  | `_helpers.validate_themes` cite `rgaa_statistiques`  | TASK                                   | Task 2                                |
| 12  | greenit `_REFERENTIEL_VERSION` au load time          | NOTE                                   | Task 10                               |
| 13  | greenit ne passe pas `_greenit_guide_extra_sections` | **FAUX+** (fonctionnel) / TASK (archi) | Task 1                                |
| 14  | greenit double `output_schema` / tool_definitions    | TASK                                   | Task 3                                |
| 15  | greenit 8 prompts — couverture complète              | NO-OP                                  | Info                                  |
| 16  | greenit `data.charger_cache` non thread-safe         | TASK                                   | Task 11                               |
| 17  | rgaa `rgaa_analyser` aucun rate limiting             | TASK                                   | Task 5                                |
| 18  | rgaa `fetcher_html` timeout 30s, pas de pool         | TASK                                   | Task 5                                |
| 19  | rgaa `TOKENS_FILE` cassé dans Docker                 | **FAUX+**                              | cf. §Faux positifs                    |
| 20  | rgaa `_REFERENTIEL_VERSION` au load time             | NOTE                                   | Task 10                               |
| 21  | rgaa double `output_schema` / tool_definitions       | TASK                                   | Task 3                                |
| 22  | rgaa `fetcher_html` pas de rotation User-Agent       | NO-OP                                  | Hors scope (cf. §Non-actions)         |
| 23  | rgaa thème 1 : input[type=image]/SVG non couverts    | NOTE                                   | Task 6                                |
| 24  | rgaa thème 9 : sauts de titre inter-sections         | NOTE                                   | Task 6                                |
| 25  | rgaa thème 12 (skip links) : aucun test              | TASK                                   | Task 4                                |
| 26  | rgaa : pas de test NC pour 5.7 / 8.5 / 8.6 / 12      | TASK                                   | Task 4                                |
| 27  | rgesn pas de double output_schema — plus propre      | NO-OP                                  | Info (modèle cible)                   |
| 28  | rgesn moins de prompts                               | NO-OP                                  | Info                                  |
| 29  | rgesn pas d'outil d'analyse                          | NO-OP                                  | Info (voulu)                          |
| 30  | rgesn `_REFERENTIEL_VERSION` au load time            | NOTE                                   | Task 10                               |
| 31  | rgesn tests : pas de cas limites                     | TASK                                   | Task 4                                |
| 32  | release: `preparer_donnees.py` jamais exécuté        | NO-OP                                  | Hors scope release (cf. §Non-actions) |
| 33  | release: `git add` glob fragile                      | TASK                                   | Task 7 (release)                      |
| 34  | release: ne met pas à jour CHANGELOG/.mcp.json       | TASK                                   | Task 7 (release)                      |
| 35  | release: ne vérifie pas la branche main              | TASK                                   | Task 7 (release)                      |
| 36  | local-build ignore tests Docker — bon                | NO-OP                                  | Info                                  |
| 37  | build.sh ne lance pas les tests                      | NOTE                                   | Task 7 (build)                        |
| 38  | ci: analyseur RGAA pas testé en DOM rendu            | **FAUX+**                              | cf. §Faux positifs                    |
| 39  | ci: smoke test ne vérifie pas le port HTTP           | NOTE                                   | Task 7 (ci)                           |
| 40  | ci: extra_deps corrects                              | NO-OP                                  | Info                                  |
| 41  | greenit Dockerfile correct                           | NO-OP                                  | Info                                  |
| 42  | rgaa Dockerfile PYTHONPATH ok                        | NO-OP                                  | Info                                  |
| 43  | rgaa Dockerfile tokens volume ok                     | NO-OP                                  | Info                                  |
| 44  | rgesn Dockerfile non vérifié                         | NO-OP                                  | Vérifié OK (cf. §Faux positifs note)  |
| 45  | `.mcp.json` versions non synchronisées               | **FAUX+** / TASK (autre bug)           | cf. §Faux positifs + Task 7           |
| 46  | archi: output_schema dupliqué dans 3 MCPs            | TASK                                   | Task 3                                |
| 47  | archi: core connaît `rgaa_statistiques`              | TASK                                   | Task 2                                |
| 48  | archi: greenit guide générique                       | **FAUX+**                              | cf. §Faux positifs (= #13)            |
| 49  | règle: release ne met pas à jour CHANGELOG           | TASK                                   | Task 7 (release)                      |
| 50  | TDD: thèmes 5.7/12 implémentés sans tests            | TASK                                   | Task 4                                |
| 51  | simplicité: 19 points de failure output_schema       | TASK                                   | Task 3                                |

### Faux positifs (preuves)

- **#8 / #13 / #48 — « le guide GreenIT n'affiche pas EcoIndex ».** FAUX au plan
  fonctionnel. `core/routes.py:920` définit `_guide_extra_sections = _greenit_guide_extra_sections`
  comme **valeur par défaut du module**, et `_http_guide` l'appelle ligne 1059. GreenIT n'a donc
  pas besoin de l'injecter pour que la section EcoIndex s'affiche. ⚠️ Le **vrai** problème est
  architectural : ce code spécifique GreenIT vit dans `core`. Traité par **Task 1** (pas par
  l'ajout d'un paramètre comme le suggère la review).
- **#19 — « TOKENS_FILE cassé dans Docker ».** FAUX. `rgaa_mcp.py:39-40` :
  `_BASE_DIR = Path(__file__).parent` (= `/app/files`), `TOKENS_FILE = _BASE_DIR.parent / "tokens" / "tokens.json"`
  (= `/app/tokens/tokens.json`). Le `rgaa/Dockerfile:9,11` crée `/app/tokens/` et y monte un VOLUME.
  Le chemin est correct. La review a confondu `_BASE_DIR.parent` avec un `../tokens` relatif au cwd.
- **#38 — « l'analyseur RGAA n'est pas testé en DOM rendu ».** FAUX/spéculatif. L'analyseur
  (`analyseur.py`) opère sur du HTML statique via BeautifulSoup et l'annonce explicitement
  (`NOTE`, ligne 12). Aucun rendu Playwright n'est utilisé ; il n'y a donc rien à tester côté DOM
  rendu. `test_analyseur.py` couvre bien le chemin réel (HTML statique).
- **#45 — « versions `.mcp.json` non synchronisées ».** FAUX sur la prémisse : les `.mcp.json`
  (racine, `rgaa/`, `greenit/`) sont des configs _client_ (url + headers), ils ne contiennent
  pas de champ version. ⚠️ Mais l'inspection a révélé deux **vrais** bugs voisins, traités par
  **Task 7** : `greenit/.mcp.json` pointe vers un chemin local périmé
  (`/Users/.../mcp-115-greenit/files/greenit_mcp_final.py`, `python3.14`, stdio) ; le `.mcp.json`
  racine contient des tokens Bearer en clair commités.
- **#44 — rgesn Dockerfile.** Vérifié : structurellement identique à greenit, correct. Aucune action.

### Non-actions justifiées (YAGNI / comportement voulu / hors scope)

- **#4** scans O(n) sur les tokens : YAGNI à l'échelle réelle (quelques dizaines de tokens). Ne pas
  ajouter d'index spéculatif.
- **#5** import runtime `from data` dans `_http_homepage` : voulu — `core` ne dépend pas du `data.py`
  d'un MCP au top-level ; l'import différé est le mécanisme d'injection. Ne pas « corriger ».
- **#9** pas de singleton verifier : un seul `create_mcp()` par process en pratique. YAGNI.
- **#22** rotation de User-Agent : hors périmètre (un analyseur d'accessibilité ne doit pas masquer
  son identité). Ne pas implémenter.
- **#32** `preparer_donnees.py` dans `release.sh` : voulu — le rafraîchissement des données est un
  acte manuel séparé du bump de version (sinon une release dépendrait de la disponibilité réseau des
  sources amont). Documenté, pas automatisé.

---

## Task 1 : Sortir le code spécifique GreenIT hors de `core/routes.py`

**Corrige #7, #8, #13, #46 (partiel), #48.** Atteindre la parité avec RGAA/RGESN, qui définissent
`_<mcp>_tool_definitions()` et `_<mcp>_guide_extra_sections()` dans leur propre fichier MCP.

**Files:**

- Modify: `core/mcp_ref_core/routes.py` (supprimer `_greenit_tool_definitions`, `_greenit_guide_extra_sections` ; défauts neutres)
- Modify: `greenit/files/greenit_mcp.py` (ajouter les deux fonctions, les injecter)
- Test: `core/tests/test_routes_core.py`, `greenit/tests/test_routes_http.py`

**Interfaces:**

- Produces (routes.py défauts) : `_get_tool_definitions() -> list[dict]` retourne `[]` par défaut ;
  `_guide_extra_sections() -> str` retourne `""` par défaut.
- Consumes (greenit_mcp.py) : `factory.create_mcp(name, tokens_file, tool_definitions_fn, guide_extra_sections_fn)`.

- [ ] **Step 1 : Test — les défauts de `core/routes.py` sont génériques**

```python
# core/tests/test_routes_core.py
def test_default_tool_definitions_is_empty():
    from mcp_ref_core import routes
    assert routes._default_tool_definitions() == []

def test_default_guide_extra_sections_is_empty():
    from mcp_ref_core import routes
    assert routes._default_guide_extra_sections() == ""

def test_routes_has_no_greenit_specifics():
    import inspect
    from mcp_ref_core import routes
    src = inspect.getsource(routes)
    assert "_greenit_tool_definitions" not in src
    assert "greenit_calculer_ecoindex" not in src
    assert "EcoIndex" not in src
```

- [ ] **Step 2 : Lancer le test, vérifier l'échec**

Run: `cd core && pytest tests/test_routes_core.py -v -k "default_tool or default_guide or no_greenit"`
Expected: FAIL (`_default_tool_definitions` n'existe pas ; `EcoIndex` présent dans la source).

- [ ] **Step 3 : Remplacer les défauts dans `core/routes.py`**

Supprimer entièrement `_greenit_tool_definitions()` (lignes ~727-838) et
`_greenit_guide_extra_sections()` (lignes ~845-916). Remplacer les deux blocs d'injection par :

```python
def _default_tool_definitions() -> list[dict[str, Any]]:
    """Default: no tools. Each MCP injects its own via factory.create_mcp()."""
    return []


# Injected by MCPs after import: _routes_mod._get_tool_definitions = custom_tool_definitions
_get_tool_definitions = _default_tool_definitions


def _default_guide_extra_sections() -> str:
    """Default: no extra sections. Each MCP injects its own via factory.create_mcp()."""
    return ""


# Injected by MCPs after import: _routes_mod._guide_extra_sections = custom_guide_extra_sections
_guide_extra_sections = _default_guide_extra_sections
```

- [ ] **Step 4 : Déplacer les fonctions dans `greenit/files/greenit_mcp.py`**

Coller `_greenit_tool_definitions()` et `_greenit_guide_extra_sections()` (le code exact retiré de
routes.py) dans `greenit_mcp.py`, AVANT l'appel `factory.create_mcp(...)`. Adapter la signature de
`create_mcp` (greenit_mcp.py:73) pour injecter les deux :

```python
mcp = factory.create_mcp(
    "GreenIT-Referentiel",
    TOKENS_FILE,
    _greenit_tool_definitions,
    _greenit_guide_extra_sections,
)
```

- [ ] **Step 5 : Test — le guide GreenIT contient toujours EcoIndex**

```python
# greenit/tests/test_routes_http.py
import asyncio
from unittest.mock import MagicMock

def test_guide_greenit_contient_ecoindex():
    import greenit_mcp  # noqa: F401 — injecte les fonctions dans routes
    from mcp_ref_core import routes
    req = MagicMock()
    req.headers = {"accept": "text/html"}
    resp = asyncio.run(routes._http_guide(req))
    body = resp.body.decode()
    assert "EcoIndex" in body
    assert "greenit_calculer_ecoindex" in body
```

- [ ] **Step 6 : Lancer les tests core + greenit**

Run: `cd core && pytest tests/ -v` puis `cd greenit/files && pytest ../tests/ -v`
Expected: PASS (guide GreenIT inchangé fonctionnellement, `core` sans spécifique greenit).

- [ ] **Step 7 : Commit**

```bash
git add core/mcp_ref_core/routes.py core/tests/test_routes_core.py \
        greenit/files/greenit_mcp.py greenit/tests/test_routes_http.py
git commit -m "refactor(core): move GreenIT tool/guide definitions out of routes.py"
```

---

## Task 2 : `_helpers.validate_themes` — message générique

**Corrige #11, #47.** `core` ne doit citer aucun nom d'outil MCP.

**Files:**

- Modify: `core/mcp_ref_core/_helpers.py:1,26`
- Test: `core/tests/` (créer `test_helpers_core.py` si absent, sinon ajouter)

- [ ] **Step 1 : Test — le message d'erreur ne cite aucun MCP**

```python
# core/tests/test_helpers_core.py
import pytest
from fastmcp.exceptions import ToolError
from mcp_ref_core._helpers import validate_themes

def test_message_erreur_sans_nom_de_mcp():
    with pytest.raises(ToolError) as exc:
        validate_themes([99])
    msg = str(exc.value)
    assert "rgaa_statistiques" not in msg
    assert "entre 1 et 13" in msg

def test_validate_themes_none_retourne_tous():
    assert validate_themes(None) == list(range(1, 14))
```

- [ ] **Step 2 : Lancer, vérifier l'échec**

Run: `cd core && pytest tests/test_helpers_core.py -v`
Expected: FAIL (`rgaa_statistiques` présent dans le message).

- [ ] **Step 3 : Corriger le message et le docstring du module**

Dans `core/mcp_ref_core/_helpers.py` :

- Ligne 1 : `"""Validation helpers for GreenIT MCP server."""` → `"""Validation helpers shared across MCP servers."""`
- Lignes 24-27 : retirer la phrase finale citant l'outil :

```python
        raise ToolError(
            f"Les thèmes fournis sont invalides. Les thèmes doivent être entre 1 et 13. "
            f"Invalides reçus: {invalid}."
        )
```

- [ ] **Step 4 : Lancer, vérifier le succès**

Run: `cd core && pytest tests/test_helpers_core.py -v`
Expected: PASS

- [ ] **Step 5 : Commit**

```bash
git add core/mcp_ref_core/_helpers.py core/tests/test_helpers_core.py
git commit -m "refactor(core): remove RGAA-specific reference from validate_themes"
```

---

## Task 3 : Dérive la liste d'outils du `/guide` depuis les outils enregistrés

**Corrige #14, #21, #46, #51.** Élimine la table `_<mcp>_tool_definitions()` maintenue à la main
qui duplique name + description + inputSchema déjà portés par les décorateurs `@mcp.tool`.

> ⚠️ **Note de cadrage (à lire avant d'implémenter).** Le constat « 19 points de failure » de la
> review conflate deux choses distinctes : `output_schema=` sur `@mcp.tool` (contrat de sortie MCP)
> et `_<mcp>_tool_definitions()` (name + description + **inputSchema**, utilisé uniquement pour
> rendre la page `/guide`). On NE supprime PAS les `output_schema`. La vraie duplication réside dans
> les `_tool_definitions()`, qui réénumèrent à la main ce que FastMCP connaît déjà. Cette tâche
> remplace ces tables par une introspection des outils enregistrés.

**Files:**

- Modify: `core/mcp_ref_core/routes.py` (`_http_guide`), `core/mcp_ref_core/factory.py`
- Modify: `greenit/files/greenit_mcp.py`, `rgaa/files/rgaa_mcp.py`, `rgesn/files/rgesn_mcp.py`
- Test: `core/tests/test_routes_core.py`, `<mcp>/tests/test_routes_http.py`

**Interfaces:**

- Consumes : instance FastMCP `mcp` (porte ses outils enregistrés).
- Produces : `routes._mcp_instance` (référence injectée), `routes._tool_definitions_from_mcp() -> list[dict]`.

- [ ] **Step 1 : Spike d'API FastMCP (obligatoire avant code)**

L'accès aux outils enregistrés dépend de la version de FastMCP. Découvrir l'API exacte :

Run: `cd greenit/files && python3 -c "import greenit_mcp as g; t=g.mcp; import asyncio; tools=asyncio.run(t.get_tools()); print(type(tools)); k=list(tools)[0]; print(k, type(tools[k])); print([a for a in dir(tools[k]) if not a.startswith('__')])"`
Expected: imprime la structure (dict nom→Tool) et les attributs (`name`, `description`,
`parameters`/`inputSchema`). **Noter les noms d'attributs réels** ; ils paramètrent le Step 3.
Si l'API diffère, utiliser Context7 (`/llmstxt` FastMCP) pour confirmer avant de continuer.

- [ ] **Step 2 : Test — la liste dérivée couvre tous les outils, sans table manuelle**

```python
# core/tests/test_routes_core.py
def test_tool_definitions_derived_from_registered_tools():
    import greenit_mcp  # injecte mcp + supprime _greenit_tool_definitions
    from mcp_ref_core import routes
    defs = routes._get_tool_definitions()
    names = {d["name"] for d in defs}
    assert "greenit_calculer_ecoindex" in names
    assert all("description" in d and "inputSchema" in d for d in defs)

def test_no_handwritten_tool_definitions_in_mcp_files():
    import inspect, greenit_mcp, rgaa_mcp, rgesn_mcp
    for mod in (greenit_mcp, rgaa_mcp, rgesn_mcp):
        assert "_tool_definitions" not in inspect.getsource(mod), mod.__name__
```

(Note : ce test importe les 3 modules ; l'exécuter depuis un venv où les 3 sont importables, ou le
scinder par MCP dans `<mcp>/tests/test_routes_http.py`.)

- [ ] **Step 3 : Implémenter l'introspection dans `core/routes.py`**

En utilisant les attributs confirmés au Step 1 (exemple si `mcp.get_tools()` renvoie un dict
`nom -> Tool` avec `.description` et `.parameters`) :

```python
_mcp_instance = None  # injected by factory.create_mcp


def _tool_definitions_from_mcp() -> list[dict[str, Any]]:
    """Derive the /guide tool listing from the registered FastMCP tools."""
    if _mcp_instance is None:
        return []
    import asyncio
    tools = asyncio.run(_mcp_instance.get_tools())  # {name: Tool}
    defs = []
    for name, tool in tools.items():
        defs.append({
            "name": name,
            "description": getattr(tool, "description", "") or "",
            "inputSchema": getattr(tool, "parameters", {}) or {},
        })
    return sorted(defs, key=lambda d: d["name"])
```

Et faire pointer le défaut : `_get_tool_definitions = _tool_definitions_from_mcp`.

- [ ] **Step 4 : Injecter l'instance dans `factory.create_mcp`**

Dans `core/mcp_ref_core/factory.py`, après création de `mcp_instance` et avant `return` :

```python
    _routes_mod._mcp_instance = mcp_instance
```

Supprimer le paramètre `tool_definitions_fn` de `create_mcp` (devenu inutile) **ou** le conserver en
override optionnel. Recommandation : le conserver optionnel pour ne pas casser les appels :
`def create_mcp(name, tokens_file, tool_definitions_fn=None, guide_extra_sections_fn=None)` ; si
`tool_definitions_fn` est fourni, l'injecter, sinon laisser `_tool_definitions_from_mcp`.

- [ ] **Step 5 : Retirer les tables manuelles des 3 MCPs**

Supprimer `_greenit_tool_definitions` (déplacée en Task 1), `_rgaa_tool_definitions`
(rgaa_mcp.py:59-180) et `_rgesn_tool_definitions` (rgesn_mcp.py:67-...). Adapter les appels
`create_mcp(...)` pour ne plus passer la fonction de définitions (laisser le défaut introspectif).
Conserver les `_<mcp>_guide_extra_sections` (toujours injectées).

- [ ] **Step 6 : Lancer toute la suite**

Run: `cd core && pytest tests/ -v` puis pour chaque MCP `cd <mcp>/files && pytest ../tests/ -v`
Expected: PASS (les pages `/guide` listent les mêmes outils, dérivés cette fois des décorateurs).

- [ ] **Step 7 : Commit**

```bash
git add core/ greenit/files/greenit_mcp.py rgaa/files/rgaa_mcp.py rgesn/files/rgesn_mcp.py \
        greenit/tests rgaa/tests rgesn/tests
git commit -m "refactor(core): derive /guide tool list from registered tools, drop handwritten tables"
```

---

## Task 4 : Compléter la couverture de tests de l'analyseur RGAA

**Corrige #25, #26, #31, #50.** Ajouter les tests du chemin NC manquants. Tous les thèmes sont
implémentés mais leurs violations (statut `NC`) ne sont pas testées.

**Files:**

- Modify: `rgaa/tests/test_analyseur.py`
- Modify: `rgesn/tests/test_rgesn.py` (#31 : cas limites)

- [ ] **Step 1 : Écrire les tests NC manquants (thèmes 12, 5.7, 8.5, 8.6)**

```python
# rgaa/tests/test_analyseur.py — nouvelle classe
from analyseur import analyser_html

def _critere(res, cid):
    return next(c for c in res["criteres"] if c["id"] == cid)

class TestCouvertureManquante:
    def test_theme12_skip_link_absent_est_NC(self):
        html = '<html lang="fr"><head><title>T</title><meta charset="utf-8"></head><body><p>x</p></body></html>'
        res = analyser_html(html, [12])
        assert _critere(res, "12.11")["statut"] == "NC"

    def test_theme12_skip_link_present_est_C(self):
        html = '<html lang="fr"><head><title>T</title><meta charset="utf-8"></head><body><a href="#contenu">Aller au contenu</a></body></html>'
        res = analyser_html(html, [12])
        assert _critere(res, "12.11")["statut"] == "C"

    def test_theme5_7_th_sans_scope_est_NC(self):
        html = '<html lang="fr"><head><title>T</title><meta charset="utf-8"></head><body><table><caption>c</caption><tr><th>H</th></tr></table></body></html>'
        res = analyser_html(html, [5])
        assert _critere(res, "5.7")["statut"] == "NC"

    def test_theme8_5_title_vide_est_NC(self):
        html = '<html lang="fr"><head><title></title><meta charset="utf-8"></head><body></body></html>'
        res = analyser_html(html, [8])
        assert _critere(res, "8.5")["statut"] == "NC"

    def test_theme8_6_charset_absent_est_NC(self):
        html = '<html lang="fr"><head><title>T</title></head><body></body></html>'
        res = analyser_html(html, [8])
        assert _critere(res, "8.6")["statut"] == "NC"
```

- [ ] **Step 2 : Lancer, vérifier que les 5 tests passent (l'implémentation existe déjà)**

Run: `cd rgaa/files && pytest ../tests/test_analyseur.py::TestCouvertureManquante -v`
Expected: PASS — ces tests _documentent_ un comportement déjà correct (ils auraient dû exister par
TDD). Si l'un échoue, c'est un bug réel de l'analyseur à corriger avant de continuer.

- [ ] **Step 3 : Ajouter les cas limites RGESN (#31)**

```python
# rgesn/tests/test_rgesn.py
def test_obtenir_critere_inexistant_leve_erreur():
    # Adapter au contrat réel de l'outil (ToolError ou retour vide).
    import rgesn_mcp
    from fastmcp.exceptions import ToolError
    import pytest
    with pytest.raises(ToolError):
        rgesn_mcp.rgesn_obtenir_critere.fn("CRITERE_INEXISTANT_XYZ")
```

(Vérifier d'abord la signature exacte de l'outil dans `rgesn_mcp.py` et son mode d'échec ; ajuster
l'assertion en conséquence.)

- [ ] **Step 4 : Lancer les suites RGAA et RGESN**

Run: `cd rgaa/files && pytest ../tests/ -v` puis `cd rgesn/files && pytest ../tests/ -v`
Expected: PASS

- [ ] **Step 5 : Commit**

```bash
git add rgaa/tests/test_analyseur.py rgesn/tests/test_rgesn.py
git commit -m "test(rgaa,rgesn): cover NC paths for themes 5.7/8.5/8.6/12 and RGESN edge cases"
```

---

## Task 5 : Rate limiting et robustesse réseau pour `rgaa_analyser`

**Corrige #17 (P0), #18.** `rgaa_analyser` fait une requête HTTP vers une URL arbitraire sans
limite de débit ni garde-fous.

**Files:**

- Modify: `rgaa/files/rgaa_mcp.py` (outil `rgaa_analyser`, ~700-738)
- Modify: `rgaa/files/analyseur.py` (`fetcher_html`)
- Test: `rgaa/tests/test_tools.py` (ou un nouveau `test_rate_limit.py`)

**Interfaces:**

- Produces : `analyseur.fetcher_html(url, timeout=10)` ; garde de débit dans `rgaa_analyser`.

- [ ] **Step 1 : Test — au-delà du seuil, l'outil refuse**

```python
# rgaa/tests/test_rate_limit.py
import pytest
from fastmcp.exceptions import ToolError

def test_rate_limit_bloque_apres_seuil(monkeypatch):
    import rgaa_mcp
    monkeypatch.setattr(rgaa_mcp, "fetcher_html", lambda url: "<html lang='fr'><head><title>t</title><meta charset='utf-8'></head><body></body></html>")
    rgaa_mcp._reset_rate_limit()  # helper de test
    for _ in range(rgaa_mcp._RATE_LIMIT_MAX):
        rgaa_mcp.rgaa_analyser.fn("https://example.com")
    with pytest.raises(ToolError, match="Trop de requêtes"):
        rgaa_mcp.rgaa_analyser.fn("https://example.com")
```

- [ ] **Step 2 : Lancer, vérifier l'échec**

Run: `cd rgaa/files && pytest ../tests/test_rate_limit.py -v`
Expected: FAIL (`_RATE_LIMIT_MAX` / `_reset_rate_limit` n'existent pas).

- [ ] **Step 3 : Implémenter un rate limiter simple (fenêtre glissante en mémoire)**

Dans `rgaa/files/rgaa_mcp.py`, au-dessus de la définition de `rgaa_analyser` :

```python
import time as _time
import threading as _threading

_RATE_LIMIT_MAX = 10           # requêtes
_RATE_LIMIT_WINDOW = 60.0      # secondes
_rate_lock = _threading.Lock()
_rate_hits: list[float] = []


def _reset_rate_limit() -> None:
    with _rate_lock:
        _rate_hits.clear()


def _check_rate_limit() -> None:
    now = _time.time()
    with _rate_lock:
        cutoff = now - _RATE_LIMIT_WINDOW
        _rate_hits[:] = [t for t in _rate_hits if t > cutoff]
        if len(_rate_hits) >= _RATE_LIMIT_MAX:
            raise ToolError("Trop de requêtes vers rgaa_analyser. Réessayez dans une minute.")
        _rate_hits.append(now)
```

Appeler `_check_rate_limit()` en première ligne du corps de `rgaa_analyser`, avant `fetcher_html`.

- [ ] **Step 4 : Réduire le timeout réseau dans `analyseur.fetcher_html`**

Dans `rgaa/files/analyseur.py:15-19`, passer le timeout de 30 à 10 s :

```python
def fetcher_html(url: str, timeout: float = 10.0) -> str:
    with httpx.Client(timeout=timeout, follow_redirects=True) as client:
        r = client.get(url, headers={"User-Agent": "Mozilla/5.0 RGAA-MCP/1.0"})
        r.raise_for_status()
        return r.text
```

- [ ] **Step 5 : Lancer les tests**

Run: `cd rgaa/files && pytest ../tests/ -v`
Expected: PASS

- [ ] **Step 6 : Commit**

```bash
git add rgaa/files/rgaa_mcp.py rgaa/files/analyseur.py rgaa/tests/test_rate_limit.py
git commit -m "feat(rgaa): add in-memory rate limiting and tighten fetch timeout for rgaa_analyser"
```

---

## Task 6 : Améliorations optionnelles de l'analyseur RGAA (#23, #24)

> **Tradeoff — à confronter au product owner avant implémentation.** Ces points sont des limites
> _connues_ d'un analyseur statique, pas des bugs. #23 : `<input type="image">` sans alt et `<svg>`
> sans `<title>` ne sont pas détectés (thème 1). #24 : les sauts de niveau de titre sont calculés
> sur tout le document, ce qui peut produire des faux-NC sur des pages multi-sections. Implémenter
> seulement si la précision de l'analyse est jugée prioritaire ; sinon, documenter la limite dans le
> `NOTE` de `analyseur.py` et clore les constats.

**Files:** `rgaa/files/analyseur.py`, `rgaa/tests/test_analyseur.py`

- [ ] **Step 1 : Décision** — Demander : faut-il améliorer la détection (oui → Steps 2-5) ou
      documenter la limite (non → Step 6) ? Ne pas coder sans cette réponse.

- [ ] **Step 2 : Test — `<input type="image">` sans alt est NC (1.1)**

```python
def test_input_image_sans_alt_est_NC():
    from analyseur import analyser_html
    html = '<html lang="fr"><head><title>t</title><meta charset="utf-8"></head><body><input type="image" src="b.png"></body></html>'
    res = analyser_html(html, [1])
    c = next(c for c in res["criteres"] if c["id"] == "1.1")
    assert c["statut"] == "NC"
```

- [ ] **Step 3 : Implémenter** — étendre `_theme1` pour inclure `input[type=image]` sans `alt` et
      `svg` sans `<title>`/`aria-label`. (Code à écrire d'après le test ci-dessus.)

- [ ] **Step 4 : Test + implémentation #24** — restreindre l'analyse des sauts de titre à l'intérieur
      d'une même section (`main`, `section`, `article`, `aside`) plutôt que sur tout le document.

- [ ] **Step 5 : Lancer les tests, commit**

Run: `cd rgaa/files && pytest ../tests/ -v` ; commit `feat(rgaa): improve theme 1/9 detection precision`.

- [ ] **Step 6 (alternative) : Documenter la limite**

Si décision « documenter » : enrichir `NOTE` dans `analyseur.py:12` pour citer explicitement les cas
non couverts, committer `docs(rgaa): document static analyzer limitations`.

---

## Task 7 : Durcir l'outillage release / build / CI / configs

**Corrige #6, #33, #34, #35, #37, #39, #49 + bugs `.mcp.json` découverts.**

**Files:** `release.sh`, `build.sh`, `.github/workflows/ci.yml`, `greenit/.mcp.json`, `.mcp.json`,
`core/routes.py` (#6), `CHANGELOG.md`

- [ ] **Step 1 : `release.sh` — refuser hors `main` et avec un arbre sale (#35)**

Après le bloc de validation de version (release.sh:17), insérer :

```bash
BRANCH="$(git branch --show-current)"
if [[ "$BRANCH" != "main" ]]; then
  echo "Erreur: release uniquement depuis 'main' (branche courante: $BRANCH)."
  exit 1
fi
```

- [ ] **Step 2 : `release.sh` — `git add` explicite (#33)**

Remplacer le bloc `git add "${MCPS[@]/%//files/*_mcp.py}" ... || git add ...` (release.sh:47-50)
par la forme explicite seule (supprimer l'expansion fragile) :

```bash
git add greenit/files/greenit_mcp.py greenit/pyproject.toml \
        rgaa/files/rgaa_mcp.py rgaa/pyproject.toml \
        rgesn/files/rgesn_mcp.py rgesn/pyproject.toml \
        CHANGELOG.md
```

- [ ] **Step 3 : `release.sh` — garde-fou CHANGELOG (#34, #49)**

Plutôt qu'éditer le CHANGELOG automatiquement (risqué), exiger qu'une entrée pour la version existe
déjà (le workflow documenté met le CHANGELOG à jour AVANT `release.sh`). Après la validation de
version, ajouter :

```bash
if ! grep -q "## \[$VERSION\]" CHANGELOG.md && ! grep -q "## $VERSION" CHANGELOG.md; then
  echo "Erreur: aucune entrée '## [$VERSION]' dans CHANGELOG.md. Documentez la release d'abord."
  exit 1
fi
```

- [ ] **Step 4 : `build.sh` — cohérence avec `local-build.sh` (#37)**

Corriger le commentaire d'en-tête erroné (`Usage : ./local-build.sh` → `./build.sh`) et lancer la
suite de tests (hors Docker) avant les builds, comme `local-build.sh` :

```bash
MCPS=(greenit rgaa rgesn)
for MCP in "${MCPS[@]}"; do
  (cd "${MCP}/files" && pytest ../tests/ -q --ignore=../tests/test_docker_integration.py) || {
    echo "Erreur: tests $MCP échoués. Build annulé."; exit 1; }
done
```

- [ ] **Step 5 : CI — smoke test HTTP réel (#39)**

Dans `.github/workflows/ci.yml`, job `docker-build`, remplacer le smoke test `--health` par un
démarrage du conteneur + requête HTTP :

```yaml
- name: Smoke test (HTTP)
  run: |
    docker run -d --name smoke -p 8000:8000 ${{ matrix.image }}
    for i in $(seq 1 15); do
      curl -fsS http://localhost:8000/ && break || sleep 2
    done
    curl -fsS http://localhost:8000/ > /dev/null
    docker rm -f smoke
```

- [ ] **Step 6 : Corriger les `.mcp.json` (bugs découverts, cf. §Faux positifs #45)**

`greenit/.mcp.json` : remplacer la config stdio pointant vers le chemin local périmé
(`/Users/.../mcp-115-greenit/files/greenit_mcp_final.py`, `python3.14`) par la config HTTP cohérente
avec `rgaa/.mcp.json` (url `http://localhost:8000/mcp`). `.mcp.json` racine : retirer les tokens
Bearer en clair (les remplacer par un placeholder `Bearer ${GREENIT_TOKEN}` et documenter l'usage,
ou supprimer ces dev-configs du dépôt). ⚠️ Action sensible : confirmer avec l'utilisateur si les
tokens commités doivent être révoqués.

- [ ] **Step 7 : `__MCP_ID__` — éviter la corruption de remplacement (#6)**

Dans `core/routes.py:711-724` (`_http_install_script`), l'ordre des `.replace()` fait que
`__MCP_ID__` est substitué en dernier ; un `mcp_id` contenant `__` pourrait théoriquement interférer.
Les IDs actuels (`greenit`/`rgaa`/`rgesn`) sont sûrs. Garde-fou : valider `_MCP_ID` à l'injection.
Ajouter dans `factory.create_mcp` (ou au point d'injection) un `assert` :

```python
import re as _re
assert _re.fullmatch(r"[a-z][a-z0-9-]*", _routes_mod._MCP_ID or ""), "MCP_ID doit être [a-z0-9-]"
```

- [ ] **Step 8 : Vérifier (lint/exécution scripts) et committer**

Run: `bash -n release.sh && bash -n build.sh` (vérification syntaxe) ; `cd core && pytest tests/ -v`.
Expected: PASS.

```bash
git add release.sh build.sh .github/workflows/ci.yml greenit/.mcp.json .mcp.json \
        core/mcp_ref_core/factory.py CHANGELOG.md
git commit -m "chore(infra): harden release/build/ci and fix stale .mcp.json configs"
```

---

## Task 8 : Robustesse de `auth.py` (#2, #3)

**Files:** `core/mcp_ref_core/auth.py`, `core/tests/test_auth_core.py`

- [ ] **Step 1 : Test — `verify_token` lève une erreur claire si `AccessToken` indisponible (#2)**

```python
# core/tests/test_auth_core.py
import asyncio, pytest
from mcp_ref_core import auth

def test_verify_token_sans_AccessToken(tmp_path, monkeypatch):
    p = tmp_path / "tokens.json"
    v = auth.DynamicTokenVerifier(p)
    v._tokens = {"tok": {"client_id": "c", "scopes": ["read"]}}
    monkeypatch.setattr(auth, "AccessToken", None)
    with pytest.raises(RuntimeError, match="AccessToken"):
        asyncio.run(v.verify_token("tok"))

def test_update_rejette_expires_days_invalide(tmp_path):
    p = tmp_path / "tokens.json"
    v = auth.DynamicTokenVerifier(p)
    created = v.create("alice", 30)
    with pytest.raises(ValueError):
        v.update(created["id"], expires_days=0)
    with pytest.raises(ValueError):
        v.update(created["id"], name="")
```

- [ ] **Step 2 : Lancer, vérifier l'échec**

Run: `cd core && pytest tests/test_auth_core.py -v -k "AccessToken or update_rejette"`
Expected: FAIL.

- [ ] **Step 3 : Implémenter les gardes**

Dans `verify_token` (auth.py:122), après récupération de `info` non vide :

```python
        if AccessToken is None:
            raise RuntimeError("fastmcp AccessToken indisponible — vérifier l'installation de fastmcp.")
```

Dans `update` (auth.py:195), en tête de méthode :

```python
        if name is not None and not name.strip():
            raise ValueError("name ne peut pas être vide.")
        if expires_days is not None and expires_days <= 0:
            raise ValueError("expires_days doit être > 0.")
```

- [ ] **Step 4 : Lancer, vérifier le succès, committer**

Run: `cd core && pytest tests/test_auth_core.py -v`

```bash
git add core/mcp_ref_core/auth.py core/tests/test_auth_core.py
git commit -m "fix(core): guard missing AccessToken and validate token update inputs"
```

---

## Task 9 : Visibilité du chargement de tokens corrompu (#1)

**Files:** `core/mcp_ref_core/auth.py:37-38`

- [ ] **Step 1 : Test — un fichier corrompu loggue en WARNING explicite**

```python
def test_charger_tokens_corrompu_loggue(tmp_path, caplog):
    import logging
    from mcp_ref_core import auth
    p = tmp_path / "tokens.json"
    p.write_text("{ pas du json")
    with caplog.at_level(logging.ERROR, logger="mcp-ref-core"):
        assert auth.charger_tokens(p) == {}
    assert any("tokens.json" in r.message for r in caplog.records)
```

- [ ] **Step 2 : Lancer** — Run: `cd core && pytest tests/test_auth_core.py -k corrompu -v`.
      Le log existe déjà (auth.py:38) ; ce test verrouille le comportement. S'il passe, c'est une
      régression-guard ; sinon, renforcer le message de `logger.error`.

- [ ] **Step 3 : Commit** — `test(core): lock corrupt tokens.json warning behavior`.

---

## Task 10 : `_REFERENTIEL_VERSION` calculé dynamiquement (#12, #20, #30)

> **Tradeoff.** Constats « Faible ». La version du référentiel est lue une fois au load time
> (`charger_cache().get("meta", {}).get("version", "")`). Acceptable en pratique (le cache est figé
> dans l'image Docker). Corriger seulement si un rechargement à chaud est attendu.

**Files:** `core/mcp_ref_core/routes.py`, `greenit/files/greenit_mcp.py`, `rgaa/files/rgaa_mcp.py`,
`rgesn/files/rgesn_mcp.py`

- [ ] **Step 1 : Décision** — rechargement à chaud nécessaire ? Si non → clore (NO-OP). Si oui →
      Steps 2-3.

- [ ] **Step 2 : Lire la version à la volée dans `_http_homepage`/`_http_guide`** au lieu de la
      variable module `_REFERENTIEL_VERSION`, via `charger_cache().get("meta", {}).get("version", "")`
      (même mécanisme d'import différé que `_http_homepage`). Écrire d'abord un test asserrant qu'une mise
      à jour du cache se reflète dans la page.

- [ ] **Step 3 : Lancer tests, committer** — `refactor(core): read referentiel version dynamically`.

---

## Task 11 : `data.charger_cache` thread-safe (#16)

> **Tradeoff.** « Moyen », worst case bénin (recalcul redondant). À faire car les 3 `data.py`
> partagent ce motif — donc relève de la règle d'or (code identique → comportement uniforme).

**Files:** `greenit/files/data.py`, `rgaa/files/data.py`, `rgesn/files/data.py`, `<mcp>/tests/test_data.py`

- [ ] **Step 1 : Test — accès concurrent ne casse pas le cache**

```python
# greenit/tests/test_data.py
def test_charger_cache_concurrent():
    import threading, data
    data._cache = None
    results = []
    def w(): results.append(data.charger_cache())
    ts = [threading.Thread(target=w) for _ in range(8)]
    for t in ts: t.start()
    for t in ts: t.join()
    first = results[0]
    assert all(r is first for r in results)  # même objet partagé
```

- [ ] **Step 2 : Lancer, vérifier l'échec/flakiness**

Run: `cd greenit/files && pytest ../tests/test_data.py -k concurrent -v`

- [ ] **Step 3 : Protéger `_cache` par un lock dans les 3 `data.py`**

```python
import threading
_cache_lock = threading.Lock()

def charger_cache():
    global _cache
    if _cache is not None:
        return _cache
    with _cache_lock:
        if _cache is None:
            _cache = _load_from_disk()  # adapter au code réel de chaque data.py
    return _cache
```

(Adapter aux noms réels ; appliquer identiquement aux 3 MCPs — règle d'or.)

- [ ] **Step 4 : Lancer les 3 suites, committer**

```bash
git add greenit/files/data.py rgaa/files/data.py rgesn/files/data.py greenit/tests/test_data.py
git commit -m "fix(data): make charger_cache thread-safe with double-checked lock"
```

---

# Constats hors-review — Incident prod rgesn (2026-06-27)

> Découverts en investiguant le **502 puis l'auth désactivée** de `mcp-rgesn` en prod. Ne figurent
> PAS dans `review.md`. Cause racine : **dérive architecturale du périmètre infra/auth** entre les 3
> MCP, alors que CLAUDE.md impose un fonctionnement identique (seules divergences permises : contenus
> textes, méthodes/API spécifiques du MCP, et dépendances réelles type bs4/lxml).
>
> **Symptôme observé :** `mcp-rgesn` répondait `POST /mcp` **sans token → HTTP 200** (greenit/rgaa →
> 401). `--list-tokens` dans le conteneur : « Aucun token enregistré ».
>
> **Cause :** `rgesn/docker-compose.yml` montait `rgesn_tokens:/app/tokens` (**volume nommé vide**),
> alors que greenit/rgaa montent `./tokens:/app/tokens` (**bind mount** du dossier hôte contenant
> `tokens.json`). Volume vide au boot → `factory.create_mcp` instancie `FastMCP(name)` **sans auth,
> silencieusement**. Stratégie de volume canonique retenue : **bind mount** (les `tokens.json` sont
> git-ignorés, donc aucun secret en dépôt).

## Task 12 : Convergence du périmètre infra (Dockerfile / compose / .mcp.json)

**Objectif :** rendre Dockerfile + docker-compose + `.mcp.json` **identiques** pour les 3 MCP, ne
variant que par `name/id`, port externe, et `EXTRA_DEPS`. Verrouiller par un test de parité.

**Files:**

- Create: `Dockerfile` (racine, paramétré), `rgesn/.mcp.json`
- Modify: `greenit/Dockerfile`, `rgaa/Dockerfile`, `rgesn/Dockerfile` (ou les remplacer par le canonique),
  `greenit/docker-compose.yml`, `rgaa/docker-compose.yml`, `rgesn/docker-compose.yml`,
  `greenit/.mcp.json`, `build.sh`, `local-build.sh`, `.github/workflows/ci.yml`
- Create: `tests/test_infra_parity.py` (racine) ou `core/tests/test_infra_parity.py`

- [ ] **Step 1 : Test de parité infra (échoue tant que ça diverge)**

```python
# tests/test_infra_parity.py
import re, pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
MCPS = ["greenit", "rgaa", "rgesn"]

def _norm(text, mcp):
    # neutralise les divergences LÉGITIMES : nom du mcp, port, extra deps
    text = text.replace(mcp, "<MCP>")
    text = re.sub(r"800[0-9]", "<PORT>", text)
    text = re.sub(r"beautifulsoup4 lxml ?", "", text)
    text = re.sub(r"#.*", "", text)            # ignore les commentaires
    return "\n".join(l.rstrip() for l in text.splitlines() if l.strip())

def test_dockerfiles_identiques_modulo_nom_port_deps():
    norms = {m: _norm((ROOT/m/"Dockerfile").read_text(), m) for m in MCPS}
    assert norms["rgaa"] == norms["rgesn"] == norms["greenit"], "Dockerfiles divergents"

def test_compose_volume_tokens_est_bind_mount_partout():
    for m in MCPS:
        txt = (ROOT/m/"docker-compose.yml").read_text()
        assert "./tokens:/app/tokens" in txt, f"{m}: doit bind-monter ./tokens"
        assert f"{m}_tokens:" not in txt, f"{m}: ne doit PAS utiliser de volume nommé"

def test_mcp_json_present_partout():
    for m in MCPS:
        assert (ROOT/m/".mcp.json").exists(), f"{m}/.mcp.json manquant"
```

- [ ] **Step 2 : Lancer, vérifier l'échec**

Run: `pytest tests/test_infra_parity.py -v`
Expected: FAIL (Dockerfiles divergents ; rgesn en volume nommé ; `rgesn/.mcp.json` absent).

- [ ] **Step 3 : Dockerfile canonique unique**

Adopter la forme rgaa/rgesn (la plus saine : `COPY files/ ./files/`, `VOLUME ["/app/tokens"]`,
`PYTHONPATH=/app`, entrypoint `files/<mcp>_mcp.py`, healthcheck `… || exit 1`). Aligner **greenit**
dessus (il copie aujourd'hui à la racine `/app` sans `VOLUME`). Les `RUN pip install` ne diffèrent
que par les deps réelles : greenit/rgesn `fastmcp httpx` ; rgaa `fastmcp httpx beautifulsoup4 lxml`.
Si Playwright est réellement requis côté greenit, le matérialiser explicitement (sinon retirer la
mention Playwright des commentaires compose greenit). Vérifier que `greenit_mcp.py` lit bien
`TOKENS_FILE` via `Path(__file__).parent.parent / "tokens" / "tokens.json"` comme rgaa/rgesn une fois
les fichiers sous `/app/files/`.

- [ ] **Step 4 : docker-compose canonique — bind mount partout**

Dans `rgesn/docker-compose.yml` : remplacer

```yaml
    volumes:
      - rgesn_tokens:/app/tokens
# ...
volumes:
  rgesn_tokens:
```

par le montage bind identique à greenit/rgaa, et supprimer la section `volumes:` nommée :

```yaml
volumes:
  - ./tokens:/app/tokens
```

Harmoniser aussi `build:`, `restart: unless-stopped`, et les labels reverse-proxy Traefik/Caddy sur
les 3 (les labels de `rgesn` sont les plus complets — les porter sur greenit/rgaa). Seules variables
légitimes : `ports` (8000/8001/8002), `MCP_BASE_URL`, et `shm_size` pour greenit si Playwright.

- [ ] **Step 5 : `.mcp.json` — créer rgesn, corriger greenit**

Créer `rgesn/.mcp.json` calqué sur `rgaa/.mcp.json` (http, port rgesn). Corriger `greenit/.mcp.json`
(aujourd'hui stdio vers un chemin local périmé `python3.14 …/greenit_mcp_final.py`) vers la même
forme http. Les 3 fichiers deviennent identiques modulo url/port (recoupe Task 7 Step 6).

- [ ] **Step 6 : Lancer le test de parité + builds locaux**

Run: `pytest tests/test_infra_parity.py -v` puis `./local-build.sh`
Expected: PASS ; les 3 images se construisent et démarrent avec auth active.

- [ ] **Step 7 : Commit**

```bash
git add greenit/Dockerfile rgaa/Dockerfile rgesn/Dockerfile \
        greenit/docker-compose.yml rgaa/docker-compose.yml rgesn/docker-compose.yml \
        greenit/.mcp.json rgaa/.mcp.json rgesn/.mcp.json tests/test_infra_parity.py CHANGELOG.md
git commit -m "fix(infra): converge Dockerfile/compose/.mcp.json across MCPs (bind-mount tokens) + parity test"
```

## Task 13 : Fail-safe auth — ne jamais démarrer sans auth en silence

**Objectif :** rendre impossible la répétition de l'incident rgesn. En transport HTTP, l'absence de
token valide doit **échouer bruyamment**, pas désactiver l'auth silencieusement.

**Files:** `core/mcp_ref_core/factory.py`, `core/tests/test_factory_core.py`

- [ ] **Step 1 : Test — boot HTTP sans token = refus (sauf override explicite)**

```python
# core/tests/test_factory_core.py
import pytest
from mcp_ref_core import factory

def test_http_sans_token_refuse_de_demarrer(tmp_path, monkeypatch):
    monkeypatch.setenv("MCP_TRANSPORT", "http")
    monkeypatch.delenv("MCP_ALLOW_NO_AUTH", raising=False)
    empty = tmp_path / "tokens.json"        # fichier absent → aucun token
    with pytest.raises(RuntimeError, match="aucun token"):
        factory.create_mcp("X", str(empty), lambda: [])

def test_http_sans_token_autorise_si_override(tmp_path, monkeypatch, caplog):
    import logging
    monkeypatch.setenv("MCP_TRANSPORT", "http")
    monkeypatch.setenv("MCP_ALLOW_NO_AUTH", "1")
    empty = tmp_path / "tokens.json"
    with caplog.at_level(logging.WARNING, logger="mcp-ref-core"):
        factory.create_mcp("X", str(empty), lambda: [])
    assert any("AUTH DÉSACTIVÉE" in r.message for r in caplog.records)

def test_stdio_sans_token_ok(tmp_path, monkeypatch):
    monkeypatch.setenv("MCP_TRANSPORT", "stdio")   # stdio = local, auth non requise
    empty = tmp_path / "tokens.json"
    factory.create_mcp("X", str(empty), lambda: [])   # ne lève pas
```

- [ ] **Step 2 : Lancer, vérifier l'échec**

Run: `cd core && pytest tests/test_factory_core.py -v -k "sans_token or override or stdio"`
Expected: FAIL.

- [ ] **Step 3 : Implémenter le garde-fou dans `create_mcp`**

Dans `core/mcp_ref_core/factory.py`, remplacer le bloc `if verifier.tokens: … else: …` (lignes 25-30)
par :

```python
    transport = os.environ.get("MCP_TRANSPORT", "stdio")
    if verifier.tokens:
        mcp_instance = FastMCP(name, auth=verifier)
        mcp_instance._auth = verifier
    elif transport == "http" and os.environ.get("MCP_ALLOW_NO_AUTH") != "1":
        raise RuntimeError(
            f"{name}: transport HTTP mais aucun token valide dans {tokens_file}. "
            "Générez un token, ou forcez MCP_ALLOW_NO_AUTH=1 pour démarrer sans auth."
        )
    else:
        if transport == "http":
            logger.warning("%s: ⚠️ AUTH DÉSACTIVÉE (MCP_ALLOW_NO_AUTH=1) — serveur HTTP ouvert.", name)
        mcp_instance = FastMCP(name)
        mcp_instance._auth = None
```

(Le `transport` est déjà recalculé plus bas ligne 32 ; factoriser la variable en haut de fonction.)

- [ ] **Step 4 : Lancer, vérifier le succès, committer**

Run: `cd core && pytest tests/test_factory_core.py -v`

```bash
git add core/mcp_ref_core/factory.py core/tests/test_factory_core.py CHANGELOG.md
git commit -m "feat(core): fail loudly when HTTP transport starts without valid tokens"
```

---

## Self-Review

**Couverture des 48 constats :** chaque # du rapport a un verdict dans le tableau de triage. Les
problèmes réels sont couverts par Tasks 1-11 ; les faux positifs (#8, #13, #19, #38, #45, #48) sont
documentés avec preuve ; les non-actions (#4, #5, #9, #22, #32) sont justifiées.

**Constats hors-review (incident prod rgesn) :** Tasks 12 (convergence infra, bind-mount canonique +
test de parité) et 13 (fail-safe auth). Ce sont les vraies causes racines mises au jour par
l'incident — pas dans `review.md`.

**Placeholders :** aucune étape de code ne reste vide. Trois tâches (Task 3 Step 1, Task 6 Step 1,
Task 12 Step 3) comportent un point de décision/découverte explicite (API FastMCP, arbitrage produit,
question Playwright greenit) — volontaire, pas un placeholder.

**Cohérence des types :** `_get_tool_definitions() -> list[dict]`, `_guide_extra_sections() -> str`,
`fetcher_html(url, timeout)`, et la signature `create_mcp(name, tokens_file, tool_definitions_fn,
guide_extra_sections_fn)` restent stables d'une tâche à l'autre.

**Ordre d'exécution recommandé :** Task 13 + Task 12 (sécurité prod, prioritaires) → Task 2 → Task 1
→ Task 3 (dépend de 1) → Tasks 4, 5, 8, 9, 11 (indépendants) → Tasks 6, 7, 10 (points de décision).
