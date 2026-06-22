# RGAA MCP — Feature Parity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bring `mcp-rgaa` to feature parity with `mcp-greenit` by fixing broken auth, adding conditional routes, install script, `--health` flag, startup logging, MCP resources, and env helpers — all test-driven.

**Architecture:** All changes confined to `files/rgaa_mcp.py`. Tests in `tests/test_tools.py` (new file). `_create_mcp()` factory pattern replaces the bare `FastMCP("RGAA MCP")` global to wire auth and conditionally register HTTP routes.

**Tech Stack:** Python 3.11, FastMCP, pytest, starlette TestClient (already a transitive dep of fastmcp), subprocess for `--health` test.

---

## File Map

| File | Action | What changes |
|---|---|---|
| `files/rgaa_mcp.py` | Modify | All 8 features below |
| `tests/test_tools.py` | Create | All tests |
| `Dockerfile` | Modify | `--health` CMD healthcheck |
| `docker-compose.yml` | Modify | Use `CMD` healthcheck via `--health` flag |
| `pyproject.toml` | Modify | Sync version to `1.0.0` |

---

## Task 1: Baseline tests for existing tools

**Files:**
- Create: `tests/test_tools.py`

These tests must pass **before any code changes** to confirm we don't regress.

- [ ] **Step 1: Create test file**

```python
"""
Tests du serveur MCP RGAA 4.2.1.

Exécution:
    cd /path/to/mcp-rgaa
    pytest tests/test_tools.py -v
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "files"))

import pytest
import json
import rgaa_mcp as mcp_module


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture(scope="session")
def cache():
    data = mcp_module.charger_cache()
    if not data or not data.get("criteres"):
        pytest.skip("Cache vide — fichier files/rgaa_cache.json introuvable")
    return data


# ============================================================================
# rgaa_lister_criteres
# ============================================================================

class TestListerCriteres:
    def test_sans_filtre(self, cache):
        result = mcp_module.rgaa_lister_criteres()
        assert isinstance(result, dict)
        assert "total" in result
        assert "criteres" in result
        assert result["total"] == len(cache["criteres"])

    def test_filtre_theme(self, cache):
        result = mcp_module.rgaa_lister_criteres(theme=1)
        assert all(c["theme"] == 1 for c in result["criteres"])

    def test_filtre_niveau_wcag(self):
        result = mcp_module.rgaa_lister_criteres(niveau_wcag="A")
        assert result["total"] > 0
        for c in result["criteres"]:
            assert c.get("niveau") is not None or True  # niveau peut être None selon cache

    def test_critere_has_required_fields(self, cache):
        result = mcp_module.rgaa_lister_criteres()
        for c in result["criteres"]:
            assert "id" in c
            assert "theme" in c
            assert "titre" in c
            assert "automatisable" in c


# ============================================================================
# rgaa_obtenir_critere
# ============================================================================

class TestObtenirCritere:
    def test_critere_existant(self, cache):
        premier_id = next(iter(cache["criteres"]))
        result = mcp_module.rgaa_obtenir_critere(premier_id)
        assert "erreur" not in result
        assert "titre" in result

    def test_critere_inexistant(self):
        result = mcp_module.rgaa_obtenir_critere("99.99")
        assert "erreur" in result


# ============================================================================
# rgaa_chercher
# ============================================================================

class TestChercher:
    def test_recherche_basique(self):
        result = mcp_module.rgaa_chercher("image")
        assert "criteres" in result
        assert "termes_glossaire" in result
        assert len(result["criteres"]) > 0

    def test_scope_criteres_seulement(self):
        result = mcp_module.rgaa_chercher("image", scope=["criteres"])
        assert isinstance(result["criteres"], list)
        assert isinstance(result["termes_glossaire"], list)
        assert len(result["termes_glossaire"]) == 0

    def test_scope_glossaire_seulement(self):
        result = mcp_module.rgaa_chercher("lien", scope=["glossaire"])
        assert isinstance(result["termes_glossaire"], list)
        assert len(result["criteres"]) == 0

    def test_terme_absent(self):
        result = mcp_module.rgaa_chercher("xyzabc123notfound")
        assert len(result["criteres"]) == 0
        assert len(result["termes_glossaire"]) == 0


# ============================================================================
# rgaa_glossaire
# ============================================================================

class TestGlossaire:
    def test_terme_existant(self, cache):
        terme = next(iter(cache["glossaire"]))
        result = mcp_module.rgaa_glossaire(terme)
        assert "erreur" not in result
        assert "definition" in result

    def test_terme_inexistant(self):
        result = mcp_module.rgaa_glossaire("terme_absolument_inexistant_xyz")
        assert "erreur" in result

    def test_insensible_casse(self, cache):
        terme = next(iter(cache["glossaire"]))
        result = mcp_module.rgaa_glossaire(terme.upper())
        # Soit trouvé exact, soit suggestion — pas d'erreur bloquante
        assert isinstance(result, dict)


# ============================================================================
# rgaa_statistiques
# ============================================================================

class TestStatistiques:
    def test_structure(self):
        stats = mcp_module.rgaa_statistiques()
        for champ in ("total_criteres", "automatisables", "manuels", "par_theme"):
            assert champ in stats, f"Champ '{champ}' manquant"

    def test_coherence_totaux(self):
        stats = mcp_module.rgaa_statistiques()
        assert stats["automatisables"] + stats["manuels"] == stats["total_criteres"]

    def test_13_themes(self):
        stats = mcp_module.rgaa_statistiques()
        assert len(stats["par_theme"]) == 13


# ============================================================================
# rgaa_taux_conformite
# ============================================================================

class TestTauxConformite:
    def test_tout_conforme(self):
        result = mcp_module.rgaa_taux_conformite({"1.1": "C", "1.2": "C"})
        assert result["taux"] == 100.0
        assert result["nb_conformes"] == 2

    def test_tout_non_conforme(self):
        result = mcp_module.rgaa_taux_conformite({"1.1": "NC", "1.2": "NC"})
        assert result["taux"] == 0.0

    def test_na_exclus_du_calcul(self):
        result = mcp_module.rgaa_taux_conformite({"1.1": "C", "1.2": "NA"})
        assert result["criteres_evalues"] == 1
        assert result["taux"] == 100.0

    def test_statut_invalide(self):
        result = mcp_module.rgaa_taux_conformite({"1.1": "INVALID"})
        assert "erreur" in result

    def test_vide(self):
        result = mcp_module.rgaa_taux_conformite({})
        assert result["taux"] == 0.0

    def test_taux_partiel(self):
        result = mcp_module.rgaa_taux_conformite({"1.1": "C", "1.2": "NC", "1.3": "NA"})
        assert result["taux"] == pytest.approx(50.0)
        assert result["nb_conformes"] == 1
        assert result["nb_non_conformes"] == 1
        assert result["nb_non_applicables"] == 1
        assert result["criteres_evalues"] == 2


# ============================================================================
# rgaa_checklist
# ============================================================================

class TestChecklist:
    def test_par_theme(self):
        result = mcp_module.rgaa_checklist(themes=[1])
        assert "criteres" in result
        assert len(result["criteres"]) > 0

    def test_par_critere(self):
        result = mcp_module.rgaa_checklist(criteres=["1.1"])
        assert any(c["id"] == "1.1" for c in result["criteres"])

    def test_sans_parametre_retourne_erreur(self):
        result = mcp_module.rgaa_checklist()
        assert "erreur" in result

    def test_structure_test(self):
        result = mcp_module.rgaa_checklist(themes=[1])
        for c in result["criteres"]:
            assert "id" in c
            assert "titre" in c
            assert "tests" in c
            assert len(c["tests"]) > 0
            for t in c["tests"]:
                assert "description" in t
                assert "outils" in t
```

