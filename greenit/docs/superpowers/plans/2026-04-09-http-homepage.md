# HTTP Homepage, Install Script & Guide — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ajouter 3 routes HTTP publiques au serveur MCP GreenIT (homepage `/`, script d'installation `/install.sh`, guide `/guide`) actives uniquement en mode HTTP.

**Architecture:** Les handlers sont des fonctions async Starlette ajoutées à FastMCP via le paramètre `custom_routes` du constructeur `FastMCP(...)`. Le script bash est un template Python avec des placeholders `__BASE_URL__` etc. remplacés à la volée. Deux nouvelles variables d'env configurent l'URL publique et le lien du formulaire de demande de token.

**Tech Stack:** FastMCP 2.x (`custom_routes`), Starlette (`Request`, `HTMLResponse`, `PlainTextResponse`), pytest + `starlette.testclient.TestClient`

**Spec:** `docs/superpowers/specs/2026-04-09-http-homepage-design.md`

---

## File Map

| Fichier | Action | Rôle |
|---|---|---|
| `files/greenit_mcp_final.py` | Modifier | Ajouter helpers env, template script, 3 handlers, modifier `_create_mcp()` |
| `docker-compose.yml` | Modifier | Ajouter `MCP_BASE_URL` et `MCP_TOKEN_REQUEST_URL` |
| `tests/test_tools.py` | Modifier | Ajouter `TestHttpRoutes` |

---

## Task 1 : Helpers env + vérification FastMCP custom_routes

**Files:**
- Modify: `files/greenit_mcp_final.py` (après la fonction `_tokens_for_auth`, avant `_create_mcp`)
- Modify: `tests/test_tools.py`

- [ ] **Step 1 : Vérifier la version FastMCP installée**

```bash
pip show fastmcp
```

Expected : version ≥ 2.0. Si < 2.0, mettre à jour : `pip install --upgrade fastmcp`.

Vérifier que `FastMCP` accepte `custom_routes` en lisant le source :

```bash
python3 -c "import inspect, fastmcp; print(inspect.signature(fastmcp.FastMCP.__init__))"
```

Expected : la signature inclut `custom_routes` ou `**kwargs`. Si `custom_routes` n'est pas dans la signature, noter et consulter la doc FastMCP sur le montage de routes custom (alternative : `mcp.http_app()` + wrapper Starlette).

- [ ] **Step 2 : Écrire le test pour `_get_base_url`**

Dans `tests/test_tools.py`, ajouter après les imports existants :

```python
import os


class TestEnvHelpers:
    def test_get_base_url_from_env(self, monkeypatch):
        monkeypatch.setenv("MCP_BASE_URL", "https://my.server.com")
        # Forcer le re-calcul (la fonction lit os.environ à chaque appel)
        result = mcp_module._get_base_url()
        assert result == "https://my.server.com"

    def test_get_base_url_strips_trailing_slash(self, monkeypatch):
        monkeypatch.setenv("MCP_BASE_URL", "https://my.server.com/")
        result = mcp_module._get_base_url()
        assert result == "https://my.server.com"

    def test_get_base_url_default_uses_host_port(self, monkeypatch):
        monkeypatch.delenv("MCP_BASE_URL", raising=False)
        monkeypatch.setenv("MCP_HOST", "0.0.0.0")
        monkeypatch.setenv("MCP_PORT", "8000")
        result = mcp_module._get_base_url()
        assert result == "http://localhost:8000"

    def test_get_base_url_custom_host(self, monkeypatch):
        monkeypatch.delenv("MCP_BASE_URL", raising=False)
        monkeypatch.setenv("MCP_HOST", "192.168.1.10")
        monkeypatch.setenv("MCP_PORT", "9000")
        result = mcp_module._get_base_url()
        assert result == "http://192.168.1.10:9000"

    def test_get_token_request_url_from_env(self, monkeypatch):
        monkeypatch.setenv("MCP_TOKEN_REQUEST_URL", "https://forms.gle/abc123")
        result = mcp_module._get_token_request_url()
        assert result == "https://forms.gle/abc123"

    def test_get_token_request_url_empty_by_default(self, monkeypatch):
        monkeypatch.delenv("MCP_TOKEN_REQUEST_URL", raising=False)
        result = mcp_module._get_token_request_url()
        assert result == ""
```

