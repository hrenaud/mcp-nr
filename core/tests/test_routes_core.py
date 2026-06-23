"""Tests for shared core route functions."""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastmcp import FastMCP

from mcp_ref_core import routes


class TestRegisterVersionResource:
    """Tests for the centralized register_version_resource function."""

    def setup_method(self):
        self._orig_mcp_id = routes._MCP_ID
        self._orig_items_key = routes._ITEMS_KEY
        self._orig_version = routes._VERSION
        routes._MCP_ID = "test"
        routes._ITEMS_KEY = "items"
        routes._VERSION = "9.9.9"

    def teardown_method(self):
        routes._MCP_ID = self._orig_mcp_id
        routes._ITEMS_KEY = self._orig_items_key
        routes._VERSION = self._orig_version

    def test_function_exists(self):
        assert hasattr(routes, "register_version_resource")
        assert callable(routes.register_version_resource)

    def test_resource_is_registered(self):
        mcp = FastMCP("test")
        fake_cache = {"meta": {"version": "1.0"}, "items": {}}
        routes.register_version_resource(mcp, lambda: fake_cache)

        import asyncio
        resources = asyncio.run(mcp.list_resources())
        uris = [str(r.uri) for r in resources]
        assert any("test://version" in u for u in uris), f"test://version not found in {uris}"

    def test_resource_returns_unified_structure(self):
        mcp = FastMCP("test")
        fake_cache = {
            "meta": {"version": "3.0", "updated_at": "2026-01-01"},
            "items": {"a": 1, "b": 2, "c": 3},
        }
        routes.register_version_resource(mcp, lambda: fake_cache)

        import asyncio
        result = asyncio.run(mcp.read_resource("test://version"))
        data = json.loads(result.contents[0].content)

        assert data["server_version"] == "9.9.9"
        assert data["referentiel_version"] == "3.0"
        assert data["updated_at"] == "2026-01-01"
        assert data["nb_items"] == 3

    def test_resource_handles_missing_meta(self):
        mcp = FastMCP("test")
        fake_cache = {"items": {"x": 1}}
        routes.register_version_resource(mcp, lambda: fake_cache)

        import asyncio
        result = asyncio.run(mcp.read_resource("test://version"))
        data = json.loads(result.contents[0].content)

        assert data["referentiel_version"] == "inconnue"
        assert data["updated_at"] == "inconnue"
        assert data["nb_items"] == 1


