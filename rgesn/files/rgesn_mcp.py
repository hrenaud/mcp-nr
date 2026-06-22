"""
Serveur MCP pour le référentiel RGESN (Référentiel Général d'Écoconception de Services Numériques)
"""

from fastmcp import FastMCP
from pathlib import Path
import logging
import os
import sys
from typing import Any

from mcp_ref_core.auth import DynamicTokenVerifier, construire_verifier, tokens_pour_auth
from mcp_ref_core import routes as _routes_mod

# Re-export helper functions from routes for backward compatibility with tests
_get_base_url = _routes_mod._get_base_url
_get_token_request_url = _routes_mod._get_token_request_url

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


# ============================================================================
# TOOL DEFINITIONS (Scaffold vide)
# ============================================================================

def _rgesn_tool_definitions() -> list[dict[str, Any]]:
    """Build tool definitions for RGESN MCP.

    Retourne une liste vide (scaffold vide).

    Returns:
        list[dict[str, Any]]: Tool definitions (empty for now)
    """
    return []


# ============================================================================
# HTTP ROUTES (public endpoints — no auth)
# ============================================================================

async def _http_homepage(request) -> "Response":
    """Délègue à routes._http_homepage"""
    return await _routes_mod._http_homepage(request)


async def _http_install_script(request) -> "Response":
    """Délègue à routes._http_install_script"""
    return await _routes_mod._http_install_script(request)


async def _http_guide(request) -> "Response":
    """Délègue à routes._http_guide"""
    return await _routes_mod._http_guide(request)


# ============================================================================
# MCP INITIALIZATION
# ============================================================================

def _create_mcp() -> FastMCP:
    """Crée et configure l'instance FastMCP avec auth et routes HTTP."""

    token_path = Path(TOKENS_FILE)
    verifier = DynamicTokenVerifier(token_path)
    _routes_mod._token_verifier = verifier
    _routes_mod._get_tool_definitions = _rgesn_tool_definitions
    _routes_mod._VERSION = VERSION
    _routes_mod._MCP_NAME = "RGESN MCP"
    _routes_mod._MCP_ID = "rgesn"

    if verifier.tokens:
        mcp_instance = FastMCP("RGESN-Referentiel", auth=verifier)
        mcp_instance._auth = verifier
    else:
        mcp_instance = FastMCP("RGESN-Referentiel")
        mcp_instance._auth = None

    transport = os.environ.get("MCP_TRANSPORT", "stdio")
    if transport == "http":
        mcp_instance.custom_route("/", methods=["GET"])(_http_homepage)
        mcp_instance.custom_route("/install.sh", methods=["GET"])(_http_install_script)
        mcp_instance.custom_route("/guide", methods=["GET"])(_http_guide)
        mcp_instance.custom_route("/admin/tokens", methods=["GET"])(_routes_mod._http_admin_list_tokens)
        mcp_instance.custom_route("/admin/tokens", methods=["POST"])(_routes_mod._http_admin_create_token)
        mcp_instance.custom_route("/admin/tokens/{id}", methods=["GET"])(_routes_mod._http_admin_get_token)
        mcp_instance.custom_route("/admin/tokens/{id}", methods=["PATCH"])(_routes_mod._http_admin_update_token)
        mcp_instance.custom_route("/admin/tokens/{id}", methods=["DELETE"])(_routes_mod._http_admin_delete_token)

    return mcp_instance


# Create MCP instance
mcp = _create_mcp()


# ============================================================================
# MAIN: CLI et démarrage du serveur
# ============================================================================

if __name__ == "__main__":
    args = sys.argv[1:]

    # --generate-token --name <nom> [--expires-days <N>]
    if "--generate-token" in args:
        from mcp_ref_core.auth import cmd_generate_token
        name = None
        expires_days = 365
        if "--name" in args:
            idx = args.index("--name")
            if idx + 1 < len(args):
                name = args[idx + 1]
        if "--expires-days" in args:
            idx = args.index("--expires-days")
            if idx + 1 < len(args):
                expires_days = int(args[idx + 1])

        cmd_generate_token(Path(TOKENS_FILE), name, expires_days)
        sys.exit(0)

    # --list-tokens
    if "--list-tokens" in args:
        from mcp_ref_core.auth import cmd_list_tokens
        cmd_list_tokens(Path(TOKENS_FILE))
        sys.exit(0)

    # --revoke-token <token>
    if "--revoke-token" in args:
        from mcp_ref_core.auth import cmd_revoke_token
        idx = args.index("--revoke-token")
        if idx + 1 >= len(args):
            print("Usage: --revoke-token <token>", file=sys.stderr)
            sys.exit(1)
        target = args[idx + 1]
        try:
            cmd_revoke_token(Path(TOKENS_FILE), target)
            sys.exit(0)
        except ValueError as e:
            print(f"Erreur: {e}", file=sys.stderr)
            sys.exit(1)

    # --health
    if "--health" in args:
        print("OK")
        sys.exit(0)

    # Démarrage serveur
    transport = os.environ.get("MCP_TRANSPORT", "stdio")
    host = os.environ.get("MCP_HOST", "0.0.0.0")
    port = int(os.environ.get("MCP_PORT", "8000"))

    logger.info("Serveur MCP RGESN v%s en démarrage...", VERSION)

    if transport == "http":
        tokens = tokens_pour_auth(Path(TOKENS_FILE))
        auth_info = f"activée ({len(tokens)} token(s))" if tokens else "désactivée"
        logger.info("Auth: %s", auth_info)
        logger.info("HTTP: %s:%d", host, port)

    logger.info("Serveur prêt")

    if transport == "http":
        mcp.run(transport="streamable-http", host=host, port=port)
    else:
        mcp.run()
