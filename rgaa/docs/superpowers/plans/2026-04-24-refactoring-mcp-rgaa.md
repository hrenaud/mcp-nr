# Refactoring Architecture MCP RGAA Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Découper le monolithe `rgaa_mcp.py` (1589 lignes) en modules à responsabilité unique, passer Python 3.13, et ajouter la ressource `rgaa://metadata` enrichie.

**Architecture:** `data.py` gère le cache RGAA, `auth.py` gère les tokens, `routes.py` gère les routes HTTP publiques. `rgaa_mcp.py` reste le point d'entrée principal et conserve VERSION, TOKENS_FILE, les outils/prompts/ressources MCP, `_configure_mcp` et `_create_mcp`. Les symboles extraits sont re-exportés depuis `rgaa_mcp.py` pour la compatibilité des tests existants.

**Tech Stack:** Python 3.13, FastMCP, pytest, Docker, Starlette (tests HTTP)

---

## File Structure

| Action | Fichier | Responsabilité |
|--------|---------|----------------|
| Modify | `Dockerfile` | Python 3.11 → 3.13 |
| Create | `files/data.py` | charger_cache, charger_audit_types + caches globaux |
| Create | `files/auth.py` | Gestion tokens : charger, sauvegarder, vérifier, CLI |
| Create | `files/routes.py` | Routes HTTP publiques : homepage, guide, install.sh |
| Modify | `files/rgaa_mcp.py` | Importe les modules extraits, re-exporte pour compat tests, ajoute rgaa://metadata |

---

### Task 1: Python 3.13 dans Dockerfile

**Files:**
- Modify: `Dockerfile:1`

- [ ] **Step 1: Vérifier la version actuelle**

```bash
head -1 Dockerfile
```
Expected: `FROM python:3.11-slim`

- [ ] **Step 2: Mettre à jour le Dockerfile**

Remplacer la ligne 1 de `Dockerfile` :
```
FROM python:3.13-slim
```

- [ ] **Step 3: Vérifier que le CI utilise déjà 3.13**

```bash
grep "python-version" .github/workflows/ci.yml
```
Expected: `python-version: "3.13"` — aucun changement nécessaire.

- [ ] **Step 4: Tester les tests localement pour baseline**

```bash
cd /path/to/mcp-rgaa
pip install fastmcp httpx beautifulsoup4 lxml pytest pytest-asyncio
cd files && pytest ../tests/ -v
```
Expected: tous les tests passent (baseline avant refactoring).

- [ ] **Step 5: Commit**

```bash
git add Dockerfile
git commit -m "chore: upgrade Docker base image to Python 3.13"
```

---

### Task 2: Extraire data.py

**Files:**
- Create: `files/data.py`
- Modify: `files/rgaa_mcp.py` (lignes 44–67 : supprimer les fonctions et caches globaux, ajouter import)

- [ ] **Step 1: Écrire le test qui vérifiera la backward compat**

Dans `tests/test_tools.py`, ce test existe déjà (fixture `cache`) :
```python
@pytest.fixture
def cache():
    return mcp_module.charger_cache()
```
Vérifier qu'il passe avant de toucher quoi que ce soit :
```bash
cd files && pytest ../tests/ -k "cache" -v
```
Expected: PASS

- [ ] **Step 2: Créer files/data.py**

```python
import json
from pathlib import Path

_BASE_DIR = Path(__file__).parent
CACHE_FILE = _BASE_DIR / "rgaa_cache.json"
AUDIT_TYPES_FILE = _BASE_DIR / "audit_types.json"

_cache: dict | None = None
_audit_types_cache: dict | None = None


def charger_cache() -> dict:
    global _cache
    if _cache is None:
        with open(CACHE_FILE, encoding="utf-8") as f:
            _cache = json.load(f)
    return _cache


def charger_audit_types() -> dict:
    global _audit_types_cache
    if _audit_types_cache is None:
        with open(AUDIT_TYPES_FILE, encoding="utf-8") as f:
            _audit_types_cache = json.load(f)
    return _audit_types_cache
```

