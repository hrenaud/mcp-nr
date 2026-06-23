import sys
import json
import time
import pytest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "files"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "core"))


class TestDynamicTokenVerifier:
    @pytest.fixture
    def tokens_file(self, tmp_path):
        path = tmp_path / "tokens.json"
        return path

    @pytest.fixture
    def populated_file(self, tmp_path):
        path = tmp_path / "tokens.json"
        data = {
            "tok_abc": {
                "id": "aabb1122",
                "name": "Alice",
                "client_id": "Alice",
                "created_at": time.time(),
                "expires_at": time.time() + 86400,
                "scopes": ["read"],
            }
        }
        path.write_text(json.dumps(data))
        return path

    def test_reload_loads_tokens(self, populated_file):
        from mcp_ref_core.auth import DynamicTokenVerifier
        v = DynamicTokenVerifier(populated_file)
        assert "tok_abc" in v.tokens

    def test_reload_ignores_expired(self, tmp_path):
        from mcp_ref_core.auth import DynamicTokenVerifier
        path = tmp_path / "tokens.json"
        data = {
            "tok_old": {
                "id": "ccdd3344",
                "name": "Bob",
                "created_at": "2020-01-01T00:00:00+00:00",
                "expires_at": time.time() - 1,
                "updated_at": "2020-01-01T00:00:00+00:00",
            }
        }
        path.write_text(json.dumps(data))
        v = DynamicTokenVerifier(path)
        assert "tok_old" not in v.tokens

    @pytest.mark.asyncio
    async def test_verify_token_valid(self, populated_file):
        from mcp_ref_core.auth import DynamicTokenVerifier
        v = DynamicTokenVerifier(populated_file)
        result = await v.verify_token("tok_abc")
        assert result is not None
        assert result.client_id == "Alice"

    @pytest.mark.asyncio
    async def test_verify_token_unknown(self, populated_file):
        from mcp_ref_core.auth import DynamicTokenVerifier
        v = DynamicTokenVerifier(populated_file)
        result = await v.verify_token("unknown_token")
        assert result is None

    @pytest.mark.asyncio
    async def test_verify_token_empty_file(self, tokens_file):
        from mcp_ref_core.auth import DynamicTokenVerifier
        v = DynamicTokenVerifier(tokens_file)
        result = await v.verify_token("whatever")
        assert result is None

    def test_create_returns_token_and_id(self, tokens_file):
        from mcp_ref_core.auth import DynamicTokenVerifier
        v = DynamicTokenVerifier(tokens_file)
        result = v.create("Carol", expires_days=30)
        assert "token" in result
        assert len(result["token"]) > 10
        assert len(result["id"]) == 8
        assert result["name"] == "Carol"
        assert result["expires_at"] > time.time()

    def test_create_persists_to_file(self, tokens_file):
        from mcp_ref_core.auth import DynamicTokenVerifier
        v = DynamicTokenVerifier(tokens_file)
        v.create("Dave")
        data = json.loads(tokens_file.read_text())
        assert len(data) == 1

    def test_create_reloads_verifier(self, tokens_file):
        from mcp_ref_core.auth import DynamicTokenVerifier
        v = DynamicTokenVerifier(tokens_file)
        result = v.create("Eve")
        assert result["token"] in v.tokens

    def test_list_all_excludes_tokens_without_id(self, tmp_path):
        from mcp_ref_core.auth import DynamicTokenVerifier
        path = tmp_path / "tokens.json"
        data = {
            "legacy_tok": {"name": "Legacy", "created_at": "2020-01-01T00:00:00+00:00", "expires_at": time.time() + 86400},
            "new_tok": {"id": "ff001122", "name": "New", "created_at": "2025-01-01T00:00:00+00:00", "expires_at": time.time() + 86400, "updated_at": "2025-01-01T00:00:00+00:00"},
        }
        path.write_text(json.dumps(data))
        v = DynamicTokenVerifier(path)
        lst = v.list_all()
        assert len(lst) == 1
        assert lst[0]["id"] == "ff001122"

    def test_get_by_id_found(self, populated_file):
        from mcp_ref_core.auth import DynamicTokenVerifier
        v = DynamicTokenVerifier(populated_file)
        result = v.get_by_id("aabb1122")
        assert result is not None
        assert result["name"] == "Alice"

    def test_get_by_id_not_found(self, populated_file):
        from mcp_ref_core.auth import DynamicTokenVerifier
        v = DynamicTokenVerifier(populated_file)
        assert v.get_by_id("zzzzzzzz") is None

    def test_update_name(self, populated_file):
        from mcp_ref_core.auth import DynamicTokenVerifier
        v = DynamicTokenVerifier(populated_file)
        result = v.update("aabb1122", name="Alicia")
        assert result["name"] == "Alicia"

    def test_update_expires_days(self, populated_file):
        from mcp_ref_core.auth import DynamicTokenVerifier
        v = DynamicTokenVerifier(populated_file)
        before = time.time()
        result = v.update("aabb1122", expires_days=10)
        assert result["expires_at"] > before + 9 * 86400

    def test_update_not_found(self, populated_file):
        from mcp_ref_core.auth import DynamicTokenVerifier
        v = DynamicTokenVerifier(populated_file)
        assert v.update("zzzzzzzz", name="X") is None

    def test_revoke_removes_token(self, populated_file):
        from mcp_ref_core.auth import DynamicTokenVerifier
        v = DynamicTokenVerifier(populated_file)
        result = v.revoke("aabb1122")
        assert result is True
        assert v.get_by_id("aabb1122") is None

    def test_revoke_not_found(self, populated_file):
        from mcp_ref_core.auth import DynamicTokenVerifier
        v = DynamicTokenVerifier(populated_file)
        assert v.revoke("zzzzzzzz") is False

    def test_revoke_reloads_verifier(self, populated_file):
        from mcp_ref_core.auth import DynamicTokenVerifier
        v = DynamicTokenVerifier(populated_file)
        v.revoke("aabb1122")
        assert "tok_abc" not in v.tokens


