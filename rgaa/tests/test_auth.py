# tests/test_auth.py
import sys
import json
import time
from pathlib import Path
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock, mock_open

sys.path.insert(0, str(Path(__file__).parent.parent / "files"))

import pytest
from mcp_ref_core.auth import (
    charger_tokens,
    sauvegarder_tokens,
    tokens_pour_auth,
    construire_verifier,
    cmd_generate_token,
    cmd_list_tokens,
    cmd_revoke_token,
)


class TestChargerTokens:
    """Tests for charger_tokens function."""

    def test_charger_tokens_file_exists(self, tmp_path):
        """Load tokens from existing file."""
        token_file = tmp_path / "tokens.json"
        test_data = {
            "token1": {"name": "Alice", "expires_at": time.time() + 86400},
            "token2": {"name": "Bob", "expires_at": time.time() + 172800},
        }
        with open(token_file, "w") as f:
            json.dump(test_data, f)

        result = charger_tokens(token_file)
        assert result == test_data
        assert len(result) == 2
        assert result["token1"]["name"] == "Alice"

    def test_charger_tokens_file_not_exists(self, tmp_path):
        """Return empty dict when file doesn't exist."""
        token_file = tmp_path / "nonexistent.json"
        result = charger_tokens(token_file)
        assert result == {}

    def test_charger_tokens_invalid_json(self, tmp_path):
        """Handle invalid JSON gracefully."""
        token_file = tmp_path / "tokens.json"
        token_file.write_text("invalid json {")

        result = charger_tokens(token_file)
        assert result == {}

    def test_charger_tokens_empty_file(self, tmp_path):
        """Handle empty JSON file."""
        token_file = tmp_path / "tokens.json"
        token_file.write_text("{}")

        result = charger_tokens(token_file)
        assert result == {}

    def test_charger_tokens_complex_structure(self, tmp_path):
        """Load tokens with all fields."""
        token_file = tmp_path / "tokens.json"
        test_data = {
            "abc123": {
                "name": "TestToken",
                "created_at": "2026-04-26T10:00:00+00:00",
                "expires_at": 1735689600.0,
            }
        }
        with open(token_file, "w") as f:
            json.dump(test_data, f)

        result = charger_tokens(token_file)
        assert "abc123" in result
        assert result["abc123"]["created_at"] == "2026-04-26T10:00:00+00:00"

    def test_charger_tokens_utf8_encoding(self, tmp_path):
        """Handle UTF-8 characters in token names."""
        token_file = tmp_path / "tokens.json"
        test_data = {
            "token1": {"name": "Utilisateur François", "expires_at": time.time() + 86400}
        }
        with open(token_file, "w", encoding="utf-8") as f:
            json.dump(test_data, f, ensure_ascii=False)

        result = charger_tokens(token_file)
        assert result["token1"]["name"] == "Utilisateur François"


class TestSauvegarderTokens:
    """Tests for sauvegarder_tokens function."""

    def test_sauvegarder_tokens_creates_file(self, tmp_path):
        """Create new file if it doesn't exist."""
        token_file = tmp_path / "new_dir" / "tokens.json"
        test_data = {"token1": {"name": "Alice", "expires_at": time.time() + 86400}}

        sauvegarder_tokens(token_file, test_data)

        assert token_file.exists()
        with open(token_file) as f:
            saved = json.load(f)
        assert saved == test_data

    def test_sauvegarder_tokens_overwrites_existing(self, tmp_path):
        """Overwrite existing file with new data."""
        token_file = tmp_path / "tokens.json"
        old_data = {"old_token": {"name": "Old"}}
        new_data = {"new_token": {"name": "New", "expires_at": time.time() + 86400}}

        with open(token_file, "w") as f:
            json.dump(old_data, f)

        sauvegarder_tokens(token_file, new_data)

        with open(token_file) as f:
            saved = json.load(f)
        assert saved == new_data
        assert "old_token" not in saved

    def test_sauvegarder_tokens_empty_dict(self, tmp_path):
        """Save empty dictionary."""
        token_file = tmp_path / "tokens.json"
        sauvegarder_tokens(token_file, {})

        assert token_file.exists()
        with open(token_file) as f:
            saved = json.load(f)
        assert saved == {}

    def test_sauvegarder_tokens_multiple_nested_dirs(self, tmp_path):
        """Create multiple nested directories as needed."""
        token_file = tmp_path / "a" / "b" / "c" / "tokens.json"
        test_data = {"token1": {"name": "Test"}}

        sauvegarder_tokens(token_file, test_data)

        assert token_file.exists()
        assert token_file.parent.exists()

    def test_sauvegarder_tokens_utf8_characters(self, tmp_path):
        """Save UTF-8 characters correctly."""
        token_file = tmp_path / "tokens.json"
        test_data = {
            "token1": {"name": "Élève François", "expires_at": time.time() + 86400}
        }

        sauvegarder_tokens(token_file, test_data)

        with open(token_file, encoding="utf-8") as f:
            saved = json.load(f)
        assert saved["token1"]["name"] == "Élève François"

    def test_sauvegarder_tokens_json_format(self, tmp_path):
        """Verify saved JSON has proper formatting."""
        token_file = tmp_path / "tokens.json"
        test_data = {"token1": {"name": "Test"}}

        sauvegarder_tokens(token_file, test_data)

        content = token_file.read_text()
        assert "\n" in content  # verify indentation
        assert "  " in content  # 2-space indent


