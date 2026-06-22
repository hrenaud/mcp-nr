# Monorepo Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fusionner les repos `mcp-rgaa` et `mcp-115-greenit` dans le monorepo `mcp-nr` (déjà cloné dans `/Users/renaudheluin/DEV/ia/mcp/mcp-nr`), avec un package partagé `core/` pour `auth.py`, `routes.py` et `_helpers.py`, et préparer l'accueil d'un troisième MCP (RGESN).

**Architecture:** Un seul repo Git contient trois packages indépendants (`greenit/`, `rgaa/`, `rgesn/`) et un package partagé `core/`. Chaque MCP importe `core` comme dépendance locale via `pip install -e ../../core`. Les Dockerfiles copient `core/` aux côtés des `files/` de chaque MCP. Le CI utilise une matrice GitHub Actions pour tester et builder chaque MCP indépendamment.

**Tech Stack:** Python 3.13, fastmcp ≥ 2.0, hatchling, pytest, Docker, GitHub Actions matrix builds.

## Global Constraints

- Python ≥ 3.11 dans tous les pyproject.toml
- fastmcp ≥ 2.0, httpx ≥ 0.27 dans toutes les dépendances
- Les imports dans les fichiers `*_mcp.py` passent de `from auth import ...` à `from mcp_ref_core.auth import ...`
- `core/` est le package partagé, nom de distribution : `mcp-ref-core`
- Chaque MCP garde son propre Dockerfile, docker-compose.yml, pyproject.toml, tests/ et .github/workflows/
- Les données (JSON cache, metadata) restent dans chaque MCP — elles ne sont pas partagées
- Ne pas casser les images Docker existantes publiées sur GHCR
- Utiliser `trash` pour supprimer des fichiers, jamais `rm`

---

## Structure cible

```
mcp-nr/                           ← repo Git existant (https://github.com/hrenaud/mcp-nr.git)
  core/                           ← package partagé
    mcp_ref_core/
      __init__.py
      auth.py                     ← version greenit (la plus complète)
      routes.py                   ← identique dans les deux projets
      _helpers.py                 ← identique dans les deux projets
    pyproject.toml
    tests/
      test_auth.py                ← tests existants de rgaa/tests/test_auth.py

  greenit/
    files/
      greenit_mcp.py              ← imports mis à jour
      data.py
      greenit_cache.json
      greenit_metadata.json
      preparer_donnees_final.py
    tests/                        ← tests existants, chemins mis à jour
    Dockerfile                    ← COPY core/ ajouté
    docker-compose.yml
    pyproject.toml                ← dépendance sur core local
    .github/workflows/
      ci.yml
      release.yml
    CHANGELOG.md
    README.md

  rgaa/
    files/
      rgaa_mcp.py                 ← imports mis à jour
      data.py
      rgaa_cache.json
      analyseur.py
      preparer_donnees.py
    tests/                        ← tests existants, chemins mis à jour
    Dockerfile                    ← COPY core/ ajouté
    docker-compose.yml
    pyproject.toml
    .github/workflows/
      ci.yml
      release.yml
    CHANGELOG.md
    README.md

  rgesn/                          ← scaffold vide pour le futur
    files/
      .gitkeep
    tests/
      .gitkeep
    Dockerfile                    ← template depuis greenit
    docker-compose.yml
    pyproject.toml
    CHANGELOG.md
    README.md

  README.md                       ← index du monorepo
  .gitignore
```

---

## Task 1 : Créer le repo monorepo et le package `core/`

**Files:**

- Create: `mcp-nr/core/mcp_ref_core/__init__.py`
- Create: `mcp-nr/core/mcp_ref_core/auth.py`
- Create: `mcp-nr/core/mcp_ref_core/routes.py`
- Create: `mcp-nr/core/mcp_ref_core/_helpers.py`
- Create: `mcp-nr/core/pyproject.toml`
- Create: `mcp-nr/core/tests/test_auth_core.py`

**Interfaces:**

