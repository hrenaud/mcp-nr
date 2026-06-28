"""
HTTP route handlers shared across MCP servers.

Module-level variables (_VERSION, _MCP_NAME, _MCP_ID, _token_verifier,
_get_tool_definitions) are injected by each MCP after import.
"""

import json
import os
import re
import logging
from html import escape
from typing import Any

logger = logging.getLogger("mcp-ref-core")

# Injected by each MCP after import: _routes_mod._VERSION = VERSION
_VERSION = ""

# Injected by each MCP after import: _routes_mod._REFERENTIEL_VERSION = "4.2.1"
_REFERENTIEL_VERSION = ""

# Injected by each MCP after import: _routes_mod._token_verifier = verifier
_token_verifier = None

# Injected by MCPs to customize MCP name in homepage and install script
_MCP_NAME = "GreenIT MCP"

# Injected by MCPs to customize MCP ID in install script (for JSON config)
_MCP_ID = "greenit"

# Injected by MCPs to customize visual identity
_LOGO = "🌱"
_ACCENT = "#22c55e"
_ACCENT_DARK = "#14532d"
_ACCENT_LIGHT = "#4ade80"
_ACCENT_BTN_TEXT = "#000"
_TAGLINE = ""

# Injected by MCPs: key in cache dict that holds the referential items (fiches/criteres)
_ITEMS_KEY = "fiches"


def register_version_resource(mcp, charger_cache_fn) -> None:
    """Register a {mcp_id}://version resource on the given FastMCP instance.

    Must be called after _MCP_ID and _ITEMS_KEY are injected.
    """
    mcp_id = _MCP_ID
    items_key = _ITEMS_KEY

    @mcp.resource(f"{mcp_id}://version")
    async def resource_version() -> str:
        cache = charger_cache_fn()
        meta = cache.get("meta", {})
        return json.dumps({
            "server_version": _VERSION,
            "referentiel_version": meta.get("version", "inconnue"),
            "updated_at": meta.get("updated_at", "inconnue"),
            "nb_items": len(cache.get(items_key, {})),
        }, ensure_ascii=False, indent=2)


_HOST_RE = re.compile(r"^[A-Za-z0-9.\-]+(:[0-9]+)?$")


def _host_autorise(host: str) -> bool:
    """Le host (issu d'un en-tête contrôlable par le client) est-il autorisé ?

    Si MCP_ALLOWED_HOSTS est défini (liste séparée par virgules), seul un host
    dont le nom (port exclu) y figure est honoré — défense contre le host header
    injection / cache poisoning. Sinon (non configuré), pas de restriction.
    """
    allow = os.environ.get("MCP_ALLOWED_HOSTS", "").strip()
    if not allow:
        return True
    hostname = host.split(":")[0].lower()
    allowed = {h.strip().lower() for h in allow.split(",") if h.strip()}
    return hostname in allowed


def _get_base_url(request=None) -> str:
    # 1. Override explicite de l'opérateur.
    url = os.environ.get("MCP_BASE_URL", "").rstrip("/")
    if url:
        return url
    # 2. Domaine réel de la requête (derrière un reverse proxy : X-Forwarded-*).
    if request is not None:
        fwd_host = request.headers.get("x-forwarded-host")
        raw_host = fwd_host if isinstance(fwd_host, str) and fwd_host else request.headers.get("host")
        if isinstance(raw_host, str):
            host = raw_host.split(",")[0].strip()
            if host and _HOST_RE.match(host) and _host_autorise(host):
                fwd_proto = request.headers.get("x-forwarded-proto")
                scheme = fwd_proto.split(",")[0].strip().lower() if isinstance(fwd_proto, str) and fwd_proto else ""
                if scheme not in ("http", "https"):
                    req_scheme = getattr(getattr(request, "url", None), "scheme", "")
                    scheme = req_scheme.lower() if isinstance(req_scheme, str) else ""
                    if scheme not in ("http", "https"):
                        scheme = "https"
                return f"{scheme}://{host}"
    # 3. Repli local.
    host = os.environ.get("MCP_HOST", "0.0.0.0")
    port = os.environ.get("MCP_PORT", "8000")
    display_host = "localhost" if host in ("0.0.0.0", "") else host
    return f"http://{display_host}:{port}"


def _get_token_request_url() -> str:
    return os.environ.get("MCP_TOKEN_REQUEST_URL", "")