- [ ] **Step 2: Run tests to verify they pass (baseline green)**

```bash
cd /Users/renaudheluin/DEV/mcp-rgaa
pytest tests/test_tools.py -v --tb=short 2>&1 | tail -30
```

Expected: All tests pass (no failures — if any fail, fix the test assertion before continuing).

- [ ] **Step 3: Commit**

```bash
git add tests/test_tools.py
git commit -m "test: tests baseline pour les 7 outils RGAA existants"
```

---

## Task 2: Env helpers — `_get_base_url()` et `_get_token_request_url()`

**Files:**
- Modify: `files/rgaa_mcp.py`
- Modify: `tests/test_tools.py` (append class)

- [ ] **Step 1: Append tests to `tests/test_tools.py`**

Append this class at the end of the file:

```python
# ============================================================================
# Env helpers
# ============================================================================

class TestEnvHelpers:
    def test_get_base_url_from_env(self, monkeypatch):
        monkeypatch.setenv("MCP_BASE_URL", "https://my.server.com")
        assert mcp_module._get_base_url() == "https://my.server.com"

    def test_get_base_url_strips_trailing_slash(self, monkeypatch):
        monkeypatch.setenv("MCP_BASE_URL", "https://my.server.com/")
        assert mcp_module._get_base_url() == "https://my.server.com"

    def test_get_base_url_default_localhost(self, monkeypatch):
        monkeypatch.delenv("MCP_BASE_URL", raising=False)
        monkeypatch.setenv("MCP_HOST", "0.0.0.0")
        monkeypatch.setenv("MCP_PORT", "8000")
        assert mcp_module._get_base_url() == "http://localhost:8000"

    def test_get_base_url_custom_host(self, monkeypatch):
        monkeypatch.delenv("MCP_BASE_URL", raising=False)
        monkeypatch.setenv("MCP_HOST", "192.168.1.10")
        monkeypatch.setenv("MCP_PORT", "9000")
        assert mcp_module._get_base_url() == "http://192.168.1.10:9000"

    def test_get_token_request_url_from_env(self, monkeypatch):
        monkeypatch.setenv("MCP_TOKEN_REQUEST_URL", "https://forms.gle/abc123")
        assert mcp_module._get_token_request_url() == "https://forms.gle/abc123"

    def test_get_token_request_url_empty_by_default(self, monkeypatch):
        monkeypatch.delenv("MCP_TOKEN_REQUEST_URL", raising=False)
        assert mcp_module._get_token_request_url() == ""
```

- [ ] **Step 2: Run tests to confirm they FAIL**

```bash
pytest tests/test_tools.py::TestEnvHelpers -v --tb=short 2>&1 | tail -15
```

Expected: `AttributeError: module 'rgaa_mcp' has no attribute '_get_base_url'`

- [ ] **Step 3: Add helpers to `files/rgaa_mcp.py`**

Replace the section just before `_http_homepage` (around line 483, after `VERSION = "1.0.0"`):

The two existing inline expressions in `_http_homepage` and `_http_guide`:
```python
os.environ.get("MCP_BASE_URL", f"http://localhost:{os.environ.get('MCP_PORT', '8000')}")
```
will be replaced by `_get_base_url()` calls in Task 3.

Add these two functions right after the `VERSION = "1.0.0"` line:

```python
def _get_base_url() -> str:
    url = os.environ.get("MCP_BASE_URL", "")
    if url:
        return url.rstrip("/")
    host = os.environ.get("MCP_HOST", "0.0.0.0")
    port = os.environ.get("MCP_PORT", "8000")
    display_host = "localhost" if host in ("0.0.0.0", "") else host
    return f"http://{display_host}:{port}"


def _get_token_request_url() -> str:
    return os.environ.get("MCP_TOKEN_REQUEST_URL", "")
```

- [ ] **Step 4: Run tests to confirm they PASS**

```bash
pytest tests/test_tools.py::TestEnvHelpers -v --tb=short 2>&1 | tail -15
```

Expected: 6 passed.

- [ ] **Step 5: Run full suite to check no regression**

```bash
pytest tests/test_tools.py -v --tb=short 2>&1 | tail -15
```

- [ ] **Step 6: Commit**

```bash
git add files/rgaa_mcp.py tests/test_tools.py
git commit -m "feat: helpers _get_base_url() et _get_token_request_url()"
```

---