- Produit: `from mcp_ref_core.auth import DynamicTokenVerifier, construire_verifier, tokens_pour_auth, cmd_generate_token, cmd_list_tokens, cmd_revoke_token`
- Produit: `from mcp_ref_core.routes import _get_base_url, _get_token_request_url, _get_tool_definitions, _http_homepage, _http_guide, _check_admin_auth, _http_admin_list_tokens, _http_admin_create_token, _http_admin_get_token, _http_admin_update_token, _http_admin_delete_token, _http_install_script`
- Produit: `from mcp_ref_core._helpers import validate_themes, validate_score_range, validate_nonnegative`

- [ ] **Step 1 : Vérifier le repo monorepo existant**

Le repo `mcp-nr` est déjà cloné depuis `https://github.com/hrenaud/mcp-nr.git`.

```bash
cd /Users/renaudheluin/DEV/ia/mcp/mcp-nr
git status
```

Expected : working tree clean, branche `main`.

- [ ] **Step 2 : Créer la structure de répertoires**

```bash
mkdir -p core/mcp_ref_core core/tests
```

- [ ] **Step 3 : Créer `core/pyproject.toml`**

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "mcp-ref-core"
version = "1.0.0"
requires-python = ">=3.11"
dependencies = [
    "fastmcp>=2.0",
    "httpx>=0.27",
]