- [ ] **Step 3 : Lancer le test — vérifier qu'il échoue**

```bash
cd /chemin/vers/projet
pytest tests/test_tools.py::TestEnvHelpers -v
```

Expected : `AttributeError: module 'greenit_mcp_final' has no attribute '_get_base_url'`

- [ ] **Step 4 : Implémenter les helpers dans `greenit_mcp_final.py`**

Ajouter après la fonction `_tokens_for_auth` (ligne ~87), avant `_create_mcp` :

```python
def _get_base_url() -> str:
    """Retourne l'URL publique de base du serveur (sans slash final)."""
    base = os.environ.get("MCP_BASE_URL", "").rstrip("/")
    if base:
        return base
    host = os.environ.get("MCP_HOST", "0.0.0.0")
    port = os.environ.get("MCP_PORT", "8000")
    display_host = "localhost" if host == "0.0.0.0" else host
    return f"http://{display_host}:{port}"


def _get_token_request_url() -> str:
    """Retourne l'URL du formulaire de demande de token."""
    return os.environ.get("MCP_TOKEN_REQUEST_URL", "")
```

- [ ] **Step 5 : Lancer le test — vérifier qu'il passe**

```bash
pytest tests/test_tools.py::TestEnvHelpers -v
```

Expected : 6 tests PASSED.

- [ ] **Step 6 : Commit**

```bash
git add files/greenit_mcp_final.py tests/test_tools.py
git commit -m "feat: add MCP_BASE_URL and MCP_TOKEN_REQUEST_URL env helpers"
```

---

## Task 2 : Handler homepage (`GET /`)

**Files:**
- Modify: `files/greenit_mcp_final.py`
- Modify: `tests/test_tools.py`

- [ ] **Step 1 : Écrire le test**

Dans `tests/test_tools.py`, ajouter en fin de fichier :

```python
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
        assert "GreenIT MCP" in r.text

    def test_homepage_contains_version(self, client):
        r = client.get("/")
        assert mcp_module.VERSION in r.text

    def test_homepage_contains_links(self, client):
        r = client.get("/")
        assert "/install.sh" in r.text
        assert "/guide" in r.text
```

- [ ] **Step 2 : Lancer le test — vérifier qu'il échoue**

```bash
pytest tests/test_tools.py::TestHttpRoutes::test_homepage_status_200 -v
```

Expected : `AttributeError: module 'greenit_mcp_final' has no attribute '_http_homepage'`

- [ ] **Step 3 : Implémenter le handler homepage**

Dans `files/greenit_mcp_final.py`, ajouter après `_get_token_request_url`, avant `_create_mcp` :