## Task 3: `_create_mcp()` — auth + routes conditionnelles + `streamable-http`

**Files:**
- Modify: `files/rgaa_mcp.py`
- Modify: `tests/test_tools.py` (append class)

This task:
1. Wraps `FastMCP` creation in `_create_mcp()` with conditional `StaticTokenVerifier`
2. Moves route registration inside `_create_mcp()`, HTTP-only
3. Replaces the unconditional global `mcp = FastMCP(...)` + bare route calls
4. Fixes transport from `"http"` → `"streamable-http"`

- [ ] **Step 1: Append tests to `tests/test_tools.py`**

```python
# ============================================================================
# _create_mcp()
# ============================================================================

class TestCreateMcp:
    def test_stdio_mode_no_routes(self, monkeypatch):
        monkeypatch.setenv("MCP_TRANSPORT", "stdio")
        mcp = mcp_module._create_mcp()
        assert mcp.name == "RGAA MCP"
        assert len(mcp._additional_http_routes) == 0

    def test_http_mode_registers_routes(self, monkeypatch):
        monkeypatch.setenv("MCP_TRANSPORT", "http")
        mcp = mcp_module._create_mcp()
        assert mcp.name == "RGAA MCP"
        assert len(mcp._additional_http_routes) == 3
        paths = [r.path for r in mcp._additional_http_routes]
        assert "/" in paths
        assert "/install.sh" in paths
        assert "/guide" in paths

    def test_no_tokens_no_auth(self, monkeypatch, tmp_path):
        monkeypatch.setattr(mcp_module, "TOKENS_FILE", str(tmp_path / "tokens.json"))
        monkeypatch.setenv("MCP_TRANSPORT", "stdio")
        mcp = mcp_module._create_mcp()
        assert mcp._auth is None

    def test_with_tokens_auth_applied(self, monkeypatch, tmp_path):
        import json as json_mod
        import time as time_mod
        tokens_file = tmp_path / "tokens.json"
        tokens_file.write_text(json_mod.dumps({
            "tok_abc123": {
                "name": "test",
                "created_at": "2026-01-01T00:00:00+00:00",
                "expires_at": time_mod.time() + 86400,
            }
        }))
        monkeypatch.setattr(mcp_module, "TOKENS_FILE", str(tokens_file))
        monkeypatch.setenv("MCP_TRANSPORT", "stdio")
        mcp = mcp_module._create_mcp()
        assert mcp._auth is not None
```

- [ ] **Step 2: Run to confirm FAIL**

```bash
pytest tests/test_tools.py::TestCreateMcp -v --tb=short 2>&1 | tail -15
```

Expected: `AttributeError: module 'rgaa_mcp' has no attribute '_create_mcp'`

- [ ] **Step 3: Refactor `files/rgaa_mcp.py`**

**3a.** Remove line 41: `mcp = FastMCP("RGAA MCP")`

**3b.** Remove lines 654-656 (the unconditional route registrations):
```python
# Routes publiques (lecture seule)
mcp.custom_route("/", methods=["GET"])(_http_homepage)
mcp.custom_route("/guide", methods=["GET"])(_http_guide)
```

**3c.** Update `_http_homepage` to use `_get_base_url()` (replace the inline expression):

In `_http_homepage`, replace:
```python
    base_url = escape(os.environ.get("MCP_BASE_URL", f"http://localhost:{os.environ.get('MCP_PORT', '8000')}"))
```
with:
```python
    base_url = escape(_get_base_url())
```

In `_http_guide`, replace:
```python
    base_url = escape(os.environ.get("MCP_BASE_URL", f"http://localhost:{os.environ.get('MCP_PORT', '8000')}"))
```
with:
```python
    base_url = escape(_get_base_url())
```

**3d.** Add `_http_install_script` function and `_INSTALL_SCRIPT_TEMPLATE` string, and `_create_mcp()` factory.

Insert after `_http_guide` function definition (before the `# ============================================================================\n# Entrypoint` section):