[project.optional-dependencies]
dev = ["pytest>=8.0", "pytest-asyncio>=0.23", "coverage>=7.0"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
```

- [ ] **Step 4 : Créer `core/mcp_ref_core/__init__.py`**

```python
from .auth import DynamicTokenVerifier, construire_verifier, tokens_pour_auth
from .routes import _get_base_url, _get_token_request_url
from ._helpers import validate_themes, validate_score_range, validate_nonnegative

__all__ = [
    "DynamicTokenVerifier",
    "construire_verifier",
    "tokens_pour_auth",
    "_get_base_url",
    "_get_token_request_url",
    "validate_themes",
    "validate_score_range",
    "validate_nonnegative",
]
```

- [ ] **Step 5 : Copier `auth.py` depuis greenit (version la plus complète)**

```bash
cp /Users/renaudheluin/DEV/DEV_GREENIT/refs/mcp-115-greenit/files/auth.py \
   /Users/renaudheluin/DEV/ia/mcp/mcp-nr/core/mcp_ref_core/auth.py
```

Puis remplacer la ligne du logger dans `auth.py` :

```python
# Avant
logger = logging.getLogger("greenit-mcp")
# Après
logger = logging.getLogger("mcp-ref-core")
```

- [ ] **Step 6 : Copier `routes.py` et `_helpers.py`**

```bash
cp /Users/renaudheluin/DEV/DEV_GREENIT/refs/mcp-115-greenit/files/routes.py \
   /Users/renaudheluin/DEV/ia/mcp/mcp-nr/core/mcp_ref_core/routes.py

cp /Users/renaudheluin/DEV/DEV_GREENIT/refs/mcp-115-greenit/files/_helpers.py \
   /Users/renaudheluin/DEV/ia/mcp/mcp-nr/core/mcp_ref_core/_helpers.py
```

- [ ] **Step 7 : Écrire un test de fumée pour `core/`**

Créer `core/tests/test_auth_core.py` :

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp_ref_core.auth import DynamicTokenVerifier, construire_verifier
from mcp_ref_core._helpers import validate_themes, validate_score_range, validate_nonnegative


def test_dynamic_token_verifier_instantiates(tmp_path):
    verifier = DynamicTokenVerifier(tmp_path / "tokens.json")
    assert verifier is not None


def test_construire_verifier_returns_none_without_file(tmp_path):
    result = construire_verifier(tmp_path / "tokens.json")
    assert result is None


def test_validate_nonnegative_accepts_zero():
    validate_nonnegative(0, "dom")  # ne doit pas lever d'exception


def test_validate_score_range_rejects_negative():
    import pytest
    from fastmcp.exceptions import ToolError
    with pytest.raises(ToolError):
        validate_score_range(-1, "score")
```

- [ ] **Step 8 : Vérifier que les tests échouent (imports manquants attendus)**

```bash
cd /Users/renaudheluin/DEV/ia/mcp/mcp-nr/core
pip install -e ".[dev]" -q
pytest tests/ -v
```

Expected : les tests passent si l'import fonctionne, ou FAIL avec ImportError si quelque chose manque.

- [ ] **Step 9 : Corriger les imports si nécessaire et relancer**

```bash
pytest tests/ -v
```

Expected : 4 tests PASSED.

- [ ] **Step 10 : Commit**

```bash
cd /Users/renaudheluin/DEV/ia/mcp/mcp-nr
git add core/
git commit -m "feat: add shared core package mcp-ref-core"
```

---

## Task 2 : Migrer `greenit` dans le monorepo

**Files:**

- Create: `mcp-nr/greenit/` (copie de mcp-115-greenit sans les fichiers partagés)
- Modify: `mcp-nr/greenit/files/greenit_mcp.py` — imports vers `mcp_ref_core`
- Modify: `mcp-nr/greenit/Dockerfile` — COPY core/
- Modify: `mcp-nr/greenit/pyproject.toml` — dépendance core locale

**Interfaces:**

- Consomme: `from mcp_ref_core.auth import ...`, `from mcp_ref_core.routes import ...`, `from mcp_ref_core._helpers import ...`

- [ ] **Step 1 : Copier le projet greenit dans le monorepo**

```bash
cp -r /Users/renaudheluin/DEV/DEV_GREENIT/refs/mcp-115-greenit \
      /Users/renaudheluin/DEV/ia/mcp/mcp-nr/greenit
```

Supprimer les fichiers qui vont dans `core/` :

```bash
trash /Users/renaudheluin/DEV/ia/mcp/mcp-nr/greenit/files/auth.py
trash /Users/renaudheluin/DEV/ia/mcp/mcp-nr/greenit/files/routes.py
trash /Users/renaudheluin/DEV/ia/mcp/mcp-nr/greenit/files/_helpers.py
```

Supprimer les artefacts inutiles dans le monorepo :

```bash
trash /Users/renaudheluin/DEV/ia/mcp/mcp-nr/greenit/.git
trash /Users/renaudheluin/DEV/ia/mcp/mcp-nr/greenit/.venv
trash /Users/renaudheluin/DEV/ia/mcp/mcp-nr/greenit/.venv-py313
trash /Users/renaudheluin/DEV/ia/mcp/mcp-nr/greenit/htmlcov
trash /Users/renaudheluin/DEV/ia/mcp/mcp-nr/greenit/.coverage
trash /Users/renaudheluin/DEV/ia/mcp/mcp-nr/greenit/.worktrees
```

- [ ] **Step 2 : Mettre à jour `greenit/pyproject.toml`**

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "mcp-greenit"
version = "2.5.1"
requires-python = ">=3.11"
dependencies = [
    "fastmcp>=2.0",
    "httpx>=0.27",
    "mcp-ref-core",
]

[project.optional-dependencies]
dev = ["pytest>=8.0", "pytest-asyncio>=0.23", "coverage>=7.0"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
```

- [ ] **Step 3 : Mettre à jour les imports dans `greenit/files/greenit_mcp.py`**

Remplacer :

```python
from auth import construire_verifier, tokens_pour_auth, cmd_generate_token, cmd_list_tokens, cmd_revoke_token
from _helpers import validate_themes, validate_score_range, validate_nonnegative
import routes
```

Par :

```python
from mcp_ref_core.auth import construire_verifier, tokens_pour_auth, cmd_generate_token, cmd_list_tokens, cmd_revoke_token
from mcp_ref_core._helpers import validate_themes, validate_score_range, validate_nonnegative
from mcp_ref_core import routes
```

- [ ] **Step 4 : Mettre à jour `greenit/Dockerfile`**

```dockerfile
FROM python:3.13-slim

ENV DEBIAN_FRONTEND=noninteractive

WORKDIR /app

RUN pip install --no-cache-dir fastmcp httpx

COPY core/mcp_ref_core/ ./mcp_ref_core/
COPY greenit/files/greenit_mcp.py .
COPY greenit/files/data.py .
COPY greenit/files/greenit_cache.json .
COPY greenit/files/greenit_metadata.json .

ENV PYTHONUNBUFFERED=1
ENV MCP_TRANSPORT=http
ENV MCP_HOST=0.0.0.0
ENV MCP_PORT=8000

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python greenit_mcp.py --health

ENTRYPOINT ["python", "greenit_mcp.py"]
```

Note : le Dockerfile doit être buildé depuis la racine du monorepo (`docker build -f greenit/Dockerfile .`).

- [ ] **Step 5 : Installer core et tester greenit**

```bash
cd /Users/renaudheluin/DEV/ia/mcp/mcp-nr
pip install -e core/ -q
cd greenit
pip install -e ".[dev]" -q
cd files
pytest ../tests/ -v --tb=short 2>&1 | tail -20
```

Expected : même nombre de tests passants qu'avant la migration.

- [ ] **Step 6 : Tester le build Docker depuis la racine**

```bash
cd /Users/renaudheluin/DEV/ia/mcp/mcp-nr
docker build -f greenit/Dockerfile -t greenit-mcp-mono .
docker run --rm greenit-mcp-mono --health
```

Expected : `OK` sur stdout, exit code 0.

- [ ] **Step 7 : Commit**

```bash
cd /Users/renaudheluin/DEV/ia/mcp/mcp-nr
git add greenit/
git commit -m "feat: migrate greenit MCP into monorepo"
```

---

## Task 3 : Migrer `rgaa` dans le monorepo

**Files:**

- Create: `mcp-nr/rgaa/` (copie de mcp-rgaa sans les fichiers partagés)
- Modify: `mcp-nr/rgaa/files/rgaa_mcp.py` — imports vers `mcp_ref_core`
- Modify: `mcp-nr/rgaa/Dockerfile` — COPY core/
- Modify: `mcp-nr/rgaa/pyproject.toml`

**Interfaces:**

- Consomme: `from mcp_ref_core.auth import ...`, `from mcp_ref_core.routes import ...`, `from mcp_ref_core._helpers import ...`

- [ ] **Step 1 : Copier le projet rgaa dans le monorepo**

```bash
cp -r /Users/renaudheluin/DEV/mcp-rgaa \
      /Users/renaudheluin/DEV/ia/mcp/mcp-nr/rgaa

trash /Users/renaudheluin/DEV/ia/mcp/mcp-nr/rgaa/files/auth.py
trash /Users/renaudheluin/DEV/ia/mcp/mcp-nr/rgaa/files/routes.py
trash /Users/renaudheluin/DEV/ia/mcp/mcp-nr/rgaa/files/_helpers.py
trash /Users/renaudheluin/DEV/ia/mcp/mcp-nr/rgaa/.git
trash /Users/renaudheluin/DEV/ia/mcp/mcp-nr/rgaa/.venv-py313
trash /Users/renaudheluin/DEV/ia/mcp/mcp-nr/rgaa/htmlcov
trash /Users/renaudheluin/DEV/ia/mcp/mcp-nr/rgaa/.coverage
trash /Users/renaudheluin/DEV/ia/mcp/mcp-nr/rgaa/.worktrees
```

- [ ] **Step 2 : Mettre à jour `rgaa/pyproject.toml`**

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "mcp-rgaa"
version = "1.2.2"
requires-python = ">=3.11"
dependencies = [
    "fastmcp>=2.0",
    "httpx>=0.27",
    "beautifulsoup4>=4.12",
    "lxml>=5.0",
    "mcp-ref-core",
]

[project.optional-dependencies]
dev = ["pytest>=8.0", "pytest-asyncio>=0.23", "coverage>=7.0"]

[tool.hatch.build.targets.wheel]
packages = ["files"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
```

- [ ] **Step 3 : Identifier et mettre à jour les imports dans `rgaa/files/rgaa_mcp.py`**

```bash
grep -n "from auth\|from _helpers\|import routes" \
  /Users/renaudheluin/DEV/ia/mcp/mcp-nr/rgaa/files/rgaa_mcp.py
```

Remplacer chaque occurrence trouvée :

```python
# Avant
from auth import construire_verifier, tokens_pour_auth, cmd_generate_token, cmd_list_tokens, cmd_revoke_token
from _helpers import validate_themes, validate_score_range, validate_nonnegative
import routes

# Après
from mcp_ref_core.auth import construire_verifier, tokens_pour_auth, cmd_generate_token, cmd_list_tokens, cmd_revoke_token
from mcp_ref_core._helpers import validate_themes, validate_score_range, validate_nonnegative
from mcp_ref_core import routes
```

- [ ] **Step 4 : Mettre à jour `rgaa/Dockerfile`**

```dockerfile
FROM python:3.13-slim

WORKDIR /app

RUN pip install --no-cache-dir fastmcp httpx beautifulsoup4 lxml

COPY core/mcp_ref_core/ ./mcp_ref_core/
COPY rgaa/files/ ./files/
COPY rgaa/tokens/.gitkeep ./tokens/.gitkeep

VOLUME ["/app/tokens"]

ENV MCP_TRANSPORT=http
ENV MCP_HOST=0.0.0.0
ENV MCP_PORT=8000

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python files/rgaa_mcp.py --health || exit 1

ENTRYPOINT ["python", "files/rgaa_mcp.py"]
```

- [ ] **Step 5 : Vérifier les imports dans les fichiers de test rgaa**

```bash
grep -rn "from auth\|from _helpers\|import routes" \
  /Users/renaudheluin/DEV/ia/mcp/mcp-nr/rgaa/tests/
```

Mettre à jour chaque occurrence trouvée avec les imports `mcp_ref_core`.

- [ ] **Step 6 : Tester rgaa**

```bash
cd /Users/renaudheluin/DEV/ia/mcp/mcp-nr
pip install -e core/ -q
cd rgaa/files
pytest ../tests/ -v --tb=short 2>&1 | tail -20
```

Expected : même nombre de tests passants qu'avant.

- [ ] **Step 7 : Tester le build Docker**

```bash
cd /Users/renaudheluin/DEV/ia/mcp/mcp-nr
docker build -f rgaa/Dockerfile -t rgaa-mcp-mono .
docker run --rm rgaa-mcp-mono --health
```

Expected : `OK`, exit code 0.

- [ ] **Step 8 : Commit**

```bash
cd /Users/renaudheluin/DEV/ia/mcp/mcp-nr
git add rgaa/
git commit -m "feat: migrate rgaa MCP into monorepo"
```

---

## Task 4 : Scaffolder `rgesn` (MCP vide prêt à développer)

**Files:**

- Create: `mcp-nr/rgesn/files/rgesn_mcp.py` — squelette minimal
- Create: `mcp-nr/rgesn/pyproject.toml`
- Create: `mcp-nr/rgesn/Dockerfile`
- Create: `mcp-nr/rgesn/docker-compose.yml`
- Create: `mcp-nr/rgesn/tests/test_smoke.py`
- Create: `mcp-nr/rgesn/CHANGELOG.md`

**Interfaces:**

- Consomme: `from mcp_ref_core.auth import construire_verifier, tokens_pour_auth`
- Consomme: `from mcp_ref_core import routes`

- [ ] **Step 1 : Créer la structure rgesn**

```bash
mkdir -p /Users/renaudheluin/DEV/ia/mcp/mcp-nr/rgesn/files
mkdir -p /Users/renaudheluin/DEV/ia/mcp/mcp-nr/rgesn/tests
mkdir -p /Users/renaudheluin/DEV/ia/mcp/mcp-nr/rgesn/tokens
touch /Users/renaudheluin/DEV/ia/mcp/mcp-nr/rgesn/tokens/.gitkeep
```

- [ ] **Step 2 : Créer `rgesn/pyproject.toml`**

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "mcp-rgesn"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "fastmcp>=2.0",
    "httpx>=0.27",
    "mcp-ref-core",
]

[project.optional-dependencies]
dev = ["pytest>=8.0", "pytest-asyncio>=0.23", "coverage>=7.0"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
```

- [ ] **Step 3 : Créer `rgesn/files/rgesn_mcp.py` (squelette)**

```python
"""
Serveur MCP pour le référentiel RGESN (Référentiel Général d'Écoconception de Services Numériques)
"""

from fastmcp import FastMCP
from pathlib import Path
import logging
import sys

from mcp_ref_core.auth import construire_verifier, tokens_pour_auth
from mcp_ref_core import routes

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
    stream=sys.stderr,
)
logger = logging.getLogger("rgesn-mcp")

VERSION = "0.1.0"

_BASE_DIR = Path(__file__).parent
TOKENS_FILE = str(_BASE_DIR / "tokens" / "tokens.json")

auth_tokens = tokens_pour_auth(Path(TOKENS_FILE))
verifier = construire_verifier(Path(TOKENS_FILE))

mcp = FastMCP(
    "RGESN — Référentiel Général d'Écoconception de Services Numériques",
    auth=verifier,
)

routes.VERSION = VERSION
routes.register_routes(mcp, tokens_file=Path(TOKENS_FILE))

# TODO: Ajouter les outils RGESN ici

if __name__ == "__main__":
    import os
    transport = os.environ.get("MCP_TRANSPORT", "stdio")
    if "--health" in sys.argv:
        print("OK")
        sys.exit(0)
    mcp.run(
        transport=transport,
        host=os.environ.get("MCP_HOST", "0.0.0.0"),
        port=int(os.environ.get("MCP_PORT", "8000")),
    )
```

- [ ] **Step 4 : Créer `rgesn/tests/test_smoke.py`**

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "files"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "core"))

def test_import_rgesn_mcp():
    import rgesn_mcp
    assert rgesn_mcp.VERSION == "0.1.0"

def test_mcp_instance_exists():
    import rgesn_mcp
    assert rgesn_mcp.mcp is not None
```

- [ ] **Step 5 : Créer `rgesn/Dockerfile`**

```dockerfile
FROM python:3.13-slim

WORKDIR /app

RUN pip install --no-cache-dir fastmcp httpx

COPY core/mcp_ref_core/ ./mcp_ref_core/
COPY rgesn/files/ ./files/
COPY rgesn/tokens/.gitkeep ./tokens/.gitkeep

VOLUME ["/app/tokens"]

ENV MCP_TRANSPORT=http
ENV MCP_HOST=0.0.0.0
ENV MCP_PORT=8000

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python files/rgesn_mcp.py --health || exit 1

ENTRYPOINT ["python", "files/rgesn_mcp.py"]
```

- [ ] **Step 6 : Créer `rgesn/docker-compose.yml`**

```yaml
services:
  rgesn:
    build:
      context: ..
      dockerfile: rgesn/Dockerfile
    image: rgesn-mcp
    ports:
      - "8002:8000"
    environment:
      MCP_TRANSPORT: ${MCP_TRANSPORT:-http}
      MCP_HOST: ${MCP_HOST:-0.0.0.0}
      MCP_PORT: ${MCP_PORT:-8000}
      MCP_BASE_URL: ${MCP_BASE_URL:-http://localhost:8002}
      MCP_TOKEN_REQUEST_URL: ${MCP_TOKEN_REQUEST_URL:-}
      ADMIN_TOKEN: ${ADMIN_TOKEN:-}
    volumes:
      - rgesn_tokens:/app/tokens

volumes:
  rgesn_tokens:
```

- [ ] **Step 7 : Créer `rgesn/CHANGELOG.md`**

```markdown
# Changelog

## [Unreleased]

### Added

- Scaffold initial du serveur MCP RGESN
```

- [ ] **Step 8 : Tester le smoke test**

```bash
cd /Users/renaudheluin/DEV/ia/mcp/mcp-nr/rgesn/files
pytest ../tests/test_smoke.py -v
```

Expected : 2 tests PASSED.

- [ ] **Step 9 : Commit**

```bash
cd /Users/renaudheluin/DEV/ia/mcp/mcp-nr
git add rgesn/
git commit -m "feat: scaffold rgesn MCP"
```

---

## Task 5 : CI monorepo (GitHub Actions matrix)

**Files:**

- Create: `mcp-nr/.github/workflows/ci.yml`
- Create: `mcp-nr/.github/workflows/release-greenit.yml`
- Create: `mcp-nr/.github/workflows/release-rgaa.yml`
- Create: `mcp-nr/.gitignore`
- Create: `mcp-nr/README.md`

- [ ] **Step 1 : Créer `.gitignore` racine**

```
__pycache__/
*.py[cod]
.venv/
.venv-py313/
*.egg-info/
dist/
.coverage
htmlcov/
.DS_Store
tokens/*.json
!tokens/.gitkeep
*.json.cover
```

- [ ] **Step 2 : Créer `.github/workflows/ci.yml`**

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        mcp: [greenit, rgaa, rgesn]
        include:
          - mcp: greenit
            extra_deps: ""
            test_dir: greenit/tests
            work_dir: greenit/files
          - mcp: rgaa
            extra_deps: "beautifulsoup4 lxml"
            test_dir: rgaa/tests
            work_dir: rgaa/files
          - mcp: rgesn
            extra_deps: ""
            test_dir: rgesn/tests
            work_dir: rgesn/files

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.13"

      - name: Install core
        run: pip install -e core/

      - name: Install MCP dependencies
        run: pip install fastmcp httpx pytest pytest-asyncio ${{ matrix.extra_deps }}

      - name: Run tests
        working-directory: ${{ matrix.work_dir }}
        run: pytest ../../${{ matrix.test_dir }} -v

  docker-build:
    runs-on: ubuntu-latest
    needs: test
    strategy:
      matrix:
        mcp: [greenit, rgaa, rgesn]
        include:
          - mcp: greenit
            image: greenit-mcp
          - mcp: rgaa
            image: rgaa-mcp
          - mcp: rgesn
            image: rgesn-mcp

    steps:
      - uses: actions/checkout@v4

      - name: Build Docker image
        run: docker build -f ${{ matrix.mcp }}/Dockerfile -t ${{ matrix.image }} .

      - name: Smoke test
        run: docker run --rm ${{ matrix.image }} --health
```

- [ ] **Step 3 : Créer `README.md` racine**

````markdown
# MCP Référentiels

Monorepo contenant les serveurs MCP pour les référentiels numériques responsables.

## MCPs disponibles

| MCP                   | Description                                                         | Port local |
| --------------------- | ------------------------------------------------------------------- | ---------- |
| [greenit](./greenit/) | Référentiel GreenIT — bonnes pratiques éco-conception web           | 8000       |
| [rgaa](./rgaa/)       | RGAA — Référentiel Général d'Accessibilité pour les Administrations | 8001       |
| [rgesn](./rgesn/)     | RGESN — Référentiel Général d'Écoconception de Services Numériques  | 8002       |

## Package partagé

Le dossier [`core/`](./core/) contient le package `mcp-ref-core` partagé entre tous les MCPs :

- `auth.py` — gestion des tokens d'authentification
- `routes.py` — routes HTTP communes (homepage, guide, admin API)
- `_helpers.py` — fonctions de validation

## Développement

```bash
# Installer le core en mode éditable
pip install -e core/

# Tester un MCP spécifique
cd greenit/files && pytest ../tests/ -v

# Builder une image Docker (depuis la racine)
docker build -f greenit/Dockerfile -t greenit-mcp .
```
````

````

- [ ] **Step 4 : Commit final**

```bash
cd /Users/renaudheluin/DEV/ia/mcp/mcp-nr
git add .github/ .gitignore README.md
git commit -m "chore: add monorepo CI and root README"
````

---

## Self-Review

### Spec coverage

- ✅ Package `core/` partagé avec `auth.py`, `routes.py`, `_helpers.py`
- ✅ Migration greenit avec tests et Docker
- ✅ Migration rgaa avec tests et Docker
- ✅ Scaffold rgesn prêt à développer
- ✅ CI matrix GitHub Actions
- ✅ `auth.py` greenit (version la plus complète) utilisée dans core
- ✅ Dockerfiles buildés depuis la racine du monorepo
- ✅ Ports distincts : greenit=8000, rgaa=8001, rgesn=8002

### Points d'attention

- Le `routes.py` actuel accède peut-être à des variables globales spécifiques à chaque MCP (VERSION, TOKENS_FILE). Vérifier lors de la Task 2/3 que `routes.register_routes()` existe bien, ou adapter.
- Les tests existants de rgaa importent `from auth import ...` directement — la Task 3 Step 5 demande de les mettre à jour.
- Les repos originaux (`mcp-rgaa`, `mcp-115-greenit`) ne sont **pas supprimés** par ce plan — c'est intentionnel, la décision d'archivage/suppression revient à l'utilisateur.