class TestRgaaMcpWiring:
    def test_create_mcp_uses_dynamic_verifier_with_tokens(self, monkeypatch, tmp_path):
        import json as _json
        import time as _time
        import rgaa_mcp as mod
        from mcp_ref_core import factory
        from mcp_ref_core.auth import DynamicTokenVerifier

        path = tmp_path / "tokens.json"
        path.write_text(_json.dumps({
            "tok_xyz": {
                "id": "11223344",
                "name": "Test",
                "created_at": "2025-01-01T00:00:00+00:00",
                "expires_at": _time.time() + 86400,
                "updated_at": "2025-01-01T00:00:00+00:00",
            }
        }))
        monkeypatch.setenv("MCP_TRANSPORT", "http")
        mcp_instance = factory.create_mcp("RGAA MCP", str(path), mod._rgaa_tool_definitions, mod._rgaa_guide_extra_sections)
        assert isinstance(mcp_instance._auth, DynamicTokenVerifier)

    def test_create_mcp_no_auth_when_no_tokens(self, monkeypatch, tmp_path):
        import rgaa_mcp as mod
        from mcp_ref_core import factory
        path = tmp_path / "tokens.json"
        monkeypatch.setenv("MCP_TRANSPORT", "http")
        mcp_instance = factory.create_mcp("RGAA MCP", str(path), mod._rgaa_tool_definitions, mod._rgaa_guide_extra_sections)
        assert mcp_instance._auth is None

    def test_verifier_injected_in_routes(self, monkeypatch, tmp_path):
        import json as _json
        import time as _time
        import rgaa_mcp as mod
        from mcp_ref_core import factory, routes
        from mcp_ref_core.auth import DynamicTokenVerifier

        path = tmp_path / "tokens.json"
        path.write_text(_json.dumps({
            "tok_xyz": {
                "id": "aabbccdd",
                "name": "Test",
                "created_at": "2025-01-01T00:00:00+00:00",
                "expires_at": _time.time() + 86400,
                "updated_at": "2025-01-01T00:00:00+00:00",
            }
        }))
        monkeypatch.setenv("MCP_TRANSPORT", "http")
        factory.create_mcp("RGAA MCP", str(path), mod._rgaa_tool_definitions, mod._rgaa_guide_extra_sections)
        assert isinstance(routes._token_verifier, DynamicTokenVerifier)


from mcp_ref_core import routes as routes_module
from starlette.testclient import TestClient
from starlette.applications import Starlette
from starlette.routing import Route