class TestTokensPourAuth:
    """Tests for tokens_pour_auth function."""

    def test_tokens_pour_auth_valid_tokens(self, tmp_path):
        """Return valid non-expired tokens."""
        token_file = tmp_path / "tokens.json"
        future_time = time.time() + 86400
        test_data = {
            "token1abcd1234": {"name": "Alice", "client_id": "token1ab", "expires_at": future_time},
            "token2abcd1234": {"name": "Bob", "client_id": "token2ab", "expires_at": future_time},
        }
        with open(token_file, "w") as f:
            json.dump(test_data, f)

        result = tokens_pour_auth(token_file)

        assert len(result) == 2
        assert "token1abcd1234" in result
        assert "token2abcd1234" in result
        assert result["token1abcd1234"]["client_id"] == "token1ab"
        assert result["token2abcd1234"]["client_id"] == "token2ab"

    def test_tokens_pour_auth_filters_expired(self, tmp_path):
        """Exclude expired tokens."""
        token_file = tmp_path / "tokens.json"
        now = time.time()
        test_data = {
            "valid": {"name": "Alice", "expires_at": now + 86400},
            "expired": {"name": "Bob", "expires_at": now - 86400},
        }
        with open(token_file, "w") as f:
            json.dump(test_data, f)

        result = tokens_pour_auth(token_file)

        assert len(result) == 1
        assert "valid" in result
        assert "expired" not in result

    def test_tokens_pour_auth_no_expiry(self, tmp_path):
        """Include tokens without expiry."""
        token_file = tmp_path / "tokens.json"
        test_data = {
            "persisttoken1234": {"name": "Charlie", "client_id": "persiste"},
        }
        with open(token_file, "w") as f:
            json.dump(test_data, f)

        result = tokens_pour_auth(token_file)

        assert len(result) == 1
        assert result["persisttoken1234"]["client_id"] == "persiste"

    def test_tokens_pour_auth_mixed_expiry(self, tmp_path):
        """Handle mix of expiring and non-expiring tokens."""
        token_file = tmp_path / "tokens.json"
        now = time.time()
        test_data = {
            "expiring": {"name": "Alice", "expires_at": now + 86400},
            "persistent": {"name": "Bob"},
            "expired": {"name": "Charlie", "expires_at": now - 1000},
        }
        with open(token_file, "w") as f:
            json.dump(test_data, f)

        result = tokens_pour_auth(token_file)

        assert len(result) == 2
        assert "expiring" in result
        assert "persistent" in result
        assert "expired" not in result

    def test_tokens_pour_auth_all_expired(self, tmp_path):
        """Return empty dict when all tokens are expired."""
        token_file = tmp_path / "tokens.json"
        now = time.time()
        test_data = {
            "expired1": {"name": "Alice", "expires_at": now - 86400},
            "expired2": {"name": "Bob", "expires_at": now - 172800},
        }
        with open(token_file, "w") as f:
            json.dump(test_data, f)

        result = tokens_pour_auth(token_file)

        assert result == {}

    def test_tokens_pour_auth_no_file(self, tmp_path):
        """Return empty dict when file doesn't exist."""
        token_file = tmp_path / "nonexistent.json"
        result = tokens_pour_auth(token_file)
        assert result == {}

    def test_tokens_pour_auth_expiry_timestamp_included(self, tmp_path):
        """Include expires_at in result as integer."""
        token_file = tmp_path / "tokens.json"
        future_time = time.time() + 86400
        test_data = {
            "token1": {"name": "Alice", "expires_at": future_time},
        }
        with open(token_file, "w") as f:
            json.dump(test_data, f)

        result = tokens_pour_auth(token_file)

        assert "expires_at" in result["token1"]
        assert isinstance(result["token1"]["expires_at"], int)
        assert result["token1"]["expires_at"] == int(future_time)

    def test_tokens_pour_auth_scopes_added(self, tmp_path):
        """Add scopes field to each token."""
        token_file = tmp_path / "tokens.json"
        future_time = time.time() + 86400
        test_data = {
            "token1": {"name": "Alice", "expires_at": future_time},
        }
        with open(token_file, "w") as f:
            json.dump(test_data, f)

        result = tokens_pour_auth(token_file)

        assert result["token1"]["scopes"] == ["read"]

    def test_tokens_pour_auth_token_prefix_fallback(self, tmp_path):
        """Use token prefix as client_id when name missing."""
        token_file = tmp_path / "tokens.json"
        future_time = time.time() + 86400
        test_data = {
            "abcd1234efgh": {"expires_at": future_time},
        }
        with open(token_file, "w") as f:
            json.dump(test_data, f)

        result = tokens_pour_auth(token_file)

        assert result["abcd1234efgh"]["client_id"] == "abcd1234"