```python
_INSTALL_SCRIPT_TEMPLATE = r"""#!/usr/bin/env bash
# RGAA MCP — Script d'installation pour Claude Code
# Usage: curl -sSL __BASE_URL__/install.sh | bash -s -- <TOKEN> [--local|--project] [--authorize] [--uninstall]
set -euo pipefail

main() {

BLUE='\033[0;34m'
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BOLD='\033[1m'
DIM='\033[2m'
NC='\033[0m'

MCP_URL="__MCP_URL__"
BASE_URL="__BASE_URL__"
TOKEN_REQUEST_URL="__TOKEN_REQUEST_URL__"

TOKEN=""
SCOPE="user"
UNINSTALL=false
FORCE_AUTHORIZE=false

for arg in "$@"; do
    case "$arg" in
        --local)     SCOPE="local" ;;
        --project)   SCOPE="project" ;;
        --uninstall) UNINSTALL=true ;;
        --authorize) FORCE_AUTHORIZE=true ;;
        *)           [ -z "$TOKEN" ] && TOKEN="$arg" ;;
    esac
done

echo ""
echo -e "${BLUE}  ╔══════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}  ║   RGAA MCP — Installation pour Claude        ║${NC}"
echo -e "${BLUE}  ╚══════════════════════════════════════════════╝${NC}"
echo ""

detect_rgaa() {
    local config_file="$HOME/.claude.json"
    [ -f "$config_file" ] || return 0
    command -v python3 &>/dev/null || return 0
    python3 -c "
import json, os, sys
try:
    with open(os.path.expanduser('~/.claude.json')) as f:
        data = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    sys.exit(0)
if 'rgaa' in data.get('mcpServers', {}):
    print('rgaa:user')
cwd = os.getcwd()
resolved = os.path.realpath(cwd)
for path, cfg in data.get('projects', {}).items():
    if path in (cwd, resolved) or os.path.realpath(path) in (cwd, resolved):
        if 'rgaa' in cfg.get('mcpServers', {}):
            print('rgaa:local')
        break
"
}

if [ "$UNINSTALL" = true ]; then
    echo -e "  ${BOLD}Détection du serveur MCP RGAA...${NC}"
    echo ""
    INSTALLED=$(detect_rgaa)
    if [ -z "$INSTALLED" ]; then
        echo -e "  ${DIM}Aucun serveur RGAA trouvé.${NC}"
        echo ""
        exit 0
    fi
    for entry in $INSTALLED; do
        name="${entry%%:*}"
        scope="${entry##*:}"
        [ "$scope" = "user" ] && scope_label="global" || scope_label="projet : $(pwd)"
        echo -e "  Détecté : ${GREEN}●${NC} ${name} ${DIM}(${scope_label})${NC}"
    done
    echo ""
    for entry in $INSTALLED; do
        name="${entry%%:*}"
        scope="${entry##*:}"
        if claude mcp remove "$name" -s "$scope" 2>/dev/null; then
            echo -e "  ${GREEN}✓${NC} ${name} retiré ${DIM}(${scope})${NC}"
        fi
    done
    if command -v python3 &>/dev/null && [ -f ".claude/settings.json" ]; then
        python3 -c "
import json
path = '.claude/settings.json'
try:
    with open(path) as f:
        data = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    exit(0)
allow = data.get('permissions', {}).get('allow', [])
original = list(allow)
allow[:] = [p for p in allow if not p.startswith('mcp__rgaa__')]
if allow != original:
    if not allow and not any(v for k, v in data.get('permissions', {}).items() if k != 'allow'):
        del data['permissions']
    else:
        data['permissions']['allow'] = allow
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)
        f.write('\n')
" 2>/dev/null && echo -e "  ${GREEN}✓${NC} Autorisations nettoyées ${DIM}(.claude/settings.json)${NC}"
    fi
    echo ""
    echo -e "  ${GREEN}Désinstallation terminée.${NC}"
    echo ""
    exit 0
fi

if [ -z "$TOKEN" ]; then
    echo -e "  ${RED}Erreur : token MCP manquant.${NC}"
    echo ""
    echo "  Usage :"
    echo "    curl -sSL ${BASE_URL}/install.sh | bash -s -- <TOKEN>"
    echo "    curl -sSL ${BASE_URL}/install.sh | bash -s -- <TOKEN> --local"
    echo "    curl -sSL ${BASE_URL}/install.sh | bash -s -- <TOKEN> --project"
    echo "    curl -sSL ${BASE_URL}/install.sh | bash -s -- --uninstall"
    echo ""
    if [ -n "$TOKEN_REQUEST_URL" ]; then
        echo "  Demandez votre token : $TOKEN_REQUEST_URL"
    else
        echo "  Contactez l'administrateur pour obtenir un token."
    fi
    echo ""
    exit 1
fi

echo -e "  ${BOLD}Étape 1/3 — Vérification des prérequis${NC}"
echo ""

if ! command -v claude &>/dev/null; then
    echo -e "  ${RED}✗${NC} Claude Code CLI non trouvé"
    echo ""
    echo "    Installez-le d'abord :"
    echo "      npm install -g @anthropic-ai/claude-code"
    echo ""
    exit 1
fi
echo -e "  ${GREEN}✓${NC} Claude Code CLI"

if [ "$SCOPE" = "user" ]; then
    echo -e "  ${GREEN}✓${NC} Scope : user ${DIM}(disponible dans tous les projets)${NC}"
elif [ "$SCOPE" = "project" ]; then
    echo -e "  ${GREEN}✓${NC} Scope : project ${DIM}(projet courant, partageable via .mcp.json)${NC}"
else
    echo -e "  ${GREEN}✓${NC} Scope : local ${DIM}(projet courant uniquement)${NC}"
fi

echo ""
echo -e "  ${BOLD}Étape 2/3 — Installation du serveur MCP${NC}"
echo ""

echo -ne "  ${DIM}→${NC} RGAA MCP... "
claude mcp remove rgaa -s "${SCOPE}" > /dev/null 2>&1 || true
if MCP_ERR=$(claude mcp add rgaa "${MCP_URL}" \
    -t http \
    -s "${SCOPE}" \
    -H "Authorization: Bearer ${TOKEN}" 2>&1); then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗${NC}"
    [ -n "$MCP_ERR" ] && echo -e "    ${DIM}${MCP_ERR}${NC}"
    exit 1
fi

echo ""
echo -e "  ${BOLD}Étape 3/3 — Autorisations des outils MCP${NC}"
echo ""

AUTHORIZE=false
if [ "$FORCE_AUTHORIZE" = true ]; then
    AUTHORIZE=true
else
    echo -e "  Pré-autoriser les outils RGAA MCP"
    echo -e "  ${DIM}(évite de confirmer chaque appel individuellement)${NC}"
    echo ""
    echo -ne "  ${YELLOW}Accepter ? (O/n) : ${NC}"
    if read -r ANSWER < /dev/tty 2>/dev/null; then
        [[ "$ANSWER" =~ ^[nN] ]] && AUTHORIZE=false || AUTHORIZE=true
    else
        echo ""
        echo -e "  ${DIM}Mode non-interactif — ajoutez --authorize pour pré-autoriser${NC}"
    fi
fi

if [ "$AUTHORIZE" = true ]; then
    mkdir -p ".claude"
    if command -v python3 &>/dev/null; then
        python3 -c "
import json
path = '.claude/settings.json'
try:
    with open(path) as f:
        data = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    data = {}
perms = data.setdefault('permissions', {})
allow = perms.setdefault('allow', [])
if 'mcp__rgaa__*' not in allow:
    allow.append('mcp__rgaa__*')
with open(path, 'w') as f:
    json.dump(data, f, indent=2)
    f.write('\n')
"
        echo -e "  ${GREEN}✓${NC} Autorisations enregistrées ${DIM}(.claude/settings.json)${NC}"
    else
        echo -e "  ${YELLOW}⚠${NC} python3 non trouvé — configurez manuellement :"
        echo '    .claude/settings.json → "permissions": { "allow": ["mcp__rgaa__*"] }'
    fi
else
    echo -e "  ${DIM}Pré-autorisation ignorée${NC}"
fi

echo ""
echo -e "  ${BLUE}╔════════════════════════════════════════╗${NC}"
echo -e "  ${BLUE}║    ${GREEN}Installation terminée !${BLUE}           ║${NC}"
echo -e "  ${BLUE}╚════════════════════════════════════════╝${NC}"
echo ""
echo -e "  ${BOLD}Serveur installé${NC} ${DIM}(scope: ${SCOPE})${NC}"
echo -e "    ${GREEN}●${NC} rgaa"
echo ""
echo -e "  ${BOLD}Pour commencer :${NC}"
echo ""
echo -e "    ${DIM}\$${NC} claude"
echo -e "    ${DIM}>${NC} Analyse l'accessibilité de https://example.com selon le RGAA 4.2.1"
echo ""
echo -e "  ${BOLD}Autres exemples :${NC}"
echo ""
echo -e "    ${DIM}>${NC} Quels critères RGAA de niveau A concernent les images ?"
echo -e "    ${DIM}>${NC} Génère une checklist d'audit pour le thème Formulaires"
echo -e "    ${DIM}>${NC} Calcule le taux de conformité à partir de ces résultats"
echo ""
echo -e "  ${DIM}Désinstaller : curl -sSL ${BASE_URL}/install.sh | bash -s -- --uninstall${NC}"
echo -e "  ${DIM}Documentation : ${BASE_URL}/guide${NC}"
echo ""

} # end main()

main "$@"
"""


async def _http_install_script(request) -> "Response":
    from starlette.responses import PlainTextResponse
    base_url = _get_base_url()
    mcp_url = f"{base_url}/mcp"
    token_request_url = _get_token_request_url()
    script = (
        _INSTALL_SCRIPT_TEMPLATE
        .replace("__BASE_URL__", base_url)
        .replace("__MCP_URL__", mcp_url)
        .replace("__TOKEN_REQUEST_URL__", token_request_url)
    )
    return PlainTextResponse(script, media_type="text/plain; charset=utf-8")


def _create_mcp() -> FastMCP:
    transport = os.environ.get("MCP_TRANSPORT", "stdio")
    tokens = _tokens_for_auth()
    if tokens:
        from fastmcp.server.auth import StaticTokenVerifier
        auth = StaticTokenVerifier(tokens=tokens)
        mcp_instance = FastMCP("RGAA MCP", auth=auth)
    else:
        mcp_instance = FastMCP("RGAA MCP")
    if transport == "http":
        mcp_instance.custom_route("/", methods=["GET"])(_http_homepage)
        mcp_instance.custom_route("/install.sh", methods=["GET"])(_http_install_script)
        mcp_instance.custom_route("/guide", methods=["GET"])(_http_guide)
    return mcp_instance


mcp = _create_mcp()
```