```python
async def _http_homepage(request) -> "Response":
    from starlette.responses import HTMLResponse
    cache = charger_cache()
    fiches_count = len(cache)
    base_url = _get_base_url()

    if fiches_count:
        status_html = (
            f'<span class="badge ok">{fiches_count} fiches chargées</span>'
        )
    else:
        status_html = '<span class="badge warn">Cache vide</span>'

    html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>GreenIT MCP</title>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: #0f1117; color: #e2e8f0;
      min-height: 100vh; display: flex; align-items: center; justify-content: center;
    }}
    .card {{
      background: #1a1d27; border: 1px solid #2d3147;
      border-radius: 12px; padding: 48px; max-width: 560px; width: 100%;
      text-align: center;
    }}
    .logo {{ font-size: 48px; margin-bottom: 16px; }}
    h1 {{ font-size: 28px; font-weight: 700; color: #fff; margin-bottom: 8px; }}
    .version {{ font-size: 14px; color: #64748b; margin-bottom: 24px; }}
    .badge {{ display: inline-block; padding: 6px 14px; border-radius: 20px; font-size: 14px; font-weight: 500; }}
    .badge.ok {{ background: #14532d; color: #4ade80; }}
    .badge.warn {{ background: #713f12; color: #fbbf24; }}
    .actions {{ margin-top: 36px; display: flex; gap: 12px; justify-content: center; flex-wrap: wrap; }}
    a.btn {{
      display: inline-block; padding: 12px 24px; border-radius: 8px;
      text-decoration: none; font-size: 15px; font-weight: 500; transition: opacity .15s;
    }}
    a.btn:hover {{ opacity: .8; }}
    a.btn.primary {{ background: #22c55e; color: #000; }}
    a.btn.secondary {{ background: #1e293b; color: #94a3b8; border: 1px solid #334155; }}
    .footer {{ margin-top: 32px; font-size: 12px; color: #334155; }}
  </style>
</head>
<body>
  <div class="card">
    <div class="logo">🌱</div>
    <h1>GreenIT MCP</h1>
    <div class="version">v{VERSION}</div>
    {status_html}
    <div class="actions">
      <a class="btn primary" href="/guide">Documentation</a>
      <a class="btn secondary" href="/install.sh">install.sh</a>
    </div>
    <div class="footer">{base_url}/mcp</div>
  </div>
</body>
</html>"""
    return HTMLResponse(html)
```

- [ ] **Step 4 : Lancer les tests homepage**

```bash
pytest tests/test_tools.py::TestHttpRoutes::test_homepage_status_200 \
       tests/test_tools.py::TestHttpRoutes::test_homepage_content_type_html \
       tests/test_tools.py::TestHttpRoutes::test_homepage_contains_name \
       tests/test_tools.py::TestHttpRoutes::test_homepage_contains_version \
       tests/test_tools.py::TestHttpRoutes::test_homepage_contains_links -v
```

Expected : 5 tests PASSED.

- [ ] **Step 5 : Commit**

```bash
git add files/greenit_mcp_final.py tests/test_tools.py
git commit -m "feat: add HTTP homepage handler (GET /)"
```

---

## Task 3 : Handler script d'installation (`GET /install.sh`)

**Files:**
- Modify: `files/greenit_mcp_final.py`
- Modify: `tests/test_tools.py`

- [ ] **Step 1 : Écrire les tests**

Dans `tests/test_tools.py`, ajouter dans `TestHttpRoutes` :

```python
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

    def test_install_script_has_greenit_mcp_add(self, client):
        r = client.get("/install.sh")
        assert "claude mcp add greenit" in r.text
        assert "-t http" in r.text
```

- [ ] **Step 2 : Lancer — vérifier que ça échoue**

```bash
pytest tests/test_tools.py::TestHttpRoutes::test_install_script_status_200 -v
```

Expected : `AttributeError: module 'greenit_mcp_final' has no attribute '_http_install_script'`

- [ ] **Step 3 : Ajouter le template du script bash**

Dans `files/greenit_mcp_final.py`, ajouter immédiatement après `_get_token_request_url` (avant `_http_homepage`) :