_INSTALL_SCRIPT_TEMPLATE = r"""#!/usr/bin/env bash
# __MCP_NAME__ — Script d'installation multi-clients
# Usage: curl -sSL __BASE_URL__/install.sh | bash -s -- <TOKEN> [options]
#
# Options:
#   --claude-code    Claude Code CLI uniquement
#   --cursor         Cursor uniquement
#   --vscode         VS Code uniquement
#   (sans flag)      Tous les clients détectés automatiquement
#   --local          (Claude Code) projet courant, non partagé
#   --project        (Claude Code) projet courant, partageable via .mcp.json
#   --authorize      (Claude Code) pré-autoriser les outils sans confirmation
#   --uninstall      Désinstaller de tous les clients détectés
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
TARGET_CLIENTS=()

for arg in "$@"; do
    case "$arg" in
        --local)          SCOPE="local" ;;
        --project)        SCOPE="project" ;;
        --uninstall)      UNINSTALL=true ;;
        --authorize)      FORCE_AUTHORIZE=true ;;
        --claude-code)    TARGET_CLIENTS+=("claude-code") ;;
        --claude-desktop) TARGET_CLIENTS+=("claude-desktop") ;;
        --cursor)         TARGET_CLIENTS+=("cursor") ;;
        --vscode)         TARGET_CLIENTS+=("vscode") ;;
        *)                [ -z "$TOKEN" ] && TOKEN="$arg" ;;
    esac
done

echo ""
echo -e "${BLUE}  ╔══════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}  ║   __MCP_NAME__ — Installation multi-clients   ║${NC}"
echo -e "${BLUE}  ╚══════════════════════════════════════════════╝${NC}"
echo ""

# ── Detection ────────────────────────────────────────────────────────────────

has_claude_code()    { command -v claude &>/dev/null; }
has_cursor()         { command -v cursor &>/dev/null || [ -d "$HOME/.cursor" ]; }
has_vscode()         { command -v code &>/dev/null; }
has_claude_desktop() {
    local cfg
    case "$(uname -s)" in
        Darwin) cfg="$HOME/Library/Application Support/Claude/claude_desktop_config.json" ;;
        Linux)  cfg="$HOME/.config/Claude/claude_desktop_config.json" ;;
        *)      return 1 ;;
    esac
    [ -f "$cfg" ] || [ -d "$(dirname "$cfg")" ]
}

DETECTED=()
if [ ${#TARGET_CLIENTS[@]} -eq 0 ]; then
    has_claude_code && DETECTED+=("claude-code")
    has_cursor      && DETECTED+=("cursor")
    has_vscode      && DETECTED+=("vscode")
else
    for c in "${TARGET_CLIENTS[@]}"; do
        if [ "$c" = "claude-desktop" ]; then
            echo -e "  ${YELLOW}⚠${NC}  Claude Desktop n'est pas compatible avec les MCP HTTP distants."
            echo -e "      Utilisez Claude Code CLI ou Cursor à la place."
            echo ""
        else
            DETECTED+=("$c")
        fi
    done
fi

if [ ${#DETECTED[@]} -eq 0 ]; then
    echo -e "  ${RED}Aucun client IA compatible détecté.${NC}"
    echo ""
    echo "  Clients supportés (MCP HTTP) :"
    echo "    • Claude Code CLI  — npm install -g @anthropic-ai/claude-code"
    echo "    • Cursor           — https://cursor.com"
    echo "    • VS Code          — https://code.visualstudio.com"
    echo ""
    echo -e "  ${DIM}Note : Claude Desktop ne supporte pas les MCP HTTP distants.${NC}"
    echo ""
    exit 1
fi

# ── Helpers UI (sélection numérotée) ─────────────────────────────────────────

# numbered_checkbox <title> <label1> <label2> ...
# Résultat : CHECKBOX_RESULT (array d'indices 0-based cochés).
numbered_checkbox() {
    local title="$1"; shift
    local labels=("$@")
    local n=${#labels[@]}
    local i answer choice
    CHECKBOX_RESULT=()

    echo -e "  ${BOLD}${title}${NC}"
    echo ""
    for ((i=0; i<n; i++)); do
        echo -e "    $((i+1))) ${labels[$i]}"
    done
    echo ""

    if [ ! -e /dev/tty ]; then
        for ((i=0; i<n; i++)); do CHECKBOX_RESULT+=("$i"); done
        echo -e "  ${DIM}Mode non-interactif — tous les clients sélectionnés${NC}"
        echo ""
        return
    fi

    echo -ne "  ${YELLOW}Numéros à installer, séparés par espace [tous] : ${NC}"
    if read -r answer < /dev/tty 2>/dev/null; then
        if [ -z "$answer" ]; then
            for ((i=0; i<n; i++)); do CHECKBOX_RESULT+=("$i"); done
        else
            for choice in $answer; do
                if [[ "$choice" =~ ^[0-9]+$ ]] && [ "$choice" -ge 1 ] && [ "$choice" -le "$n" ]; then
                    CHECKBOX_RESULT+=("$((choice - 1))")
                fi
            done
        fi
    else
        for ((i=0; i<n; i++)); do CHECKBOX_RESULT+=("$i"); done
        echo -e "  ${DIM}Mode non-interactif — tous les clients sélectionnés${NC}"
    fi
    echo ""
}

# numbered_radio <title> <default_index> <label1> <label2> ...
# Résultat : RADIO_RESULT (indice 0-based).
numbered_radio() {
    local title="$1"; shift
    local default_idx="$1"; shift
    local labels=("$@")
    local n=${#labels[@]}
    local i answer
    RADIO_RESULT="$default_idx"

    echo -e "  ${BOLD}${title}${NC}"
    echo ""
    for ((i=0; i<n; i++)); do
        echo -e "    $((i+1))) ${labels[$i]}"
    done
    echo ""

    if [ ! -e /dev/tty ]; then
        echo -e "  ${DIM}Mode non-interactif — option par défaut sélectionnée${NC}"
        echo ""
        return
    fi

    echo -ne "  ${YELLOW}Votre choix [$((default_idx+1))] : ${NC}"
    if read -r answer < /dev/tty 2>/dev/null; then
        if [[ "$answer" =~ ^[0-9]+$ ]] && [ "$answer" -ge 1 ] && [ "$answer" -le "$n" ]; then
            RADIO_RESULT="$((answer - 1))"
        fi
    fi
    echo ""
}

# ── Sélection des clients ─────────────────────────────────────────────────────

if [ ${#TARGET_CLIENTS[@]} -gt 0 ]; then
    echo -e "  ${BOLD}Clients ciblés :${NC}"
    for client in "${DETECTED[@]}"; do
        case "$client" in
            claude-code) echo -e "    ${GREEN}[✓]${NC} Claude Code CLI" ;;
            cursor)      echo -e "    ${GREEN}[✓]${NC} Cursor" ;;
            vscode)      echo -e "    ${GREEN}[✓]${NC} VS Code" ;;
        esac
    done
    echo ""
else
    CLIENT_LABELS=()
    for client in "${DETECTED[@]}"; do
        case "$client" in
            claude-code) CLIENT_LABELS+=("Claude Code CLI") ;;
            cursor)      CLIENT_LABELS+=("Cursor") ;;
            vscode)      CLIENT_LABELS+=("VS Code") ;;
        esac
    done

    numbered_checkbox "Sur quels clients installer ?" "${CLIENT_LABELS[@]}"

    if [ ${#CHECKBOX_RESULT[@]} -eq 0 ]; then
        echo -e "  ${YELLOW}Aucun client sélectionné. Annulé.${NC}"
        echo ""
        exit 0
    fi

    SELECTED=()
    for idx in "${CHECKBOX_RESULT[@]}"; do SELECTED+=("${DETECTED[$idx]}"); done
    DETECTED=("${SELECTED[@]}")
fi

# ── Sélection de la portée (Claude Code uniquement) ───────────────────────────

NEEDS_SCOPE=false
for c in "${DETECTED[@]}"; do [ "$c" = "claude-code" ] && NEEDS_SCOPE=true || true; done

if [ "$NEEDS_SCOPE" = true ] && [ ${#TARGET_CLIENTS[@]} -eq 0 ] && [ "$SCOPE" = "user" ]; then
    numbered_radio "Portée d'installation pour Claude Code :" 0 \
        "global  — ~/.claude/settings.json  (tous vos projets)" \
        "local   — .claude/settings.json    (projet courant, non partagé)" \
        "projet  — .mcp.json                (projet courant, partageable)"
    case "$RADIO_RESULT" in
        0) SCOPE="user" ;;
        1) SCOPE="local" ;;
        2) SCOPE="project" ;;
    esac
fi

# ── JSON helpers ─────────────────────────────────────────────────────────────

# write_json_mcp <path> <root_key> <token> <mcp_url> <mcp_id>
write_json_mcp() {
    local path="$1" key="$2" token="$3" mcp_url="$4" mcp_id="$5"
    mkdir -p "$(dirname "$path")"
    python3 -c "
import json, sys
path, key, token, mcp_url, mcp_id = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5]
try:
    with open(path) as f:
        data = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    data = {}
data.setdefault(key, {})[mcp_id] = {
    'url': mcp_url,
    'headers': {'Authorization': 'Bearer ' + token}
}
with open(path, 'w') as f:
    json.dump(data, f, indent=2)
    f.write('\n')
" "$path" "$key" "$token" "$mcp_url" "$mcp_id"
}

# remove_json_mcp <path> <root_key> <mcp_id>
remove_json_mcp() {
    local path="$1" key="$2" mcp_id="$3"
    [ -f "$path" ] || return 0
    python3 -c "
import json, sys
path, key, mcp_id = sys.argv[1], sys.argv[2], sys.argv[3]
try:
    with open(path) as f:
        data = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    exit(0)
if key in data and mcp_id in data[key]:
    del data[key][mcp_id]
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)
        f.write('\n')
" "$path" "$key" "$mcp_id"
}

# ── Uninstall ────────────────────────────────────────────────────────────────

if [ "$UNINSTALL" = true ]; then
    echo -e "  ${BOLD}Désinstallation...${NC}"
    echo ""
    for client in "${DETECTED[@]}"; do
        case "$client" in
            claude-code)
                for s in user local project; do
                    claude mcp remove __MCP_ID__ -s "$s" > /dev/null 2>&1 && \
                        echo -e "  ${GREEN}✓${NC} Claude Code CLI ${DIM}(${s})${NC}" || true
                done
                if [ -f ".claude/settings.json" ]; then
                    python3 -c "
import json
path = '.claude/settings.json'
try:
    with open(path) as f:
        data = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    exit(0)
allow = data.get('permissions', {}).get('allow', [])
filtered = [p for p in allow if not p.startswith('mcp____MCP_ID____')]
if filtered != allow:
    data['permissions']['allow'] = filtered
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)
        f.write('\n')
" 2>/dev/null && echo -e "  ${GREEN}✓${NC} Autorisations nettoyées ${DIM}(.claude/settings.json)${NC}"
                fi
                ;;
            cursor)
                remove_json_mcp "$HOME/.cursor/mcp.json" "mcpServers" "__MCP_ID__"
                echo -e "  ${GREEN}✓${NC} Cursor ${DIM}(~/.cursor/mcp.json)${NC}"
                ;;
            vscode)
                remove_json_mcp ".vscode/mcp.json" "servers" "__MCP_ID__"
                echo -e "  ${GREEN}✓${NC} VS Code ${DIM}(.vscode/mcp.json)${NC}"
                ;;
        esac
    done
    echo ""
    echo -e "  ${GREEN}Désinstallation terminée.${NC}"
    echo ""
    exit 0
fi

# ── Check token ──────────────────────────────────────────────────────────────

if [ -z "$TOKEN" ]; then
    echo -e "  ${RED}Erreur : token MCP manquant.${NC}"
    echo ""
    echo "  Usage :"
    echo "    curl -sSL ${BASE_URL}/install.sh | bash -s -- <TOKEN>"
    echo "    curl -sSL ${BASE_URL}/install.sh | bash -s -- <TOKEN> --cursor"
    echo "    curl -sSL ${BASE_URL}/install.sh | bash -s -- <TOKEN> --claude-code --authorize"
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

# ── Install per client ───────────────────────────────────────────────────────

echo -e "  ${BOLD}Installation...${NC}"
echo ""

INSTALLED_COUNT=0

for client in "${DETECTED[@]}"; do
    case "$client" in
        claude-code)
            echo -ne "  ${DIM}→${NC} Claude Code CLI... "
            claude mcp remove __MCP_ID__ -s "${SCOPE}" > /dev/null 2>&1 || true
            if MCP_ERR=$(claude mcp add __MCP_ID__ "${MCP_URL}" \
                -t http -s "${SCOPE}" \
                -H "Authorization: Bearer ${TOKEN}" 2>&1); then
                echo -e "${GREEN}✓${NC} ${DIM}(scope: ${SCOPE})${NC}"
                INSTALLED_COUNT=$((INSTALLED_COUNT + 1))
            else
                echo -e "${RED}✗${NC}"
                [ -n "$MCP_ERR" ] && echo -e "    ${DIM}${MCP_ERR}${NC}"
            fi
            ;;
        cursor)
            echo -ne "  ${DIM}→${NC} Cursor... "
            if write_json_mcp "$HOME/.cursor/mcp.json" "mcpServers" "$TOKEN" "$MCP_URL" "__MCP_ID__"; then
                echo -e "${GREEN}✓${NC} ${DIM}(~/.cursor/mcp.json)${NC}"
                INSTALLED_COUNT=$((INSTALLED_COUNT + 1))
            else
                echo -e "${RED}✗${NC}"
            fi
            ;;
        vscode)
            echo -ne "  ${DIM}→${NC} VS Code... "
            if write_json_mcp ".vscode/mcp.json" "servers" "$TOKEN" "$MCP_URL" "__MCP_ID__"; then
                echo -e "${GREEN}✓${NC} ${DIM}(.vscode/mcp.json)${NC}"
                INSTALLED_COUNT=$((INSTALLED_COUNT + 1))
            else
                echo -e "${RED}✗${NC}"
            fi
            ;;
    esac
done

# ── Claude Code: authorize tools ─────────────────────────────────────────────

for client in "${DETECTED[@]}"; do
    if [ "$client" = "claude-code" ]; then
        echo ""
        echo -e "  ${BOLD}Autorisations Claude Code${NC}"
        echo ""
        AUTHORIZE=false
        if [ "$FORCE_AUTHORIZE" = true ]; then
            AUTHORIZE=true
        else
            echo -e "  Pré-autoriser les outils __MCP_NAME__"
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
if 'mcp____MCP_ID____*' not in allow:
    allow.append('mcp____MCP_ID____*')
with open(path, 'w') as f:
    json.dump(data, f, indent=2)
    f.write('\n')
" && echo -e "  ${GREEN}✓${NC} Autorisations enregistrées ${DIM}(.claude/settings.json)${NC}"
        else
            echo -e "  ${DIM}Pré-autorisation ignorée${NC}"
        fi
        break
    fi
done

# ── Summary ──────────────────────────────────────────────────────────────────

echo ""
echo -e "  ${BLUE}╔════════════════════════════════════════╗${NC}"
echo -e "  ${BLUE}║    ${GREEN}Installation terminée !${BLUE}           ║${NC}"
echo -e "  ${BLUE}╚════════════════════════════════════════╝${NC}"
echo ""
echo -e "  ${BOLD}${INSTALLED_COUNT} client(s) configuré(s)${NC}"
echo ""
echo -e "  ${BOLD}Exemples de prompts :${NC}"
echo ""
echo -e "    ${DIM}›${NC} Quels outils sont prioritaires avec __MCP_NAME__ ?"
echo -e "    ${DIM}›${NC} Audite https://example.com et donne-moi les recommandations"
echo -e "    ${DIM}›${NC} Compare les critères ou recommandations"
echo ""
echo -e "  ${DIM}Désinstaller : curl -sSL ${BASE_URL}/install.sh | bash -s -- --uninstall${NC}"
echo -e "  ${DIM}Documentation : ${BASE_URL}/guide${NC}"
echo ""

} # end main()

main "$@"
"""