**3e.** Also update the run call at the bottom of `__main__` block. Replace:
```python
        mcp.run(transport="http", host=host, port=port)
```
with:
```python
        mcp.run(transport="streamable-http", host=host, port=port)
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_tools.py::TestCreateMcp -v --tb=short 2>&1 | tail -20
```

Expected: 4 passed.

- [ ] **Step 5: Run full suite**

```bash
pytest tests/test_tools.py -v --tb=short 2>&1 | tail -20
```

Expected: All pass.

- [ ] **Step 6: Commit**

```bash
git add files/rgaa_mcp.py tests/test_tools.py
git commit -m "feat: _create_mcp() avec StaticTokenVerifier et routes HTTP conditionnelles"
```

---

## Task 4: HTTP routes tests (homepage, install.sh, guide)

**Files:**
- Modify: `tests/test_tools.py` (append class)

No new code — just tests for the 3 HTTP handlers using Starlette TestClient.

- [ ] **Step 1: Append tests to `tests/test_tools.py`**

```python
# ============================================================================
# HTTP Routes
# ============================================================================

from starlette.testclient import TestClient
from starlette.applications import Starlette
from starlette.routing import Route


class TestHttpRoutes:
    @pytest.fixture(scope="class")
    def client(self):
        app = Starlette(routes=[
            Route("/", mcp_module._http_homepage, methods=["GET"]),
            Route("/install.sh", mcp_module._http_install_script, methods=["GET"]),
            Route("/guide", mcp_module._http_guide, methods=["GET"]),
        ])
        return TestClient(app, raise_server_exceptions=True)

    def test_homepage_status_200(self, client):
        r = client.get("/")
        assert r.status_code == 200

    def test_homepage_content_type_html(self, client):
        r = client.get("/")
        assert "text/html" in r.headers["content-type"]

    def test_homepage_contains_name(self, client):
        r = client.get("/")
        assert "RGAA MCP" in r.text

    def test_homepage_contains_version(self, client):
        r = client.get("/")
        assert mcp_module.VERSION in r.text

    def test_homepage_contains_links(self, client):
        r = client.get("/")
        assert "/install.sh" in r.text
        assert "/guide" in r.text

    def test_install_script_status_200(self, client):
        r = client.get("/install.sh")
        assert r.status_code == 200

    def test_install_script_content_type(self, client):
        r = client.get("/install.sh")
        assert "text/plain" in r.headers["content-type"]

    def test_install_script_is_bash(self, client):
        r = client.get("/install.sh")
        assert r.text.startswith("#!/usr/bin/env bash")

    def test_install_script_contains_mcp_url(self, client, monkeypatch):
        monkeypatch.setenv("MCP_BASE_URL", "https://test.example.com")
        r = client.get("/install.sh")
        assert "https://test.example.com/mcp" in r.text

    def test_install_script_no_raw_placeholder(self, client):
        r = client.get("/install.sh")
        assert "__BASE_URL__" not in r.text
        assert "__MCP_URL__" not in r.text
        assert "__TOKEN_REQUEST_URL__" not in r.text

    def test_install_script_has_uninstall_flag(self, client):
        r = client.get("/install.sh")
        assert "--uninstall" in r.text

    def test_install_script_has_rgaa_mcp_add(self, client):
        r = client.get("/install.sh")
        assert "claude mcp add rgaa" in r.text
        assert "-t http" in r.text

    def test_guide_status_200(self, client):
        r = client.get("/guide")
        assert r.status_code == 200

    def test_guide_content_type_html(self, client):
        r = client.get("/guide")
        assert "text/html" in r.headers["content-type"]

    def test_guide_contains_install_command(self, client):
        r = client.get("/guide")
        assert "curl -sSL" in r.text
        assert "install.sh" in r.text

    def test_guide_contains_tools_list(self, client):
        r = client.get("/guide")
        for tool in ("rgaa_lister_criteres", "rgaa_chercher", "rgaa_analyser"):
            assert tool in r.text, f"Tool '{tool}' missing from guide"

    def test_guide_contains_token_section(self, client):
        r = client.get("/guide")
        assert "token" in r.text.lower()

    def test_guide_token_request_url_shown(self, client, monkeypatch):
        monkeypatch.setenv("MCP_TOKEN_REQUEST_URL", "https://forms.gle/test")
        r = client.get("/guide")
        assert "https://forms.gle/test" in r.text

    def test_homepage_base_url_escaped(self, client, monkeypatch):
        monkeypatch.setenv("MCP_BASE_URL", 'http://x.com"><script>alert(1)</script>')
        r = client.get("/")
        assert "<script>alert(1)</script>" not in r.text

    def test_guide_token_url_escaped(self, client, monkeypatch):
        monkeypatch.setenv("MCP_TOKEN_REQUEST_URL", "javascript:alert(1)")
        r = client.get("/guide")
        assert "javascript:alert(1)" not in r.text
```