```python
# Template du script d'installation bash.
# Placeholders remplacés à la volée :
#   __BASE_URL__          → MCP_BASE_URL (sans /mcp)
#   __MCP_URL__           → MCP_BASE_URL/mcp
#   __TOKEN_REQUEST_URL__ → MCP_TOKEN_REQUEST_URL
_INSTALL_SCRIPT_TEMPLATE = r"""#!/usr/bin/env bash
# GreenIT MCP — Script d'installation pour Claude Code
# Usage: curl -sSL __BASE_URL__/install.sh | bash -s -- <TOKEN> [--local] [--authorize] [--uninstall]
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
        --uninstall) UNINSTALL=true ;;
        --authorize) FORCE_AUTHORIZE=true ;;
        *)           [ -z "$TOKEN" ] && TOKEN="$arg" ;;
    esac
done

echo ""
echo -e "${BLUE}  ╔════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}  ║   GreenIT MCP — Installation pour Claude   ║${NC}"
echo -e "${BLUE}  ╚════════════════════════════════════════════╝${NC}"
echo ""

# --- Détection du serveur GreenIT installé ---
detect_greenit() {
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
if 'greenit' in data.get('mcpServers', {}):
    print('greenit:user')
cwd = os.getcwd()
resolved = os.path.realpath(cwd)
for path, cfg in data.get('projects', {}).items():
    if path in (cwd, resolved) or os.path.realpath(path) in (cwd, resolved):
        if 'greenit' in cfg.get('mcpServers', {}):
            print('greenit:local')
        break
"
}

# --- Mode désinstallation ---
if [ "$UNINSTALL" = true ]; then
    echo -e "  ${BOLD}Détection du serveur MCP GreenIT...${NC}"
    echo ""
    INSTALLED=$(detect_greenit)
    if [ -z "$INSTALLED" ]; then
        echo -e "  ${DIM}Aucun serveur GreenIT trouvé.${NC}"
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
allow[:] = [p for p in allow if not p.startswith('mcp__greenit__')]
if allow != original:
    if not allow and not any(v for k, v in data.get('permissions', {}).items() if k != 'allow'):
        del data['permissions']
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

# --- Vérifier le token ---
if [ -z "$TOKEN" ]; then
    echo -e "  ${RED}Erreur : token MCP manquant.${NC}"
    echo ""
    echo "  Usage :"
    echo "    curl -sSL ${BASE_URL}/install.sh | bash -s -- <TOKEN>"
    echo "    curl -sSL ${BASE_URL}/install.sh | bash -s -- <TOKEN> --local"
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

# ===========================================================
#  Étape 1/3 — Vérification des prérequis
# ===========================================================
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
else
    echo -e "  ${GREEN}✓${NC} Scope : local ${DIM}(projet courant uniquement)${NC}"
fi

# ===========================================================
#  Étape 2/3 — Installation du serveur MCP
# ===========================================================
echo ""
echo -e "  ${BOLD}Étape 2/3 — Installation du serveur MCP${NC}"
echo ""

echo -ne "  ${DIM}→${NC} GreenIT MCP... "
claude mcp remove greenit -s "${SCOPE}" > /dev/null 2>&1 || true
if MCP_ERR=$(claude mcp add greenit "${MCP_URL}" \
    -t http \
    -s "${SCOPE}" \
    -H "Authorization: Bearer ${TOKEN}" 2>&1); then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗${NC}"
    [ -n "$MCP_ERR" ] && echo -e "    ${DIM}${MCP_ERR}${NC}"
    exit 1
fi

# ===========================================================
#  Étape 3/3 — Autorisations
# ===========================================================
echo ""
echo -e "  ${BOLD}Étape 3/3 — Autorisations des outils MCP${NC}"
echo ""

AUTHORIZE=false
if [ "$FORCE_AUTHORIZE" = true ]; then
    AUTHORIZE=true
else
    echo -e "  Pré-autoriser les outils GreenIT MCP"
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
if 'mcp__greenit__*' not in allow:
    allow.append('mcp__greenit__*')
with open(path, 'w') as f:
    json.dump(data, f, indent=2)
    f.write('\n')
"
        echo -e "  ${GREEN}✓${NC} Autorisations enregistrées ${DIM}(.claude/settings.json)${NC}"
    else
        echo -e "  ${YELLOW}⚠${NC} python3 non trouvé — configurez manuellement :"
        echo '    .claude/settings.json → "permissions": { "allow": ["mcp__greenit__*"] }'
    fi
else
    echo -e "  ${DIM}Pré-autorisation ignorée${NC}"
fi

# ===========================================================
#  Résumé
# ===========================================================
echo ""
echo -e "  ${BLUE}╔══════════════════════════════════════════╗${NC}"
echo -e "  ${BLUE}║      ${GREEN}Installation terminée !${BLUE}          ║${NC}"
echo -e "  ${BLUE}╚══════════════════════════════════════════╝${NC}"
echo ""
echo -e "  ${BOLD}Serveur installé${NC} ${DIM}(scope: ${SCOPE})${NC}"
echo -e "    ${GREEN}●${NC} greenit"
echo ""
echo -e "  ${BOLD}Pour commencer :${NC}"
echo ""
echo -e "    ${DIM}\$${NC} claude"
echo -e "    ${DIM}>${NC} Quelles fiches GreenIT sont prioritaires pour mon site ?"
echo ""
echo -e "  ${BOLD}Autres exemples :${NC}"
echo ""
echo -e "    ${DIM}>${NC} Audite https://example.com et donne-moi les recommandations GreenIT"
echo -e "    ${DIM}>${NC} Quelles bonnes pratiques pour réduire les requêtes réseau ?"
echo -e "    ${DIM}>${NC} Compare les fiches RWEB_0049 et RWEB_0051"
echo ""
echo -e "  ${DIM}Désinstaller : curl -sSL ${BASE_URL}/install.sh | bash -s -- --uninstall${NC}"
echo -e "  ${DIM}Documentation : ${BASE_URL}/guide${NC}"
echo ""

} # end main()

main "$@"
"""
```