def _make_admin_client(monkeypatch, tmp_path, admin_token="secret123"):
    """Crée un TestClient Starlette avec les routes admin câblées."""
    import json as _json
    import time as _time
    from mcp_ref_core.auth import DynamicTokenVerifier

    path = tmp_path / "tokens.json"
    verifier = DynamicTokenVerifier(path)
    routes_module._token_verifier = verifier

    if admin_token:
        monkeypatch.setenv("ADMIN_TOKEN", admin_token)
    else:
        monkeypatch.delenv("ADMIN_TOKEN", raising=False)

    app = Starlette(routes=[
        Route("/admin/tokens", routes_module._http_admin_list_tokens, methods=["GET"]),
        Route("/admin/tokens", routes_module._http_admin_create_token, methods=["POST"]),
        Route("/admin/tokens/{id}", routes_module._http_admin_get_token, methods=["GET"]),
        Route("/admin/tokens/{id}", routes_module._http_admin_update_token, methods=["PATCH"]),
        Route("/admin/tokens/{id}", routes_module._http_admin_delete_token, methods=["DELETE"]),
    ])
    return TestClient(app, raise_server_exceptions=True)


class TestAdminAuth:
    def test_no_admin_token_env_returns_503(self, monkeypatch, tmp_path):
        client = _make_admin_client(monkeypatch, tmp_path, admin_token=None)
        monkeypatch.delenv("ADMIN_TOKEN", raising=False)
        r = client.get("/admin/tokens", headers={})
        assert r.status_code == 503
        assert r.json()["error"] == "Admin API disabled"

    def test_missing_auth_header_returns_401(self, monkeypatch, tmp_path):
        client = _make_admin_client(monkeypatch, tmp_path)
        r = client.get("/admin/tokens")
        assert r.status_code == 401
        assert r.json()["error"] == "Unauthorized"

    def test_wrong_token_returns_401(self, monkeypatch, tmp_path):
        client = _make_admin_client(monkeypatch, tmp_path)
        r = client.get("/admin/tokens", headers={"Authorization": "Bearer wrong"})
        assert r.status_code == 401

    def test_valid_token_passes(self, monkeypatch, tmp_path):
        client = _make_admin_client(monkeypatch, tmp_path)
        r = client.get("/admin/tokens", headers={"Authorization": "Bearer secret123"})
        assert r.status_code == 200


HEADERS = {"Authorization": "Bearer secret123"}


class TestAdminCreateToken:
    def test_create_returns_201(self, monkeypatch, tmp_path):
        client = _make_admin_client(monkeypatch, tmp_path)
        r = client.post("/admin/tokens", json={"name": "Alice"}, headers=HEADERS)
        assert r.status_code == 201

    def test_create_returns_token_value(self, monkeypatch, tmp_path):
        client = _make_admin_client(monkeypatch, tmp_path)
        r = client.post("/admin/tokens", json={"name": "Alice"}, headers=HEADERS)
        data = r.json()
        assert "token" in data
        assert len(data["token"]) > 10
        assert data["name"] == "Alice"
        assert "id" in data
        assert "expires_at" in data

    def test_create_missing_name_returns_400(self, monkeypatch, tmp_path):
        client = _make_admin_client(monkeypatch, tmp_path)
        r = client.post("/admin/tokens", json={}, headers=HEADERS)
        assert r.status_code == 400

    def test_create_invalid_expires_days_returns_400(self, monkeypatch, tmp_path):
        client = _make_admin_client(monkeypatch, tmp_path)
        r = client.post("/admin/tokens", json={"name": "X", "expires_days": 0}, headers=HEADERS)
        assert r.status_code == 400

    def test_create_token_immediately_usable_in_verifier(self, monkeypatch, tmp_path):
        client = _make_admin_client(monkeypatch, tmp_path)
        r = client.post("/admin/tokens", json={"name": "Bob"}, headers=HEADERS)
        token_value = r.json()["token"]
        # Vérifie que le reload() a bien mis à jour le cache en mémoire
        assert token_value in routes_module._token_verifier.tokens