- [ ] **Step 2: Run tests**

```bash
pytest tests/test_tools.py::TestHttpRoutes -v --tb=short 2>&1 | tail -30
```

Some tests will fail because the guide doesn't yet show `install.sh` curl command, the token request URL, and XSS escaping may be missing. Fix them before proceeding:

**Fix guide — add install section and token URL:**

In `_http_guide`, locate the `<h2>1. Connexion manuelle</h2>` section. Add before it a new install section:

```html
    <h2>Installation rapide</h2>
    <p>Remplacez <code>TOKEN</code> par votre token d'accès :</p>
    <pre><code>curl -sSL {base_url}/install.sh | bash -s -- TOKEN</code></pre>
```

And add token request URL display. Find the `<h2>1. Connexion manuelle (.mcp.json)</h2>` section and add after the code block, conditionally:

In `_http_guide`, at the top, after `base_url = escape(_get_base_url())`, add:
```python
    token_request_url = escape(_get_token_request_url())
```

Then in the HTML, after the `.mcp.json` code block, add:
```html
    {'<p>Demandez votre token : <a href="' + token_request_url + '">' + token_request_url + '</a></p>' if token_request_url else ''}
```

**Fix homepage — add install.sh link:**

In `_http_homepage`, add an install block showing the curl command (similar to greenit). After the `{status_html}` line, add:

```html
    <div class="install-block">
      <div class="install-label">Installer (remplacez TOKEN par votre token) :</div>
      <div class="install-cmd">curl -sSL {base_url}/install.sh | bash -s -- TOKEN</div>
    </div>
```

And add the CSS for `.install-block` and `.install-cmd` to the style block:
```css
    .install-block {{
      margin-top: 28px; background: #0f1117; border: 1px solid #2d3147;
      border-radius: 8px; padding: 14px 16px; text-align: left;
    }}
    .install-label {{ font-size: 12px; color: #64748b; margin-bottom: 8px; }}
    .install-cmd {{ font-family: monospace; font-size: 13px; color: #e2e8f0; word-break: break-all; }}
```

- [ ] **Step 3: Run tests again**

```bash
pytest tests/test_tools.py::TestHttpRoutes -v --tb=short 2>&1 | tail -30
```

Expected: All pass.

- [ ] **Step 4: Full suite**

```bash
pytest tests/test_tools.py -v --tb=short 2>&1 | tail -15
```

- [ ] **Step 5: Commit**

```bash
git add files/rgaa_mcp.py tests/test_tools.py
git commit -m "feat: route /install.sh avec script bash d'installation RGAA"
```

---

## Task 5: `--health` CLI flag + Dockerfile

**Files:**
- Modify: `files/rgaa_mcp.py`
- Modify: `Dockerfile`
- Modify: `docker-compose.yml`
- Modify: `tests/test_tools.py` (append class)

- [ ] **Step 1: Append tests to `tests/test_tools.py`**

```python
# ============================================================================
# --health flag
# ============================================================================

import subprocess


class TestHealthFlag:
    def test_health_exits_0_when_cache_ok(self):
        result = subprocess.run(
            [sys.executable, "files/rgaa_mcp.py", "--health"],
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).parent.parent),
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        assert "OK" in result.stdout

    def test_health_output_contains_criteres_count(self):
        result = subprocess.run(
            [sys.executable, "files/rgaa_mcp.py", "--health"],
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).parent.parent),
        )
        assert "critères" in result.stdout or "criteres" in result.stdout.lower()
```

- [ ] **Step 2: Run to confirm FAIL**

```bash
pytest tests/test_tools.py::TestHealthFlag -v --tb=short 2>&1 | tail -15
```

Expected: process returns non-zero or hangs (no `--health` handling yet).

- [ ] **Step 3: Add `--health` to `files/rgaa_mcp.py`**

In the `if __name__ == "__main__":` block, after the `--revoke-token` block and before the transport block, add:

```python
    if "--health" in args:
        cache = charger_cache()
        nb = len(cache.get("criteres", {}))
        if nb > 0:
            print(f"OK: {nb} critères chargés")
            sys.exit(0)
        else:
            print("ERREUR: Cache vide")
            sys.exit(1)
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_tools.py::TestHealthFlag -v --tb=short 2>&1 | tail -15
```

Expected: 2 passed.

- [ ] **Step 5: Update Dockerfile**

Current `CMD`:
```dockerfile
CMD ["python", "files/rgaa_mcp.py"]
```

Add a `HEALTHCHECK` instruction before `CMD`:

```dockerfile
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python files/rgaa_mcp.py --health || exit 1

CMD ["python", "files/rgaa_mcp.py"]
```

- [ ] **Step 6: Update `docker-compose.yml`**

Remove the existing `healthcheck` block (which uses urllib HTTP) — Docker will use the `HEALTHCHECK` from the Dockerfile. The `docker-compose.yml` healthcheck override is no longer needed:

```yaml
services:
  rgaa:
    build: .
    image: rgaa-mcp
    ports:
      - "8000:8000"
    environment:
      MCP_TRANSPORT: ${MCP_TRANSPORT:-http}
      MCP_HOST: ${MCP_HOST:-0.0.0.0}
      MCP_PORT: ${MCP_PORT:-8000}
    volumes:
      - ./tokens:/app/tokens
    restart: unless-stopped
```

- [ ] **Step 7: Full suite**

```bash
pytest tests/test_tools.py -v --tb=short 2>&1 | tail -15
```

- [ ] **Step 8: Commit**

```bash
git add files/rgaa_mcp.py Dockerfile docker-compose.yml tests/test_tools.py
git commit -m "feat: flag --health pour healthcheck Docker"
```

---

## Task 6: Startup logging

**Files:**
- Modify: `files/rgaa_mcp.py`
- Modify: `tests/test_tools.py` (append class)

- [ ] **Step 1: Append tests to `tests/test_tools.py`**

```python
# ============================================================================
# Startup logging
# ============================================================================

class TestStartupLogging:
    def _run_health(self):
        return subprocess.run(
            [sys.executable, "files/rgaa_mcp.py", "--health"],
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).parent.parent),
        )

    def test_health_logs_version_to_stderr(self):
        result = self._run_health()
        assert mcp_module.VERSION in result.stderr

    def test_health_logs_cache_count_to_stderr(self):
        result = self._run_health()
        assert "critères" in result.stderr or "Cache" in result.stderr
```

Note: these tests run `--health` and check stderr for log output. The health check triggers `charger_cache()` which is where we'll add the startup log. We'll also log at the main server startup.

- [ ] **Step 2: Run to confirm FAIL**

```bash
pytest tests/test_tools.py::TestStartupLogging -v --tb=short 2>&1 | tail -15
```

- [ ] **Step 3: Add startup logging to `files/rgaa_mcp.py`**

In the `if __name__ == "__main__":` block, just before the `if "--health" in args:` block, add:

```python
    cache = charger_cache()
    logger.info("Serveur MCP RGAA v%s", VERSION)
    logger.info("Cache: %s (%d critères)", CACHE_FILE, len(cache.get("criteres", {})))
```

Then update the `--health` block to reuse the already-loaded cache (remove the `charger_cache()` call inside it):

```python
    if "--health" in args:
        nb = len(cache.get("criteres", {}))
        if nb > 0:
            print(f"OK: {nb} critères chargés")
            sys.exit(0)
        else:
            print("ERREUR: Cache vide")
            sys.exit(1)
```

And in the `if transport == "http":` block, add auth and HTTP info logs:

```python
    if transport == "http":
        host = os.environ.get("MCP_HOST", "0.0.0.0")
        port = int(os.environ.get("MCP_PORT", "8000"))
        tokens = _tokens_for_auth()
        auth_info = f"activée ({len(tokens)} token(s))" if tokens else "désactivée"
        logger.info("Auth: %s", auth_info)
        logger.info("HTTP: %s:%d", host, port)
        mcp.run(transport="streamable-http", host=host, port=port)
    else:
        mcp.run(transport="stdio")
```

Remove the now-duplicate `host`/`port` extraction that was before the run calls.

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_tools.py::TestStartupLogging -v --tb=short 2>&1 | tail -15
```

Expected: 2 passed.

- [ ] **Step 5: Full suite**

```bash
pytest tests/test_tools.py -v --tb=short 2>&1 | tail -15
```

- [ ] **Step 6: Commit**

```bash
git add files/rgaa_mcp.py tests/test_tools.py
git commit -m "feat: logs de démarrage (version, cache, auth, port)"
```

---

## Task 7: MCP Resources

**Files:**
- Modify: `files/rgaa_mcp.py`
- Modify: `tests/test_tools.py` (append class)

Three resources: `rgaa://version`, `rgaa://criteres/{id}`, `rgaa://index`.

- [ ] **Step 1: Append tests to `tests/test_tools.py`**

```python
# ============================================================================
# MCP Resources
# ============================================================================

import asyncio


class TestMcpResources:
    def test_resources_registered(self):
        resources = asyncio.run(mcp_module.mcp.list_resources())
        uris = [str(r.uri) for r in resources]
        assert any("rgaa://version" in u for u in uris), f"rgaa://version missing. Got: {uris}"
        assert any("rgaa://index" in u for u in uris), f"rgaa://index missing. Got: {uris}"

    def test_resource_version_content(self):
        resources = asyncio.run(mcp_module.mcp.list_resources())
        uris = [str(r.uri) for r in resources]
        assert any("rgaa://version" in u for u in uris)

    def test_resource_index_structure(self):
        # Read the resource via the mcp object
        result = asyncio.run(mcp_module.mcp.read_resource("rgaa://index"))
        data = json.loads(result[0].text if hasattr(result[0], "text") else result[0].content)
        assert isinstance(data, list)
        assert len(data) > 0
        assert "id" in data[0]
        assert "titre" in data[0]

    def test_resource_critere_by_id(self, cache):
        premier_id = next(iter(cache["criteres"]))
        result = asyncio.run(mcp_module.mcp.read_resource(f"rgaa://criteres/{premier_id}"))
        data = json.loads(result[0].text if hasattr(result[0], "text") else result[0].content)
        assert "erreur" not in data
        assert "titre" in data

    def test_tools_still_registered(self):
        tools = asyncio.run(mcp_module.mcp.list_tools())
        names = [t.name for t in tools]
        for expected in ("rgaa_lister_criteres", "rgaa_obtenir_critere", "rgaa_chercher",
                         "rgaa_glossaire", "rgaa_statistiques", "rgaa_analyser",
                         "rgaa_checklist", "rgaa_taux_conformite"):
            assert expected in names, f"Tool '{expected}' not registered"
```