- [ ] **Step 4 : Implémenter le handler `_http_install_script`**

Dans `files/greenit_mcp_final.py`, ajouter après `_http_homepage` :

```python
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
```

- [ ] **Step 5 : Lancer les tests**

```bash
pytest tests/test_tools.py::TestHttpRoutes::test_install_script_status_200 \
       tests/test_tools.py::TestHttpRoutes::test_install_script_content_type \
       tests/test_tools.py::TestHttpRoutes::test_install_script_is_bash \
       tests/test_tools.py::TestHttpRoutes::test_install_script_no_raw_placeholder \
       tests/test_tools.py::TestHttpRoutes::test_install_script_has_uninstall_flag \
       tests/test_tools.py::TestHttpRoutes::test_install_script_has_greenit_mcp_add -v
```

Expected : 6 tests PASSED.

Note : `test_install_script_contains_mcp_url` utilise `monkeypatch` sur `os.environ` — le handler lit `_get_base_url()` à chaque appel, donc le monkeypatch doit précéder la requête. Si ce test échoue, vérifier que `_get_base_url()` lit bien `os.environ` au moment de l'appel (pas à l'import).

- [ ] **Step 6 : Commit**

```bash
git add files/greenit_mcp_final.py tests/test_tools.py
git commit -m "feat: add install.sh handler with bash script template"
```

---

## Task 4 : Handler guide (`GET /guide`)

**Files:**
- Modify: `files/greenit_mcp_final.py`
- Modify: `tests/test_tools.py`

- [ ] **Step 1 : Écrire les tests**

Dans `tests/test_tools.py`, ajouter dans `TestHttpRoutes` :

```python
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
        for tool in ("lister_fiches", "chercher_fiche", "auditer_url", "audit_rapide"):
            assert tool in r.text, f"Tool '{tool}' missing from guide"

    def test_guide_contains_token_section(self, client):
        r = client.get("/guide")
        assert "token" in r.text.lower()

    def test_guide_token_request_url_shown(self, client, monkeypatch):
        monkeypatch.setenv("MCP_TOKEN_REQUEST_URL", "https://forms.gle/test")
        r = client.get("/guide")
        assert "https://forms.gle/test" in r.text
```

- [ ] **Step 2 : Lancer — vérifier que ça échoue**

```bash
pytest tests/test_tools.py::TestHttpRoutes::test_guide_status_200 -v
```

Expected : `AttributeError: module 'greenit_mcp_final' has no attribute '_http_guide'`

- [ ] **Step 3 : Implémenter le handler `_http_guide`**

Dans `files/greenit_mcp_final.py`, ajouter après `_http_install_script` :

