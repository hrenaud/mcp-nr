"""Shared factory functions for all MCP servers."""

import logging
import os
import sys
from pathlib import Path

from fastmcp import FastMCP

logger = logging.getLogger("mcp-ref-core")


def create_mcp(name: str, tokens_file: str, tool_definitions_fn, guide_extra_sections_fn=None) -> FastMCP:
    """Create and configure a FastMCP instance with shared setup."""
    from mcp_ref_core.auth import DynamicTokenVerifier
    from mcp_ref_core import routes as _routes_mod

    token_path = Path(tokens_file)
    verifier = DynamicTokenVerifier(token_path)
    _routes_mod._token_verifier = verifier
    _routes_mod._get_tool_definitions = tool_definitions_fn
    if guide_extra_sections_fn is not None:
        _routes_mod._guide_extra_sections = guide_extra_sections_fn

    if verifier.tokens:
        mcp_instance = FastMCP(name, auth=verifier)
        mcp_instance._auth = verifier
    else:
        mcp_instance = FastMCP(name)
        mcp_instance._auth = None

    transport = os.environ.get("MCP_TRANSPORT", "stdio")
    if transport == "http":
        from mcp_ref_core.routes import (
            _http_admin_create_token,
            _http_admin_delete_token,
            _http_admin_get_token,
            _http_admin_list_tokens,
            _http_admin_update_token,
            _http_guide,
            _http_homepage,
            _http_install_script,
        )
        mcp_instance.custom_route("/", methods=["GET"])(_http_homepage)
        mcp_instance.custom_route("/install.sh", methods=["GET"])(_http_install_script)
        mcp_instance.custom_route("/guide", methods=["GET"])(_http_guide)
        mcp_instance.custom_route("/admin/tokens", methods=["GET"])(_http_admin_list_tokens)
        mcp_instance.custom_route("/admin/tokens", methods=["POST"])(_http_admin_create_token)
        mcp_instance.custom_route("/admin/tokens/{id}", methods=["GET"])(_http_admin_get_token)
        mcp_instance.custom_route("/admin/tokens/{id}", methods=["PATCH"])(_http_admin_update_token)
        mcp_instance.custom_route("/admin/tokens/{id}", methods=["DELETE"])(_http_admin_delete_token)

    return mcp_instance


def run_main(mcp, version: str, mcp_name: str, cache_fn, items_key: str, tokens_file: str) -> None:
    """Handle CLI arguments and run the MCP server."""
    from mcp_ref_core.auth import cmd_generate_token, cmd_list_tokens, cmd_revoke_token, tokens_pour_auth

    args = sys.argv[1:]
    cache = cache_fn()
    nb = len(cache.get(items_key, {}))

    if "--health" in args:
        if nb > 0:
            print(f"OK: {nb} {items_key} chargés")
            sys.exit(0)
        else:
            print("ERREUR: Cache vide")
            sys.exit(1)

    tokens_path = Path(tokens_file)

    if "--generate-token" in args:
        try:
            name_arg = args[args.index("--name") + 1] if "--name" in args else None
            days = int(args[args.index("--expires-days") + 1]) if "--expires-days" in args else 365
            cmd_generate_token(tokens_path, name_arg, days)
        except (IndexError, ValueError) as e:
            print(f"Erreur d'argument : {e}", file=sys.stderr)
            sys.exit(1)
        sys.exit(0)

    if "--list-tokens" in args:
        cmd_list_tokens(tokens_path)
        sys.exit(0)

    if "--revoke-token" in args:
        try:
            token = args[args.index("--revoke-token") + 1]
            cmd_revoke_token(tokens_path, token)
        except (IndexError, ValueError) as e:
            print(f"Erreur : {e}", file=sys.stderr)
            sys.exit(1)
        sys.exit(0)

    transport = os.environ.get("MCP_TRANSPORT", "stdio")
    if transport == "http":
        host = os.environ.get("MCP_HOST", "0.0.0.0")
        port = int(os.environ.get("MCP_PORT", "8000"))
        active_tokens = tokens_pour_auth(tokens_path)
        auth_info = f"activée ({len(active_tokens)} token(s))" if active_tokens else "désactivée"
        logger.info("Auth: %s", auth_info)
        logger.info("HTTP: %s:%d", host, port)
        mcp.run(transport="streamable-http", host=host, port=port)
    else:
        mcp.run(transport="stdio")