async def _http_homepage(request) -> "Response":
    """Renders the homepage with server status and quick install instructions."""
    from starlette.responses import HTMLResponse
    from data import charger_cache
    cache = charger_cache()
    fiches_count = len(cache.get(_ITEMS_KEY, {}))
    base_url = escape(_get_base_url(request))
    status_html = (
        f'<span class="badge ok">{fiches_count} entrées chargées</span>'
        if fiches_count else
        '<span class="badge warn">Cache vide</span>'
    )
    tagline_html = f'<p class="tagline">{escape(_TAGLINE)}</p>' if _TAGLINE else ''
    ref_version_html = f'<div class="ref-version">Référentiel {escape(_REFERENTIEL_VERSION)}</div>' if _REFERENTIEL_VERSION else ''

    html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{_MCP_NAME}</title>
  <style>
    :root {{
      --accent: {_ACCENT};
      --accent-dark: {_ACCENT_DARK};
      --accent-light: {_ACCENT_LIGHT};
      --accent-btn-text: {_ACCENT_BTN_TEXT};
    }}
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      font-size: 16px; background: #0f1117; color: #e2e8f0;
      min-height: 100vh; display: flex; align-items: center; justify-content: center;
    }}
    .card {{
      background: #1a1d27; border: 1px solid #2d3147;
      border-top: 3px solid var(--accent);
      border-radius: 12px; padding: 48px; max-width: 560px; width: 100%;
      text-align: center;
    }}
    .logo {{ font-size: 48px; margin-bottom: 16px; }}
    h1 {{ font-size: 32px; font-weight: 700; color: #fff; margin-bottom: 6px; }}
    .version {{ font-size: 13px; color: #cbd5e1; margin-bottom: 4px; }}
    .ref-version {{ font-size: 12px; color: #94a3b8; margin-bottom: 6px; }}
    .tagline {{ font-size: 14px; color: #64748b; margin-bottom: 20px; }}
    .badge {{ display: inline-block; padding: 6px 14px; border-radius: 20px; font-size: 14px; font-weight: 500; }}
    .badge.ok {{ background: var(--accent-dark); color: var(--accent-light); }}
    .badge.warn {{ background: #713f12; color: #fbbf24; }}
    .actions {{ margin-top: 36px; display: flex; gap: 12px; justify-content: center; flex-wrap: wrap; }}
    a.btn {{
      display: inline-block; padding: 12px 24px; border-radius: 8px;
      text-decoration: none; font-size: 15px; font-weight: 500; transition: opacity .15s;
    }}
    a.btn:hover {{ opacity: .8; }}
    a.btn.primary {{ background: var(--accent); color: var(--accent-btn-text); }}
    a.btn.secondary {{ background: #1e293b; color: #94a3b8; border: 1px solid #334155; }}
    .footer {{ margin-top: 32px; font-size: 12px; color: #94a3b8; }}
    .install-block {{
      margin-top: 28px; background: #0f1117; border: 1px solid #2d3147;
      border-radius: 8px; padding: 14px 16px; text-align: left;
    }}
    .install-label {{
      font-size: 11px; color: #64748b; margin-bottom: 8px;
      letter-spacing: .06em; text-transform: uppercase;
    }}
    .install-cmd {{
      font-family: "SF Mono", "Fira Code", monospace;
      font-size: 13px; color: #e2e8f0; word-break: break-all; line-height: 1.6;
    }}
  </style>
</head>
<body>
  <div class="card">
    <div class="logo">{_LOGO}</div>
    <h1>{_MCP_NAME}</h1>
    <div class="version">v{_VERSION}</div>
    {ref_version_html}
    {tagline_html}
    {status_html}
    <div class="install-block">
      <div class="install-label">Installation rapide</div>
      <div class="install-cmd">curl -sSL {base_url}/install.sh | bash -s -- TOKEN</div>
    </div>
    <div class="actions">
      <a class="btn primary" href="/guide">Documentation</a>
    </div>
    <div class="footer">{base_url}/mcp</div>
  </div>
</body>
</html>"""
    return HTMLResponse(html)


async def _check_admin_auth(request) -> "tuple[bool, Any]":
    from starlette.responses import JSONResponse
    admin_token = os.environ.get("ADMIN_TOKEN", "")
    if not admin_token:
        return False, JSONResponse({"error": "Admin API disabled"}, status_code=503)
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer ") or auth_header[7:] != admin_token:
        return False, JSONResponse({"error": "Unauthorized"}, status_code=401)
    return True, None


async def _http_admin_list_tokens(request) -> "Response":
    from starlette.responses import JSONResponse
    ok, err = await _check_admin_auth(request)
    if not ok:
        return err
    return JSONResponse(_token_verifier.list_all())


async def _http_admin_create_token(request) -> "Response":
    from starlette.responses import JSONResponse
    ok, err = await _check_admin_auth(request)
    if not ok:
        return err
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON body"}, status_code=400)
    name = body.get("name", "").strip() if isinstance(body, dict) else ""
    if not name:
        return JSONResponse({"error": "name is required"}, status_code=400)
    expires_days = body.get("expires_days", 365)
    if not isinstance(expires_days, int) or expires_days <= 0:
        return JSONResponse({"error": "expires_days must be a positive integer"}, status_code=400)
    result = _token_verifier.create(name, expires_days)
    return JSONResponse(result, status_code=201)


async def _http_admin_get_token(request) -> "Response":
    from starlette.responses import JSONResponse
    ok, err = await _check_admin_auth(request)
    if not ok:
        return err
    token_id = request.path_params["id"]
    token_info = _token_verifier.get_by_id(token_id)
    if token_info is None:
        return JSONResponse({"error": "Token not found"}, status_code=404)
    return JSONResponse(token_info)


async def _http_admin_update_token(request) -> "Response":
    from starlette.responses import JSONResponse
    ok, err = await _check_admin_auth(request)
    if not ok:
        return err
    token_id = request.path_params["id"]
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON body"}, status_code=400)
    if not isinstance(body, dict):
        return JSONResponse({"error": "Invalid JSON body"}, status_code=400)
    name = body.get("name")
    expires_days = body.get("expires_days")
    if name is not None and not isinstance(name, str):
        return JSONResponse({"error": "name must be a string"}, status_code=400)
    if expires_days is not None and (not isinstance(expires_days, int) or expires_days <= 0):
        return JSONResponse({"error": "expires_days must be a positive integer"}, status_code=400)
    if name is None and expires_days is None:
        return JSONResponse({"error": "Provide name and/or expires_days"}, status_code=400)
    result = _token_verifier.update(token_id, name=name, expires_days=expires_days)
    if result is None:
        return JSONResponse({"error": "Token not found"}, status_code=404)
    return JSONResponse(result)


async def _http_admin_delete_token(request) -> "Response":
    from starlette.responses import JSONResponse, Response
    ok, err = await _check_admin_auth(request)
    if not ok:
        return err
    token_id = request.path_params["id"]
    deleted = _token_verifier.revoke(token_id)
    if not deleted:
        return JSONResponse({"error": "Token not found"}, status_code=404)
    return Response(status_code=204)


async def _http_install_script(request) -> "Response":
    from starlette.responses import PlainTextResponse
    # Garde-fou : _MCP_ID est injecté dans un script shell ; on interdit tout
    # caractère hors [a-z0-9-] pour écarter une corruption/injection de remplacement.
    if not re.fullmatch(r"[a-z][a-z0-9-]*", _MCP_ID or ""):
        raise ValueError(f"_MCP_ID invalide '{_MCP_ID}' — doit matcher [a-z][a-z0-9-]*")
    base_url = _get_base_url(request)
    mcp_url = f"{base_url}/mcp"
    token_request_url = _get_token_request_url()
    script = (
        _INSTALL_SCRIPT_TEMPLATE
        .replace("__BASE_URL__", base_url)
        .replace("__MCP_URL__", mcp_url)
        .replace("__TOKEN_REQUEST_URL__", token_request_url)
        .replace("__MCP_NAME__", _MCP_NAME)
        .replace("__MCP_ID__", _MCP_ID)
    )
    return PlainTextResponse(script, media_type="text/plain; charset=utf-8")


def _default_tool_definitions() -> list[dict[str, Any]]:
    """Default: no tools. Each MCP injects its own via factory.create_mcp()."""
    return []


# Référence vers l'instance FastMCP, injectée par factory.create_mcp().
_mcp_instance = None


def _tool_definitions_from_mcp() -> list[dict[str, Any]]:
    """Dérive la liste d'outils du /guide depuis les outils FastMCP enregistrés.

    Source unique de vérité = les décorateurs @mcp.tool (évite la table manuelle
    dupliquée dans chaque MCP). Lecture paresseuse : les outils sont enregistrés
    après create_mcp, donc on lit l'instance au moment du rendu de /guide.
    """
    if _mcp_instance is None:
        return []
    try:
        try:
            from fastmcp.tools.function_tool import FunctionTool
        except ImportError:  # compat FastMCP plus anciens
            from fastmcp.tools.tool import FunctionTool
        components = _mcp_instance._local_provider._components
        tools = [c for c in components.values() if isinstance(c, FunctionTool)]
    except Exception:
        return []
    defs = [
        {
            "name": t.name,
            "description": getattr(t, "description", "") or "",
            "inputSchema": getattr(t, "parameters", {}) or {},
        }
        for t in tools
    ]
    return sorted(defs, key=lambda d: d["name"])


# Injected by MCPs after import: _routes_mod._get_tool_definitions = custom_tool_definitions
# Défaut : dérivation introspective depuis les outils enregistrés.
_get_tool_definitions = _tool_definitions_from_mcp


def _default_guide_extra_sections() -> str:
    """Default: no extra sections. Each MCP injects its own via factory.create_mcp()."""
    return ""


# Injected by MCPs after import: _routes_mod._guide_extra_sections = custom_guide_extra_sections
_guide_extra_sections = _default_guide_extra_sections


async def _http_guide(request) -> "Response":
    """Renders the user guide with token management and configuration instructions."""
    from starlette.responses import HTMLResponse, JSONResponse

    # Check Accept header for content negotiation
    accept_header = request.headers.get("accept", "text/html").lower()

    if "application/json" in accept_header:
        # Return JSON with tool definitions
        tools = _get_tool_definitions()
        return JSONResponse({"tools": tools})

    # Return HTML (default behavior) - get tools once for rendering
    tools = _get_tool_definitions()
    base_url = escape(_get_base_url(request))
    token_request_url = _get_token_request_url()
    if token_request_url and (token_request_url.startswith("http://") or token_request_url.startswith("https://")):
        token_request_url = escape(token_request_url)
        token_section = f"""
        <p>Remplissez le formulaire de demande d'accès :</p>
        <a class="btn primary" href="{token_request_url}" target="_blank" rel="noopener">
          Demander un accès →
        </a>"""
    else:
        token_section = "<p>Contactez l'administrateur pour obtenir votre token.</p>"

    tools_rows = "\n".join(
        f"<tr><td><code>{tool['name']}</code></td><td>{tool['description']}</td></tr>"
        for tool in tools
    )

    access_link = (
        f' <a href="{token_request_url}" target="_blank" rel="noopener">Demander un accès →</a>'
        if token_request_url and token_request_url.startswith("http") else ''
    )

    html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{_MCP_NAME} — Guide d'installation</title>
  <style>
    :root {{
      --accent: {_ACCENT};
      --accent-dark: {_ACCENT_DARK};
      --accent-light: {_ACCENT_LIGHT};
      --accent-btn-text: {_ACCENT_BTN_TEXT};
    }}
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      font-size: 16px; background: #0f1117; color: #cbd5e1; line-height: 1.7;
    }}
    .top-bar {{ height: 3px; background: var(--accent); position: fixed; top: 0; left: 0; right: 0; }}
    .wrap {{ max-width: 760px; margin: 0 auto; padding: 56px 24px 80px; }}
    h1 {{ font-size: 30px; color: #fff; margin-bottom: 4px; }}
    .subtitle {{ color: #64748b; font-size: 14px; margin-bottom: 48px; }}
    h2 {{ font-size: 18px; color: #fff; margin: 48px 0 16px; border-left: 4px solid var(--accent); padding-left: 12px; }}
    h3 {{ font-size: 15px; color: #94a3b8; margin: 24px 0 10px; font-weight: 500; }}
    p {{ margin-bottom: 12px; }}
    pre {{
      background: #1e293b; border: 1px solid #334155; border-radius: 8px;
      padding: 16px; overflow-x: auto; font-size: 14px; margin: 16px 0;
    }}
    code {{ font-family: "SF Mono", "Fira Code", monospace; font-size: 13px; background: #1e293b; padding: 2px 6px; border-radius: 4px; }}
    pre code {{ background: none; padding: 0; }}
    table {{ width: 100%; border-collapse: collapse; margin: 16px 0; }}
    th {{ text-align: left; padding: 10px 12px; background: #1e293b; color: #94a3b8; font-size: 14px; border-bottom: 1px solid #334155; }}
    td {{ padding: 10px 12px; border-bottom: 1px solid #1e293b; font-size: 15px; vertical-align: top; }}
    td:first-child {{ white-space: nowrap; width: 240px; }}
    tr:nth-child(even) td {{ background: rgba(255,255,255,.02); }}
    a {{ color: var(--accent); text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    a.btn {{
      display: inline-block; margin-top: 12px; padding: 12px 24px; border-radius: 8px;
      text-decoration: none; font-size: 15px; font-weight: 500;
    }}
    a.btn.primary {{ background: var(--accent); color: var(--accent-btn-text); }}
    .note {{ background: #1e293b; border-left: 3px solid var(--accent); padding: 12px 16px; border-radius: 0 8px 8px 0; font-size: 14px; margin: 8px 0; }}
    .back {{ display: inline-block; margin-bottom: 32px; color: #64748b; text-decoration: none; font-size: 14px; }}
    .back:hover {{ color: #94a3b8; }}
  </style>
</head>
<body>
  <div class="top-bar"></div>
  <div class="wrap">
    <a class="back" href="/">← {_MCP_NAME}</a>
    <h1>Guide d'installation — {_MCP_NAME}</h1>
    <p class="subtitle">Connectez Claude à {_MCP_NAME}</p>

    <h2>1. Demander un accès</h2>
    {token_section}

    <h2>2. Installation</h2>

    <h3>Script automatique — Claude Code (recommandé)</h3>
    <pre><code>curl -sSL {base_url}/install.sh | bash -s -- VOTRE_TOKEN</code></pre>
    <p>Options disponibles :</p>
    <pre><code># Installer pour le projet courant uniquement (dans ~/.claude.json)
curl -sSL {base_url}/install.sh | bash -s -- VOTRE_TOKEN --local

# Installer pour le projet courant, partageable via git (crée .mcp.json)
curl -sSL {base_url}/install.sh | bash -s -- VOTRE_TOKEN --project

# Pré-autoriser tous les outils (sans confirmation interactive)
curl -sSL {base_url}/install.sh | bash -s -- VOTRE_TOKEN --authorize

# Désinstaller
curl -sSL {base_url}/install.sh | bash -s -- --uninstall</code></pre>

    <h3>Commande directe — Claude Code (token manuel)</h3>
    <p>Authentification par token personnel :</p>
    <pre><code>claude mcp add {_MCP_ID} {base_url}/mcp -t http -H "Authorization: Bearer VOTRE_TOKEN"</code></pre>
    <p>Remplacez <code>VOTRE_TOKEN</code> par votre token personnel.{access_link}</p>

    <h2>3. Installation manuelle</h2>
    <p>Pour Cursor, VS Code ou tout autre client MCP :</p>
    <pre><code>{{
  "mcpServers": {{
    "{_MCP_ID}": {{
      "type": "http",
      "url": "{base_url}/mcp",
      "headers": {{
        "Authorization": "Bearer VOTRE_TOKEN"
      }}
    }}
  }}
}}</code></pre>

    <h2>4. Outils disponibles</h2>
    <table>
      <thead><tr><th>Outil</th><th>Description</th></tr></thead>
      <tbody>{tools_rows}</tbody>
    </table>

    {_guide_extra_sections()}
  </div>
</body>
</html>"""
    return HTMLResponse(html)