```python
async def _http_guide(request) -> "Response":
    from starlette.responses import HTMLResponse
    base_url = _get_base_url()
    token_request_url = _get_token_request_url()

    if token_request_url:
        token_section = f"""
        <p>Remplissez le formulaire de demande d'accès :</p>
        <a class="btn primary" href="{token_request_url}" target="_blank" rel="noopener">
          Demander un accès →
        </a>"""
    else:
        token_section = "<p>Contactez l'administrateur pour obtenir votre token.</p>"

    tools = [
        ("lister_fiches", "Liste les fiches avec filtres (lifecycle, ressource, impact, priorité)"),
        ("fiches_prioritaires", "Retourne les fiches à fort impact et haute priorité"),
        ("chercher_fiche", "Recherche des fiches par mot-clé avec scoring de pertinence"),
        ("comparer_fiches", "Compare plusieurs fiches côte à côte avec recommandation"),
        ("audit_rapide", "Génère une liste de fiches adaptées à un contexte projet"),
        ("obtenir_fiche_complete", "Récupère le contenu complet d'une fiche"),
        ("obtenir_statistiques", "Statistiques du référentiel (distributions, top fiches)"),
        ("auditer_url", "Audite un site web et génère un rapport EcoIndex + recommandations GreenIT"),
    ]
    tools_rows = "\n".join(
        f"<tr><td><code>{name}</code></td><td>{desc}</td></tr>"
        for name, desc in tools
    )

    html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>GreenIT MCP — Guide d'installation</title>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: #0f1117; color: #cbd5e1; line-height: 1.7;
    }}
    .wrap {{ max-width: 760px; margin: 0 auto; padding: 48px 24px 80px; }}
    h1 {{ font-size: 28px; color: #fff; margin-bottom: 4px; }}
    .subtitle {{ color: #64748b; font-size: 14px; margin-bottom: 48px; }}
    h2 {{ font-size: 18px; color: #fff; margin: 40px 0 16px; border-left: 3px solid #22c55e; padding-left: 12px; }}
    p {{ margin-bottom: 12px; }}
    pre {{
      background: #1e293b; border: 1px solid #334155; border-radius: 8px;
      padding: 16px; overflow-x: auto; font-size: 14px; margin: 16px 0;
    }}
    code {{ font-family: "SF Mono", "Fira Code", monospace; font-size: 13px; background: #1e293b; padding: 2px 6px; border-radius: 4px; }}
    pre code {{ background: none; padding: 0; }}
    table {{ width: 100%; border-collapse: collapse; margin: 16px 0; }}
    th {{ text-align: left; padding: 10px 12px; background: #1e293b; color: #94a3b8; font-size: 13px; }}
    td {{ padding: 10px 12px; border-bottom: 1px solid #1e293b; font-size: 14px; vertical-align: top; }}
    td:first-child {{ white-space: nowrap; width: 220px; }}
    a.btn {{
      display: inline-block; margin-top: 12px; padding: 12px 24px; border-radius: 8px;
      text-decoration: none; font-size: 15px; font-weight: 500;
    }}
    a.btn.primary {{ background: #22c55e; color: #000; }}
    .step {{ counter-increment: steps; }}
    .note {{ background: #1e293b; border-left: 3px solid #3b82f6; padding: 12px 16px; border-radius: 0 8px 8px 0; font-size: 14px; margin: 16px 0; }}
    .back {{ display: inline-block; margin-bottom: 32px; color: #64748b; text-decoration: none; font-size: 14px; }}
    .back:hover {{ color: #94a3b8; }}
  </style>
</head>
<body>
  <div class="wrap">
    <a class="back" href="/">← GreenIT MCP</a>
    <h1>🌱 Guide d'installation</h1>
    <p class="subtitle">Connectez Claude aux bonnes pratiques d'éco-conception web GreenIT</p>

    <h2>1. Prérequis</h2>
    <p>Claude Code CLI doit être installé sur votre machine :</p>
    <pre><code>npm install -g @anthropic-ai/claude-code</code></pre>

    <h2>2. Obtenir un accès</h2>
    {token_section}

    <h2>3. Installation</h2>
    <p>Une fois votre token obtenu, exécutez :</p>
    <pre><code>curl -sSL {base_url}/install.sh | bash -s -- VOTRE_TOKEN</code></pre>
    <p>Options disponibles :</p>
    <pre><code># Installer pour le projet courant uniquement
curl -sSL {base_url}/install.sh | bash -s -- VOTRE_TOKEN --local

# Pré-autoriser tous les outils (sans confirmation interactive)
curl -sSL {base_url}/install.sh | bash -s -- VOTRE_TOKEN --authorize

# Désinstaller
curl -sSL {base_url}/install.sh | bash -s -- --uninstall</code></pre>

    <h2>4. Installation manuelle</h2>
    <p>Pour Cursor, VS Code ou tout autre client MCP :</p>
    <pre><code>{{
  "mcpServers": {{
    "greenit": {{
      "type": "http",
      "url": "{base_url}/mcp",
      "headers": {{
        "Authorization": "Bearer VOTRE_TOKEN"
      }}
    }}
  }}
}}</code></pre>

    <h2>5. Outils disponibles</h2>
    <table>
      <thead><tr><th>Outil</th><th>Description</th></tr></thead>
      <tbody>{tools_rows}</tbody>
    </table>

    <h2>6. Exemples de prompts</h2>
    <div class="note">Quelles fiches GreenIT sont prioritaires pour un site React ?</div>
    <div class="note">Audite https://example.com et donne-moi les recommandations GreenIT</div>
    <div class="note">Quelles bonnes pratiques pour réduire les requêtes réseau ?</div>
    <div class="note">Compare les fiches RWEB_0049 et RWEB_0051</div>
    <div class="note">Donne-moi les statistiques du référentiel GreenIT</div>
  </div>
</body>
</html>"""
    return HTMLResponse(html)
```