class TestConstruireVerifier:
    """Tests for construire_verifier function."""

    def test_construire_verifier_with_valid_tokens(self, tmp_path):
        """Return StaticTokenVerifier when tokens exist."""
        token_file = tmp_path / "tokens.json"
        future_time = time.time() + 86400
        test_data = {
            "token1": {"name": "Alice", "expires_at": future_time},
        }
        with open(token_file, "w") as f:
            json.dump(test_data, f)

        result = construire_verifier(token_file)

        assert result is not None
        assert hasattr(result, "verify_token") or hasattr(result, "tokens")

    def test_construire_verifier_no_tokens(self, tmp_path):
        """Return None when no valid tokens."""
        token_file = tmp_path / "tokens.json"
        with open(token_file, "w") as f:
            json.dump({}, f)

        result = construire_verifier(token_file)

        assert result is None

    def test_construire_verifier_all_expired(self, tmp_path):
        """Return None when all tokens are expired."""
        token_file = tmp_path / "tokens.json"
        now = time.time()
        test_data = {
            "expired": {"name": "Alice", "expires_at": now - 86400},
        }
        with open(token_file, "w") as f:
            json.dump(test_data, f)

        result = construire_verifier(token_file)

        assert result is None

    def test_construire_verifier_file_not_exists(self, tmp_path):
        """Return None when file doesn't exist."""
        token_file = tmp_path / "nonexistent.json"
        result = construire_verifier(token_file)
        assert result is None

    def test_construire_verifier_filters_expired_before_building(self, tmp_path):
        """Only include non-expired tokens in verifier."""
        token_file = tmp_path / "tokens.json"
        now = time.time()
        test_data = {
            "valid": {"name": "Alice", "expires_at": now + 86400},
            "expired": {"name": "Bob", "expires_at": now - 86400},
        }
        with open(token_file, "w") as f:
            json.dump(test_data, f)

        result = construire_verifier(token_file)

        assert result is not None
        # Verifier should only contain 1 token
        assert len(result.tokens) == 1