class TestAdminListTokens:
    def test_list_returns_200(self, monkeypatch, tmp_path):
        client = _make_admin_client(monkeypatch, tmp_path)
        r = client.get("/admin/tokens", headers=HEADERS)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_list_does_not_expose_token_values(self, monkeypatch, tmp_path):
        client = _make_admin_client(monkeypatch, tmp_path)
        client.post("/admin/tokens", json={"name": "Carol"}, headers=HEADERS)
        r = client.get("/admin/tokens", headers=HEADERS)
        for item in r.json():
            assert "token" not in item

    def test_list_shows_created_token(self, monkeypatch, tmp_path):
        client = _make_admin_client(monkeypatch, tmp_path)
        client.post("/admin/tokens", json={"name": "Dave"}, headers=HEADERS)
        r = client.get("/admin/tokens", headers=HEADERS)
        names = [t["name"] for t in r.json()]
        assert "Dave" in names


class TestAdminGetToken:
    def test_get_returns_200(self, monkeypatch, tmp_path):
        client = _make_admin_client(monkeypatch, tmp_path)
        created = client.post("/admin/tokens", json={"name": "Eve"}, headers=HEADERS).json()
        r = client.get(f"/admin/tokens/{created['id']}", headers=HEADERS)
        assert r.status_code == 200
        assert r.json()["name"] == "Eve"

    def test_get_unknown_id_returns_404(self, monkeypatch, tmp_path):
        client = _make_admin_client(monkeypatch, tmp_path)
        r = client.get("/admin/tokens/zzzzzzzz", headers=HEADERS)
        assert r.status_code == 404


class TestAdminUpdateToken:
    def test_patch_name_returns_200(self, monkeypatch, tmp_path):
        client = _make_admin_client(monkeypatch, tmp_path)
        created = client.post("/admin/tokens", json={"name": "Frank"}, headers=HEADERS).json()
        r = client.patch(f"/admin/tokens/{created['id']}", json={"name": "Francis"}, headers=HEADERS)
        assert r.status_code == 200
        assert r.json()["name"] == "Francis"

    def test_patch_expires_days_updates_expiry(self, monkeypatch, tmp_path):
        client = _make_admin_client(monkeypatch, tmp_path)
        created = client.post("/admin/tokens", json={"name": "Grace"}, headers=HEADERS).json()
        r = client.patch(f"/admin/tokens/{created['id']}", json={"expires_days": 10}, headers=HEADERS)
        assert r.status_code == 200
        assert r.json()["expires_at"] > 0

    def test_patch_empty_body_returns_400(self, monkeypatch, tmp_path):
        client = _make_admin_client(monkeypatch, tmp_path)
        created = client.post("/admin/tokens", json={"name": "Hank"}, headers=HEADERS).json()
        r = client.patch(f"/admin/tokens/{created['id']}", json={}, headers=HEADERS)
        assert r.status_code == 400

    def test_patch_unknown_id_returns_404(self, monkeypatch, tmp_path):
        client = _make_admin_client(monkeypatch, tmp_path)
        r = client.patch("/admin/tokens/zzzzzzzz", json={"name": "X"}, headers=HEADERS)
        assert r.status_code == 404

    def test_patch_invalid_expires_days_returns_400(self, monkeypatch, tmp_path):
        client = _make_admin_client(monkeypatch, tmp_path)
        created = client.post("/admin/tokens", json={"name": "Iris"}, headers=HEADERS).json()
        r = client.patch(f"/admin/tokens/{created['id']}", json={"expires_days": -5}, headers=HEADERS)
        assert r.status_code == 400


class TestAdminDeleteToken:
    def test_delete_returns_204(self, monkeypatch, tmp_path):
        client = _make_admin_client(monkeypatch, tmp_path)
        created = client.post("/admin/tokens", json={"name": "Jack"}, headers=HEADERS).json()
        r = client.delete(f"/admin/tokens/{created['id']}", headers=HEADERS)
        assert r.status_code == 204

    def test_delete_removes_token(self, monkeypatch, tmp_path):
        client = _make_admin_client(monkeypatch, tmp_path)
        created = client.post("/admin/tokens", json={"name": "Kim"}, headers=HEADERS).json()
        client.delete(f"/admin/tokens/{created['id']}", headers=HEADERS)
        r = client.get(f"/admin/tokens/{created['id']}", headers=HEADERS)
        assert r.status_code == 404

    def test_delete_unknown_id_returns_404(self, monkeypatch, tmp_path):
        client = _make_admin_client(monkeypatch, tmp_path)
        r = client.delete("/admin/tokens/zzzzzzzz", headers=HEADERS)
        assert r.status_code == 404