- [ ] **Step 4 : Lancer les tests guide**

```bash
pytest tests/test_tools.py::TestHttpRoutes::test_guide_status_200 \
       tests/test_tools.py::TestHttpRoutes::test_guide_content_type_html \
       tests/test_tools.py::TestHttpRoutes::test_guide_contains_install_command \
       tests/test_tools.py::TestHttpRoutes::test_guide_contains_tools_list \
       tests/test_tools.py::TestHttpRoutes::test_guide_contains_token_section -v
```

Expected : 5 tests PASSED.

- [ ] **Step 5 : Commit**

```bash
git add files/greenit_mcp_final.py tests/test_tools.py
git commit -m "feat: add /guide HTML documentation handler"
```

---

## Task 5 : Brancher les routes dans FastMCP + docker-compose

**Files:**
- Modify: `files/greenit_mcp_final.py` (fonction `_create_mcp`)
- Modify: `docker-compose.yml`

- [ ] **Step 1 : Écrire le test d'intégration**

Dans `tests/test_tools.py`, ajouter dans `TestHttpRoutes` :

```python
    def test_routes_registered_in_http_mode(self, monkeypatch):
        """Vérifie que les 3 routes sont accessibles via le client standard."""
        for path in ("/", "/install.sh", "/guide"):
            r = client.get(path)  # client is already the test app from fixture
            assert r.status_code == 200, f"Route {path} returned {r.status_code}"
```

Correction : le test doit utiliser `self.client` via la fixture. Réécrire comme suit :

```python
    def test_all_routes_return_200(self, client):
        for path in ("/", "/install.sh", "/guide"):
            r = client.get(path)
            assert r.status_code == 200, f"Route {path} retourne {r.status_code}"
```

- [ ] **Step 2 : Modifier `_create_mcp()` pour brancher les routes**

Dans `files/greenit_mcp_final.py`, remplacer la fonction `_create_mcp` (actuellement lignes ~89-97) par :

```python
def _create_mcp() -> FastMCP:
    transport = os.environ.get("MCP_TRANSPORT", "stdio")
    if transport == "http":
        from starlette.routing import Route
        custom_routes = [
            Route("/", _http_homepage, methods=["GET"]),
            Route("/install.sh", _http_install_script, methods=["GET"]),
            Route("/guide", _http_guide, methods=["GET"]),
        ]
        tokens = _tokens_for_auth()
        if tokens:
            from fastmcp.server.auth import StaticTokenVerifier
            auth = StaticTokenVerifier(tokens=tokens)
            return FastMCP("GreenIT-Referentiel", auth=auth, custom_routes=custom_routes)
        return FastMCP("GreenIT-Referentiel", custom_routes=custom_routes)
    return FastMCP("GreenIT-Referentiel")
```