- [ ] **Step 3: Mettre à jour rgaa_mcp.py — retirer les fonctions, importer depuis data.py**

Dans `files/rgaa_mcp.py` :

1. Remplacer les lignes 44–67 (caches + fonctions) par :
```python
# ============================================================================
# Cache RGAA (module data)
# ============================================================================

from data import charger_cache, charger_audit_types, CACHE_FILE as _DATA_CACHE_FILE
```

2. Plus bas dans le fichier, retirer aussi la ligne `CACHE_FILE = _BASE_DIR / "rgaa_cache.json"` (ligne 39) et `AUDIT_TYPES_FILE = _BASE_DIR / "audit_types.json"` (ligne 51) — elles sont maintenant dans data.py. Garder seulement `TOKENS_FILE`.

3. Après `VERSION = "1.2.0"`, ajouter la ligne de compatibilité :
```python
# re-export pour les tests existants (mcp_module.charger_cache)
```
(charger_cache est déjà accessible via l'import from data)

- [ ] **Step 4: Vérifier les tests**

```bash
cd files && pytest ../tests/ -v
```
Expected: tous les tests passent.

- [ ] **Step 5: Commit**

```bash
git add files/data.py files/rgaa_mcp.py
git commit -m "refactor: extraire data.py (charger_cache, charger_audit_types)"
```

---

### Task 3: Extraire auth.py

**Files:**
- Create: `files/auth.py`
- Modify: `files/rgaa_mcp.py` (lignes 649–717 : remplacer par import + délégation)

- [ ] **Step 1: Identifier les fonctions à extraire**

Dans `rgaa_mcp.py` les fonctions token actuelles sont :
- `_load_tokens()` → lit `TOKENS_FILE` global
- `_save_tokens(tokens)` → écrit dans `TOKENS_FILE` global
- `_tokens_for_auth()` → appelle `_load_tokens()`, retourne dict pour StaticTokenVerifier
- `_cmd_generate_token(name, expires_days)` → CLI
- `_cmd_list_tokens()` → CLI
- `_cmd_revoke_token(token)` → CLI

La nouvelle interface prend `path: Path` en premier paramètre pour éliminer la dépendance au global `TOKENS_FILE`.

- [ ] **Step 2: Créer files/auth.py**

```python
import json
import logging
import secrets
import time
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger("rgaa-mcp")


def charger_tokens(path: Path) -> dict:
    if path.exists():
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error("Erreur tokens: %s", e)
    return {}


def sauvegarder_tokens(path: Path, tokens: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(tokens, f, ensure_ascii=False, indent=2)


def tokens_pour_auth(path: Path) -> dict:
    now = time.time()
    result = {}
    for token, info in charger_tokens(path).items():
        expires_at = info.get("expires_at")
        if expires_at and expires_at < now:
            continue
        entry = {"client_id": info.get("name", token[:8]), "scopes": ["read"]}
        if expires_at:
            entry["expires_at"] = int(expires_at)
        result[token] = entry
    return result


def construire_verifier(path: Path):
    tokens = tokens_pour_auth(path)
    if not tokens:
        return None
    from fastmcp.server.auth import StaticTokenVerifier
    return StaticTokenVerifier(tokens=tokens)


def cmd_generate_token(path: Path, name: str, expires_days: int = 365) -> None:
    token = secrets.token_urlsafe(32)
    expires_at = time.time() + expires_days * 86400
    tokens = charger_tokens(path)
    tokens[token] = {
        "name": name,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": expires_at,
    }
    sauvegarder_tokens(path, tokens)
    print(f"Token généré pour '{name}' (expire dans {expires_days} jours):")
    print(f"  {token}")


def cmd_list_tokens(path: Path) -> None:
    tokens = charger_tokens(path)
    if not tokens:
        print("Aucun token.")
        return
    now = time.time()
    for token, info in tokens.items():
        expires_at = info.get("expires_at", 0)
        statut = "EXPIRÉ" if expires_at and expires_at < now else "actif"
        print(f"  {token[:16]}...  {info.get('name')}  [{statut}]")


def cmd_revoke_token(path: Path, token: str) -> None:
    tokens = charger_tokens(path)
    if token in tokens:
        del tokens[token]
        sauvegarder_tokens(path, tokens)
        print("Token révoqué.")
    else:
        print("Token introuvable.")
```

- [ ] **Step 3: Mettre à jour rgaa_mcp.py**

1. Remplacer les lignes 649–717 (token functions + CLI commands) par :
```python
# ============================================================================
# Gestion des tokens (module auth)
# ============================================================================

import auth as _auth_module

def _load_tokens() -> dict:
    return _auth_module.charger_tokens(Path(TOKENS_FILE))

def _save_tokens(tokens: dict) -> None:
    _auth_module.sauvegarder_tokens(Path(TOKENS_FILE), tokens)

def _tokens_for_auth() -> dict:
    return _auth_module.tokens_pour_auth(Path(TOKENS_FILE))

def _cmd_generate_token(name: str, expires_days: int = 365) -> None:
    _auth_module.cmd_generate_token(Path(TOKENS_FILE), name, expires_days)

def _cmd_list_tokens() -> None:
    _auth_module.cmd_list_tokens(Path(TOKENS_FILE))

def _cmd_revoke_token(token: str) -> None:
    _auth_module.cmd_revoke_token(Path(TOKENS_FILE), token)
```

Note: les wrappers locaux préservent la signature sans argument `path` pour ne pas modifier le code d'appel dans `__main__` ni les tests.

- [ ] **Step 4: Supprimer les imports devenus inutiles dans rgaa_mcp.py**

Retirer de la section imports : `secrets`, `time`, `datetime`, `timezone` — sauf si utilisés ailleurs dans le fichier. Vérifier avec grep.

```bash
grep -n "secrets\|^import time\|from datetime" files/rgaa_mcp.py
```

Retirer uniquement ceux qui ne sont plus utilisés.

- [ ] **Step 5: Vérifier les tests**

```bash
cd files && pytest ../tests/ -v
```
Expected: tous les tests passent.

- [ ] **Step 6: Commit**

```bash
git add files/auth.py files/rgaa_mcp.py
git commit -m "refactor: extraire auth.py (gestion des tokens)"
```

---

### Task 4: Extraire routes.py

**Files:**
- Create: `files/routes.py`
- Modify: `files/rgaa_mcp.py` (supprimer `_get_base_url`, `_get_token_request_url`, `TOOLS_DESCRIPTION`, `_http_homepage`, `_http_install_script`, `_http_guide` ; ajouter import + re-exports)

La difficulté principale : `_http_homepage` utilise `VERSION` qui est défini dans `rgaa_mcp.py`. Pour éviter l'import circulaire, `routes.py` expose une variable `_VERSION = ""` que `rgaa_mcp.py` injecte après avoir défini sa propre `VERSION`.

- [ ] **Step 1: Créer files/routes.py**

Copier depuis `rgaa_mcp.py` les fonctions `_get_base_url` (ligne 727), `_get_token_request_url` (ligne 737), `TOOLS_DESCRIPTION` (ligne 741), `_http_homepage` (ligne 755), `_http_guide` (ligne 827), `_http_install_script` (vers ligne 960).

Dans routes.py, remplacer chaque usage de `VERSION` par `_VERSION` :

```python
import os
import logging

logger = logging.getLogger("rgaa-mcp")

# Injecté par rgaa_mcp.py après import : import routes as _r; _r._VERSION = VERSION
_VERSION = ""


def _get_base_url() -> str:
    url = os.environ.get("MCP_BASE_URL", "").rstrip("/")
    if url:
        return url
    host = os.environ.get("MCP_HOST", "0.0.0.0")
    port = os.environ.get("MCP_PORT", "8000")
    display_host = "localhost" if host in ("0.0.0.0", "") else host
    return f"http://{display_host}:{port}"


def _get_token_request_url() -> str:
    return os.environ.get("MCP_TOKEN_REQUEST_URL", "")


TOOLS_DESCRIPTION = [
    ("rgaa_lister_criteres", "Liste les critères RGAA, filtrables par thème"),
    ("rgaa_obtenir_critere", "Retourne le détail d'un critère (tests, WCAG, niveau)"),
    ("rgaa_chercher", "Recherche dans les critères et le glossaire par mot-clé"),
    ("rgaa_glossaire", "Retourne la définition d'un terme du glossaire RGAA"),
    ("rgaa_statistiques", "Statistiques du référentiel (niveaux, thèmes, tests)"),
    ("rgaa_analyser", "Analyse statique d'une URL (thèmes 1,2,5,6,8,9,11,12)"),
    ("rgaa_checklist", "Checklist de tests manuels par thème ou critère"),
    ("rgaa_taux_conformite", "Calcule le taux de conformité RGAA à partir des résultats"),
    ("rgaa_types_audit", "Liste les 3 types d'audit RGAA et indique lequel répond à l'obligation légale"),
    ("rgaa_criteres_audit", "Retourne la liste des critères pour un type d'audit (complet, rapide, complémentaire)"),
]


async def _http_homepage(request) -> "Response":
    from starlette.responses import HTMLResponse
    from html import escape
    from data import charger_cache
    cache = charger_cache()
    nb_criteres = len(cache.get("criteres", []))
    base_url = escape(_get_base_url())
    # ... (copie exacte du corps de _http_homepage depuis rgaa_mcp.py)
    # Remplacer VERSION par _VERSION dans le f-string HTML
```

**Note importante :** copier le corps complet des trois fonctions HTTP depuis `rgaa_mcp.py` (lignes 755–1461). La seule modification est `VERSION` → `_VERSION` dans les f-strings.

- [ ] **Step 2: Ajouter l'injection VERSION dans rgaa_mcp.py**

Dans `rgaa_mcp.py`, après la ligne `VERSION = "1.2.0"` :

```python
import routes as _routes_mod
_routes_mod._VERSION = VERSION
```

- [ ] **Step 3: Remplacer les fonctions dans rgaa_mcp.py par des re-exports**

Supprimer les fonctions `_get_base_url`, `_get_token_request_url`, `TOOLS_DESCRIPTION`, `_http_homepage`, `_http_install_script`, `_http_guide` de `rgaa_mcp.py`.

Ajouter immédiatement après l'injection VERSION :

```python
from routes import (
    _get_base_url,
    _get_token_request_url,
    TOOLS_DESCRIPTION,
    _http_homepage,
    _http_install_script,
    _http_guide,
)
```

- [ ] **Step 4: Vérifier les tests — en particulier les routes HTTP**

```bash
cd files && pytest ../tests/test_tools.py::TestHttpRoutes -v
cd files && pytest ../tests/test_tools.py::TestEnvHelpers -v
```
Expected: tous passent.

- [ ] **Step 5: Lancer la suite complète**

```bash
cd files && pytest ../tests/ -v
```
Expected: tous les tests passent.

- [ ] **Step 6: Commit**

```bash
git add files/routes.py files/rgaa_mcp.py
git commit -m "refactor: extraire routes.py (routes HTTP publiques)"
```

---

### Task 5: Ajouter la ressource rgaa://metadata

**Files:**
- Modify: `files/rgaa_mcp.py` (ajouter après la ressource `rgaa://index`)

- [ ] **Step 1: Écrire le test**

Dans `tests/test_tools.py`, ajouter une nouvelle classe de test :

```python
import asyncio

class TestMetadataResource:
    def test_metadata_resource_returns_json(self):
        result = asyncio.run(resource_metadata())
        data = json.loads(result)
        assert isinstance(data, dict)

    def test_metadata_has_required_fields(self):
        result = asyncio.run(resource_metadata())
        data = json.loads(result)
        assert "nb_criteres" in data
        assert "nb_themes" in data
        assert "taux_automatisable" in data
        assert "languages" in data
        assert "source" in data

    def test_metadata_nb_criteres(self):
        result = asyncio.run(resource_metadata())
        data = json.loads(result)
        assert data["nb_criteres"] == 106

    def test_metadata_taux_automatisable_is_float(self):
        result = asyncio.run(resource_metadata())
        data = json.loads(result)
        assert isinstance(data["taux_automatisable"], float)
        assert 0.0 <= data["taux_automatisable"] <= 100.0
```

Ajouter l'import en haut du test :
```python
from rgaa_mcp import resource_metadata
```

- [ ] **Step 2: Lancer le test pour vérifier qu'il échoue**

```bash
cd files && pytest ../tests/test_tools.py::TestMetadataResource -v
```
Expected: FAIL avec `ImportError: cannot import name 'resource_metadata'`

- [ ] **Step 3: Implémenter la ressource dans rgaa_mcp.py**

Ajouter après la ressource `rgaa://index` (vers ligne 1505) :

```python
@mcp.resource("rgaa://metadata")
async def resource_metadata() -> str:
    """Métadonnées du référentiel RGAA (langues, source, statistiques)."""
    cache = charger_cache()
    criteres = cache.get("criteres", {})
    meta = cache.get("meta", {})
    themes = cache.get("themes", {})
    nb_auto = sum(1 for c in criteres.values() if c.get("automatisable"))
    taux = round(nb_auto / len(criteres) * 100, 1) if criteres else 0.0
    return json.dumps({
        "languages": ["fr"],
        "versions": [meta.get("version", "inconnue")],
        "source": "https://github.com/DISIC/RGAA",
        "updated_at": meta.get("updated_at", "inconnue"),
        "nb_criteres": len(criteres),
        "nb_themes": len(themes),
        "taux_automatisable": taux,
    }, ensure_ascii=False, indent=2)
```

- [ ] **Step 4: Lancer les tests**

```bash
cd files && pytest ../tests/ -v
```
Expected: tous les tests passent, y compris `TestMetadataResource`.

- [ ] **Step 5: Commit**

```bash
git add files/rgaa_mcp.py tests/test_tools.py
git commit -m "feat: ajouter ressource rgaa://metadata enrichie"
```

---

### Task 6: Mettre à jour la documentation

**Files:**
- Modify: `README.md` (ajouter `rgaa://metadata` dans le tableau des ressources)
- Modify: `files/routes.py` (mettre à jour `_http_guide` : ajouter section metadata)

- [ ] **Step 1: Mettre à jour le tableau Ressources dans README.md**

Trouver le tableau des ressources dans README.md et ajouter la ligne manquante :

```markdown
| `rgaa://metadata` | Métadonnées du référentiel (langues, source, nb critères, automatisables) |
```

Ce tableau se trouve déjà dans le README à la section "Ressources disponibles" — vérifier que `rgaa://metadata` y figure (il y est déjà selon le README actuel, mais vérifier qu'il est complet).

- [ ] **Step 2: Mettre à jour _http_guide dans routes.py**

Dans la section ressources du guide HTML, s'assurer que `rgaa://metadata` apparaît avec sa description enrichie :

```html
<tr><td><code>rgaa://metadata</code></td><td>Métadonnées (langues, source, nb critères, automatisables, taux)</td></tr>
```

Rechercher dans routes.py le tableau des ressources et vérifier/ajouter cette ligne.

- [ ] **Step 3: Vérifier les tests**

```bash
cd files && pytest ../tests/ -v
```
Expected: tous passent.

- [ ] **Step 4: Commit**

```bash
git add README.md files/routes.py
git commit -m "docs: mettre à jour README et guide /guide avec rgaa://metadata"
```

---

## Self-Review

**Spec coverage :**
- [x] Python 3.13 Dockerfile → Task 1
- [x] data.py extrait → Task 2
- [x] auth.py extrait → Task 3
- [x] routes.py extrait → Task 4
- [x] rgaa://metadata → Task 5
- [x] Backward compat tests → Tasks 2–4 (re-exports, wrappers locaux)
- [x] VERSION reste dans rgaa_mcp.py → Tasks 3–4
- [x] TOKENS_FILE reste accessible depuis mcp_module → Task 3

**Placeholder scan :** aucun TBD/TODO dans ce plan.

**Type consistency :** `charger_cache()` sans paramètre dans data.py — compatible avec tous les appels actuels dans rgaa_mcp.py.