class TestCmdGenerateToken:
    """Tests for cmd_generate_token function."""

    def test_cmd_generate_token_creates_file(self, tmp_path, capsys):
        """Generate token and save to file."""
        token_file = tmp_path / "tokens.json"

        cmd_generate_token(token_file, "Alice")

        assert token_file.exists()
        with open(token_file) as f:
            data = json.load(f)
        assert len(data) == 1
        token = list(data.keys())[0]
        assert data[token]["name"] == "Alice"

    def test_cmd_generate_token_prints_token(self, tmp_path, capsys):
        """Print generated token to stdout."""
        token_file = tmp_path / "tokens.json"

        cmd_generate_token(token_file, "TestUser")

        captured = capsys.readouterr()
        # mcp_ref_core prints just the token (not a full message)
        lines = captured.out.strip().split('\n')
        assert len(lines) >= 1, "Should print token"
        # First line should be a token (base64-ish)
        assert len(lines[0]) > 20

    def test_cmd_generate_token_custom_expiry(self, tmp_path):
        """Generate token with custom expiry days."""
        token_file = tmp_path / "tokens.json"
        before = time.time()

        cmd_generate_token(token_file, "Bob", expires_days=30)

        after = time.time()
        with open(token_file) as f:
            data = json.load(f)
        token = list(data.keys())[0]
        expires_at = data[token]["expires_at"]
        # Should be approximately 30 days from now (±60s margin for slow CI)
        expected = 30 * 86400
        assert before + expected - 60 <= expires_at <= after + expected + 60

    def test_cmd_generate_token_default_expiry(self, tmp_path):
        """Default expiry is 365 days."""
        token_file = tmp_path / "tokens.json"
        before = time.time()

        cmd_generate_token(token_file, "Charlie")

        after = time.time()
        with open(token_file) as f:
            data = json.load(f)
        token = list(data.keys())[0]
        expires_at = data[token]["expires_at"]
        expected = 365 * 86400
        assert before + expected - 10 <= expires_at <= after + expected + 10

    def test_cmd_generate_token_adds_to_existing(self, tmp_path):
        """Add new token to existing file."""
        token_file = tmp_path / "tokens.json"
        existing = {"old_token": {"name": "Old"}}
        with open(token_file, "w") as f:
            json.dump(existing, f)

        cmd_generate_token(token_file, "New")

        with open(token_file) as f:
            data = json.load(f)
        assert len(data) == 2
        assert "old_token" in data
        assert any(info["name"] == "New" for info in data.values())

    def test_cmd_generate_token_has_created_at(self, tmp_path):
        """Include created_at timestamp as Unix time."""
        token_file = tmp_path / "tokens.json"
        before = time.time()

        cmd_generate_token(token_file, "Test")

        after = time.time()
        with open(token_file) as f:
            data = json.load(f)
        token = list(data.keys())[0]
        assert "created_at" in data[token]
        # Verify it's a Unix timestamp (number between before/after)
        created_at = data[token]["created_at"]
        assert isinstance(created_at, (int, float))
        assert before <= created_at <= after

    def test_cmd_generate_token_unique_tokens(self, tmp_path):
        """Generate unique tokens each time."""
        token_file = tmp_path / "tokens.json"

        cmd_generate_token(token_file, "Alice")
        with open(token_file) as f:
            tokens1 = set(json.load(f).keys())

        cmd_generate_token(token_file, "Bob")
        with open(token_file) as f:
            tokens2 = set(json.load(f).keys())

        assert len(tokens2) == 2
        assert tokens2 > tokens1


class TestCmdListTokens:
    """Tests for cmd_list_tokens function."""

    def test_cmd_list_tokens_empty(self, tmp_path, capsys):
        """Print message when no tokens exist."""
        token_file = tmp_path / "tokens.json"
        with open(token_file, "w") as f:
            json.dump({}, f)

        cmd_list_tokens(token_file)

        captured = capsys.readouterr()
        assert "Aucun token" in captured.out or "aucun" in captured.out.lower()

    def test_cmd_list_tokens_shows_valid(self, tmp_path, capsys):
        """List valid tokens."""
        token_file = tmp_path / "tokens.json"
        future_time = time.time() + 86400
        test_data = {
            "token1234567890ab": {"name": "Alice", "expires_at": future_time, "created_at": time.time(), "client_id": "token12"},
        }
        with open(token_file, "w") as f:
            json.dump(test_data, f)

        cmd_list_tokens(token_file)

        captured = capsys.readouterr()
        assert "Alice" in captured.out
        assert "actif" in captured.out

    def test_cmd_list_tokens_shows_expired(self, tmp_path, capsys):
        """Mark expired tokens in list."""
        token_file = tmp_path / "tokens.json"
        now = time.time()
        test_data = {
            "expiredtoken12345": {"name": "Bob", "expires_at": now - 86400, "created_at": now - 172800, "client_id": "expired"},
        }
        with open(token_file, "w") as f:
            json.dump(test_data, f)

        cmd_list_tokens(token_file)

        captured = capsys.readouterr()
        assert "Bob" in captured.out
        assert "EXPIRÉ" in captured.out

    def test_cmd_list_tokens_no_expiry_marked_active(self, tmp_path, capsys):
        """Mark tokens without expiry as active."""
        token_file = tmp_path / "tokens.json"
        test_data = {
            "persisttoken123456": {"name": "Charlie", "created_at": time.time(), "client_id": "persist"},
        }
        with open(token_file, "w") as f:
            json.dump(test_data, f)

        cmd_list_tokens(token_file)

        captured = capsys.readouterr()
        assert "Charlie" in captured.out
        assert "actif" in captured.out

    def test_cmd_list_tokens_multiple(self, tmp_path, capsys):
        """List multiple tokens."""
        token_file = tmp_path / "tokens.json"
        future = time.time() + 86400
        past = time.time() - 86400
        test_data = {
            "tokenactive1234567": {"name": "Alice", "expires_at": future},
            "tokenexpired123456": {"name": "Bob", "expires_at": past},
            "tokenpersist123456": {"name": "Charlie"},
        }
        with open(token_file, "w") as f:
            json.dump(test_data, f)

        cmd_list_tokens(token_file)

        captured = capsys.readouterr()
        assert "Alice" in captured.out
        assert "Bob" in captured.out
        assert "Charlie" in captured.out
        assert "EXPIRÉ" in captured.out
        assert "actif" in captured.out

    def test_cmd_list_tokens_truncates_token(self, tmp_path, capsys):
        """Show client_id (token[:8]) in list."""
        token_file = tmp_path / "tokens.json"
        long_token = "a" * 50
        test_data = {
            long_token: {"name": "Test", "expires_at": time.time() + 86400, "created_at": time.time(), "client_id": "aaaaaaaa"},
        }
        with open(token_file, "w") as f:
            json.dump(test_data, f)

        cmd_list_tokens(token_file)

        captured = capsys.readouterr()
        # mcp_ref_core shows client_id which is first 8 chars
        assert "aaaaaaaa" in captured.out
        assert "Test" in captured.out