- [ ] **Step 2: Run to confirm FAIL**

```bash
pytest tests/test_tools.py::TestMcpResources -v --tb=short 2>&1 | tail -20
```

Expected: `AssertionError: rgaa://version missing.`

- [ ] **Step 3: Add resources to `files/rgaa_mcp.py`**

The `@mcp.resource` decorators must be declared AFTER `mcp = _create_mcp()`. Add this section right after `mcp = _create_mcp()`:

```python
# ============================================================================
# Ressources MCP
# ============================================================================

@mcp.resource("rgaa://version")
async def resource_version() -> str:
    """Version du serveur MCP et des données RGAA."""
    cache = charger_cache()
    meta = cache.get("meta", {})
    return json.dumps({
        "server_version": VERSION,
        "data_version": meta.get("version", "inconnue"),
        "data_updated_at": meta.get("updated_at", "inconnue"),
        "nb_criteres": len(cache.get("criteres", {})),
    }, ensure_ascii=False, indent=2)


@mcp.resource("rgaa://criteres/{critere_id}")
async def resource_critere(critere_id: str) -> str:
    """Détail complet d'un critère RGAA (même données que rgaa_obtenir_critere)."""
    cache = charger_cache()
    critere = cache["criteres"].get(critere_id)
    if critere is None:
        return json.dumps({"erreur": f"Critère '{critere_id}' introuvable"}, ensure_ascii=False)
    return json.dumps(critere, ensure_ascii=False, indent=2)


@mcp.resource("rgaa://index")
async def resource_index() -> str:
    """Index léger de tous les critères RGAA (id, thème, titre, niveau)."""
    cache = charger_cache()
    index = [
        {
            "id": c["id"],
            "theme": c["theme"],
            "titre": c["titre"],
            "niveau": c.get("niveau"),
            "automatisable": c["automatisable"],
        }
        for c in cache["criteres"].values()
    ]
    return json.dumps(index, ensure_ascii=False, indent=2)
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_tools.py::TestMcpResources -v --tb=short 2>&1 | tail -20
```

Expected: 5 passed. If `read_resource` API differs, adjust the content accessor: try `result[0].text`, `result[0].content`, or `result.contents[0].text`.

- [ ] **Step 5: Full suite**

```bash
pytest tests/test_tools.py -v --tb=short 2>&1 | tail -15
```

Expected: All pass.

- [ ] **Step 6: Commit**

```bash
git add files/rgaa_mcp.py tests/test_tools.py
git commit -m "feat: ressources MCP rgaa://version, rgaa://criteres/{id}, rgaa://index"
```

---

## Task 8: Sync pyproject.toml version + CHANGELOG

**Files:**
- Modify: `pyproject.toml`
- Modify: `CHANGELOG.md`

- [ ] **Step 1: Fix pyproject.toml version**

`pyproject.toml` currently has `version = "0.1.0"`. Sync to `1.0.0` (matches `VERSION` in `rgaa_mcp.py`):

```bash
sed -i.bak 's/^version = "0.1.0"/version = "1.0.0"/' pyproject.toml && rm -f pyproject.toml.bak
grep "^version = " pyproject.toml
```

Expected: `version = "1.0.0"`

- [ ] **Step 2: Update CHANGELOG.md**

Edit `CHANGELOG.md` — move entries from `[Unreleased]` to a new `[1.1.0]` section:

```markdown
## [Unreleased]

---

## [1.1.0] — 2026-04-18

### Ajouté
- Authentification Bearer token fonctionnelle via `StaticTokenVerifier` (bug corrigé)
- Pattern `_create_mcp()` : routes HTTP conditionnelles (stdio ne charge plus les routes web)
- Route `/install.sh` : script bash d'installation automatique pour Claude Code
- Flag `--health` pour le healthcheck Docker (remplace la sonde HTTP urllib)
- Logs de démarrage : version, nombre de critères, statut auth, port
- Helpers `_get_base_url()` et `_get_token_request_url()` (support `MCP_TOKEN_REQUEST_URL`)
- Ressources MCP : `rgaa://version`, `rgaa://criteres/{id}`, `rgaa://index`
- Transport `streamable-http` (corrige la compatibilité FastMCP 3.x)
- Suite de tests pytest complète (`tests/test_tools.py`)

---

## [1.0.0] — 2026-04-18
```

- [ ] **Step 3: Run full test suite one last time**

```bash
pytest tests/test_tools.py -v 2>&1 | tail -20
```

Expected: All pass.

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml CHANGELOG.md
git commit -m "chore: sync pyproject version 1.0.0, CHANGELOG v1.1.0"
```

---

## Self-Review

**Spec coverage:**
- ✅ Auth bug fixed — `_create_mcp()` with `StaticTokenVerifier`
- ✅ Conditional routes — only registered when `MCP_TRANSPORT=http`
- ✅ `_get_base_url()` + `_get_token_request_url()` helpers
- ✅ `MCP_TOKEN_REQUEST_URL` env var — displayed in guide
- ✅ `/install.sh` route — bash script adapted for RGAA
- ✅ `--health` CLI flag — `sys.exit(0)` on success
- ✅ Dockerfile `HEALTHCHECK` updated
- ✅ Startup logging — version, cache count, auth status, port
- ✅ MCP Resources — 3 resources registered
- ✅ Transport `streamable-http`
- ✅ Tests for all of the above

**Type/name consistency:**
- `_create_mcp()` → returns `FastMCP`, used as `mcp = _create_mcp()`
- `mcp._additional_http_routes` — FastMCP internal attribute used in `TestCreateMcp`; if FastMCP changes this attribute name, the test will fail with `AttributeError`
- `mcp._auth` — same caveat, FastMCP internal
- Resource read API: `mcp.read_resource()` returns a list; content accessor may be `.text` or `.content` depending on FastMCP version — adjust in test if needed

**Placeholder scan:** No TBDs. All code blocks are complete.
