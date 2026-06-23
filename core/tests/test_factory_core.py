"""Tests for the shared MCP factory functions."""

import json
import os
import sys
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from fastmcp import FastMCP

from mcp_ref_core import factory, routes


class TestCreateMcp:
    """Tests for create_mcp factory function."""

    def test_returns_fastmcp_instance(self, tmp_path):
        tokens_file = str(tmp_path / "tokens.json")
        Path(tokens_file).write_text("{}")
        mcp = factory.create_mcp("Test MCP", tokens_file, lambda: [])
        assert isinstance(mcp, FastMCP)

    def test_no_auth_when_no_tokens(self, tmp_path):
        tokens_file = str(tmp_path / "tokens.json")
        Path(tokens_file).write_text("{}")
        mcp = factory.create_mcp("Test MCP", tokens_file, lambda: [])
        assert mcp._auth is None

    def test_sets_token_verifier_on_routes(self, tmp_path):
        tokens_file = str(tmp_path / "tokens.json")
        Path(tokens_file).write_text("{}")
        factory.create_mcp("Test MCP", tokens_file, lambda: [])
        assert routes._token_verifier is not None

    def test_sets_tool_definitions_on_routes(self, tmp_path):
        tokens_file = str(tmp_path / "tokens.json")
        Path(tokens_file).write_text("{}")
        my_fn = lambda: [{"name": "test_tool"}]
        factory.create_mcp("Test MCP", tokens_file, my_fn)
        assert routes._get_tool_definitions is my_fn

    def test_sets_guide_extra_sections_when_provided(self, tmp_path):
        tokens_file = str(tmp_path / "tokens.json")
        Path(tokens_file).write_text("{}")
        my_fn = lambda: "<h2>Extra</h2>"
        factory.create_mcp("Test MCP", tokens_file, lambda: [], guide_extra_sections_fn=my_fn)
        assert routes._guide_extra_sections is my_fn

    def test_no_http_routes_in_stdio_mode(self, tmp_path):
        tokens_file = str(tmp_path / "tokens.json")
        Path(tokens_file).write_text("{}")
        with patch.dict(os.environ, {"MCP_TRANSPORT": "stdio"}):
            mcp = factory.create_mcp("Test MCP", tokens_file, lambda: [])
        assert isinstance(mcp, FastMCP)

    def test_mcp_name_is_set(self, tmp_path):
        tokens_file = str(tmp_path / "tokens.json")
        Path(tokens_file).write_text("{}")
        mcp = factory.create_mcp("My Custom MCP", tokens_file, lambda: [])
        assert mcp.name == "My Custom MCP"


class TestRunMain:
    """Tests for run_main entrypoint function."""

    def _fake_cache(self):
        return {"items": {"a": 1, "b": 2}}

    def _empty_cache(self):
        return {"items": {}}

    def test_health_exits_0_when_cache_non_empty(self, tmp_path):
        tokens_file = str(tmp_path / "tokens.json")
        Path(tokens_file).write_text("{}")
        mcp = MagicMock()
        with patch("sys.argv", ["prog", "--health"]):
            with pytest.raises(SystemExit) as exc:
                factory.run_main(mcp, "1.0", "Test", self._fake_cache, "items", tokens_file)
        assert exc.value.code == 0

    def test_health_exits_1_when_cache_empty(self, tmp_path):
        tokens_file = str(tmp_path / "tokens.json")
        Path(tokens_file).write_text("{}")
        mcp = MagicMock()
        with patch("sys.argv", ["prog", "--health"]):
            with pytest.raises(SystemExit) as exc:
                factory.run_main(mcp, "1.0", "Test", self._empty_cache, "items", tokens_file)
        assert exc.value.code == 1

    def test_generate_token_creates_token(self, tmp_path):
        tokens_file = str(tmp_path / "tokens.json")
        Path(tokens_file).write_text("{}")
        mcp = MagicMock()
        with patch("sys.argv", ["prog", "--generate-token", "--name", "Alice"]):
            with pytest.raises(SystemExit) as exc:
                factory.run_main(mcp, "1.0", "Test", self._fake_cache, "items", tokens_file)
        assert exc.value.code == 0
        data = json.loads(Path(tokens_file).read_text())
        assert len(data) == 1

    def test_list_tokens_exits_0(self, tmp_path):
        tokens_file = str(tmp_path / "tokens.json")
        Path(tokens_file).write_text("{}")
        mcp = MagicMock()
        with patch("sys.argv", ["prog", "--list-tokens"]):
            with pytest.raises(SystemExit) as exc:
                factory.run_main(mcp, "1.0", "Test", self._fake_cache, "items", tokens_file)
        assert exc.value.code == 0

    def test_run_stdio_calls_mcp_run(self, tmp_path):
        tokens_file = str(tmp_path / "tokens.json")
        Path(tokens_file).write_text("{}")
        mcp = MagicMock()
        with patch("sys.argv", ["prog"]):
            with patch.dict(os.environ, {"MCP_TRANSPORT": "stdio"}):
                factory.run_main(mcp, "1.0", "Test", self._fake_cache, "items", tokens_file)
        mcp.run.assert_called_once_with(transport="stdio")

    def test_revoke_token_nonexistent_exits_1(self, tmp_path):
        tokens_file = str(tmp_path / "tokens.json")
        Path(tokens_file).write_text("{}")
        mcp = MagicMock()
        with patch("sys.argv", ["prog", "--revoke-token", "nonexistent_token"]):
            with pytest.raises(SystemExit) as exc:
                factory.run_main(mcp, "1.0", "Test", self._fake_cache, "items", tokens_file)
        assert exc.value.code == 1