class TestCmdRevokeToken:
    """Tests for cmd_revoke_token function."""

    def test_cmd_revoke_token_removes_token(self, tmp_path, capsys):
        """Remove token from file."""
        token_file = tmp_path / "tokens.json"
        test_data = {
            "token_to_revoke": {"name": "Alice"},
            "token_to_keep": {"name": "Bob"},
        }
        with open(token_file, "w") as f:
            json.dump(test_data, f)

        cmd_revoke_token(token_file, "token_to_revoke")

        with open(token_file) as f:
            data = json.load(f)
        assert "token_to_revoke" not in data
        assert "token_to_keep" in data

    def test_cmd_revoke_token_prints_success(self, tmp_path, capsys):
        """Print success message when token revoked."""
        token_file = tmp_path / "tokens.json"
        test_data = {"token1": {"name": "Alice"}}
        with open(token_file, "w") as f:
            json.dump(test_data, f)

        cmd_revoke_token(token_file, "token1")

        captured = capsys.readouterr()
        assert "révoqué" in captured.out.lower()

    def test_cmd_revoke_token_not_found(self, tmp_path):
        """Raise ValueError when token not found."""
        token_file = tmp_path / "tokens.json"
        test_data = {"token1": {"name": "Alice"}}
        with open(token_file, "w") as f:
            json.dump(test_data, f)

        with pytest.raises(ValueError):
            cmd_revoke_token(token_file, "nonexistent")

    def test_cmd_revoke_token_empty_file(self, tmp_path):
        """Raise ValueError on empty token file."""
        token_file = tmp_path / "tokens.json"
        with open(token_file, "w") as f:
            json.dump({}, f)

        with pytest.raises(ValueError):
            cmd_revoke_token(token_file, "any_token")

    def test_cmd_revoke_token_persists_changes(self, tmp_path):
        """Verify token file is updated on disk."""
        token_file = tmp_path / "tokens.json"
        test_data = {"token1": {"name": "Alice"}, "token2": {"name": "Bob"}}
        with open(token_file, "w") as f:
            json.dump(test_data, f)

        cmd_revoke_token(token_file, "token1")

        # Read file again to verify persistence
        with open(token_file) as f:
            data = json.load(f)
        assert "token1" not in data
        assert "token2" in data

    def test_cmd_revoke_token_case_sensitive(self, tmp_path):
        """Token revocation is case-sensitive."""
        token_file = tmp_path / "tokens.json"
        test_data = {"TOKEN1": {"name": "Alice"}}
        with open(token_file, "w") as f:
            json.dump(test_data, f)

        with pytest.raises(ValueError):
            cmd_revoke_token(token_file, "token1")  # lowercase

        # Verify token still exists
        with open(token_file) as f:
            data = json.load(f)
        assert "TOKEN1" in data