**Note :** Si FastMCP ne supporte pas `custom_routes` dans son constructeur (vérifiable à Task 1 step 1), utiliser à la place :

```python
# Alternative si custom_routes non supporté :
mcp_instance = FastMCP("GreenIT-Referentiel", auth=auth if tokens else None)
# Accéder à l'app Starlette sous-jacente et ajouter les routes manuellement.
# Consulter la version de FastMCP installée et sa doc pour la méthode correcte.
```

- [ ] **Step 3 : Lancer la suite de tests complète**

```bash
pytest tests/test_tools.py -v
```

Expected : tous les tests passent (y compris les anciens). Si des tests échouent à cause de l'import de `greenit_mcp_final` avec `MCP_TRANSPORT=stdio`, vérifier que `_create_mcp()` retourne bien `FastMCP("GreenIT-Referentiel")` sans custom_routes en mode stdio.

- [ ] **Step 4 : Mettre à jour `docker-compose.yml`**

Ajouter les 2 nouvelles variables dans la section `environment` du service `greenit` :

```yaml
services:
  greenit:
    build: .
    image: greenit-mcp
    ports:
      - "8000:8000"
    environment:
      MCP_TRANSPORT: http
      MCP_HOST: 0.0.0.0
      MCP_PORT: "8000"
      MCP_BASE_URL: ""           # ex: https://mcp-115-greenit.hrenaud.synology.me
      MCP_TOKEN_REQUEST_URL: ""  # ex: https://forms.gle/xxxxx
    volumes:
      - ./tokens:/app/tokens
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "python", "greenit_mcp_final.py", "--health"]
      interval: 30s
      timeout: 5s
      start_period: 10s
      retries: 3
```

- [ ] **Step 5 : Test de fumée manuel (optionnel mais recommandé)**

Démarrer le serveur en mode HTTP :

```bash
MCP_TRANSPORT=http MCP_BASE_URL=http://localhost:8000 python files/greenit_mcp_final.py
```

Dans un autre terminal :

```bash
curl -s http://localhost:8000/ | grep -c "GreenIT MCP"   # doit retourner 1
curl -s http://localhost:8000/install.sh | head -3        # doit afficher #!/usr/bin/env bash
curl -s http://localhost:8000/guide | grep -c "lister_fiches"  # doit retourner 1
```

- [ ] **Step 6 : Commit final**

```bash
git add files/greenit_mcp_final.py docker-compose.yml tests/test_tools.py
git commit -m "feat: wire HTTP routes into FastMCP and update docker-compose env vars"
```

---

## Self-Review

**Couverture du spec :**

| Spec | Tâche |
|---|---|
| `GET /` homepage avec nom + version | Task 2 |
| `GET /install.sh` script bash avec URL injectée | Task 3 |
| `GET /guide` page HTML avec 6 sections | Task 4 |
| Env var `MCP_BASE_URL` | Task 1 |
| Env var `MCP_TOKEN_REQUEST_URL` | Task 1 |
| Routes publiques (pas d'auth) | Task 5 — routes hors du middleware auth FastMCP |
| Routes actives uniquement en mode HTTP | Task 5 — `_create_mcp()` conditionnel |
| docker-compose mis à jour | Task 5 |
| Token toujours requis côté script | Task 3 — `if [ -z "$TOKEN" ]` |
| Section "Demander un accès" via formulaire | Task 4 — `_get_token_request_url()` |

**Pas de placeholder :** aucun TBD ni TODO dans le plan.

**Cohérence des types :** `_get_base_url()` et `_get_token_request_url()` définis en Task 1, utilisés en Tasks 2-4. `_http_homepage`, `_http_install_script`, `_http_guide` définis en Tasks 2-4, référencés en Task 5 dans `_create_mcp()`.
