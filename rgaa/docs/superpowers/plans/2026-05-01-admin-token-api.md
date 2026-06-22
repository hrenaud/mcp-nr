# Admin Token API Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ajouter une API HTTP d'administration pour créer, lister, détailler, modifier et révoquer les tokens d'accès MCP, avec rechargement dynamique sans redémarrage.

**Architecture:** `DynamicTokenVerifier` dans `auth.py` remplace `StaticTokenVerifier` : il tient les tokens en mémoire et expose des méthodes CRUD qui écrivent dans `tokens.json` puis rechargent. Les 5 endpoints admin dans `routes.py` reçoivent le vérificateur par injection (pattern identique à `_VERSION`). `rgaa_mcp.py` orchestre le câblage.

**Tech Stack:** Python 3.11, FastMCP (TokenVerifier, AccessToken), Starlette (JSONResponse, TestClient), pytest, threading.Lock

---

## Limitation connue

Si le serveur démarre **sans aucun token**, l'auth middleware FastMCP n'est pas installé. Les tokens créés via l'API admin ne seront actifs qu'après redémarrage dans ce cas. Pour un serveur déjà en production avec des tokens existants, le rechargement est immédiat. Ce comportement est identique à l'existant.

---

## Structure des fichiers

| Fichier | Action | Responsabilité |
|---------|--------|----------------|
| `files/auth.py` | Modifier | Ajouter `DynamicTokenVerifier` (CRUD + reload) + champ `id` dans `cmd_generate_token` |
| `files/routes.py` | Modifier | Ajouter `_token_verifier = None`, helper auth admin, 5 handlers admin |
| `files/rgaa_mcp.py` | Modifier | Câbler `DynamicTokenVerifier`, injecter dans routes, monter les 5 routes |
| `tests/test_admin_api.py` | Créer | Tests unitaires et d'intégration de l'API admin |
| `README.md` | Modifier | Section API admin + variable `ADMIN_TOKEN` |
| `CLAUDE.md` | Modifier | Variable `ADMIN_TOKEN` dans la table |
| `API.md` | Modifier | Documentation des 5 endpoints |
| `ARCHITECTURE.md` | Modifier | Section auth : `DynamicTokenVerifier` |
| `CHANGELOG.md` | Modifier | Entrée nouvelle feature |
| `docker-compose.yml` | Modifier | Variable `ADMIN_TOKEN` |

---

## Task 1 : DynamicTokenVerifier (auth.py)

**Files:**
- Modify: `files/auth.py`
- Test: `tests/test_admin_api.py` (créer)

- [ ] **Étape 1 : Créer le fichier de test avec les tests unitaires du verifier**

```python
# tests/test_admin_api.py
import sys
import json
import time
import pytest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "files"))


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
                "created_at": "2025-01-01T00:00:00+00:00",
                "expires_at": time.time() + 86400,
                "updated_at": "2025-01-01T00:00:00+00:00",
            }
        }
        path.write_text(json.dumps(data))
        return path

    def test_reload_loads_tokens(self, populated_file):
        from auth import DynamicTokenVerifier
        v = DynamicTokenVerifier(populated_file)
        assert "tok_abc" in v._tokens

    def test_reload_ignores_expired(self, tmp_path):
        from auth import DynamicTokenVerifier
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
        assert "tok_old" not in v._tokens

    @pytest.mark.asyncio
    async def test_verify_token_valid(self, populated_file):
        from auth import DynamicTokenVerifier
        v = DynamicTokenVerifier(populated_file)
        result = await v.verify_token("tok_abc")
        assert result is not None
        assert result.client_id == "Alice"

    @pytest.mark.asyncio
    async def test_verify_token_unknown(self, populated_file):
        from auth import DynamicTokenVerifier
        v = DynamicTokenVerifier(populated_file)
        result = await v.verify_token("unknown_token")
        assert result is None

    @pytest.mark.asyncio
    async def test_verify_token_empty_file(self, tokens_file):
        from auth import DynamicTokenVerifier
        v = DynamicTokenVerifier(tokens_file)
        result = await v.verify_token("whatever")
        assert result is None

    def test_create_returns_token_and_id(self, tokens_file):
        from auth import DynamicTokenVerifier
        v = DynamicTokenVerifier(tokens_file)
        result = v.create("Carol", expires_days=30)
        assert "token" in result
        assert len(result["token"]) > 10
        assert len(result["id"]) == 8
        assert result["name"] == "Carol"
        assert result["expires_at"] > time.time()

    def test_create_persists_to_file(self, tokens_file):
        from auth import DynamicTokenVerifier
        v = DynamicTokenVerifier(tokens_file)
        v.create("Dave")
        data = json.loads(tokens_file.read_text())
        assert len(data) == 1

    def test_create_reloads_verifier(self, tokens_file):
        from auth import DynamicTokenVerifier
        v = DynamicTokenVerifier(tokens_file)
        result = v.create("Eve")
        assert result["token"] in v._tokens

    def test_list_all_excludes_tokens_without_id(self, tmp_path):
        from auth import DynamicTokenVerifier
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
        from auth import DynamicTokenVerifier
        v = DynamicTokenVerifier(populated_file)
        result = v.get_by_id("aabb1122")
        assert result is not None
        assert result["name"] == "Alice"

    def test_get_by_id_not_found(self, populated_file):
        from auth import DynamicTokenVerifier
        v = DynamicTokenVerifier(populated_file)
        assert v.get_by_id("zzzzzzzz") is None

    def test_update_name(self, populated_file):
        from auth import DynamicTokenVerifier
        v = DynamicTokenVerifier(populated_file)
        result = v.update("aabb1122", name="Alicia")
        assert result["name"] == "Alicia"

    def test_update_expires_days(self, populated_file):
        from auth import DynamicTokenVerifier
        v = DynamicTokenVerifier(populated_file)
        before = time.time()
        result = v.update("aabb1122", expires_days=10)
        assert result["expires_at"] > before + 9 * 86400

    def test_update_not_found(self, populated_file):
        from auth import DynamicTokenVerifier
        v = DynamicTokenVerifier(populated_file)
        assert v.update("zzzzzzzz", name="X") is None

    def test_revoke_removes_token(self, populated_file):
        from auth import DynamicTokenVerifier
        v = DynamicTokenVerifier(populated_file)
        result = v.revoke("aabb1122")
        assert result is True
        assert v.get_by_id("aabb1122") is None

    def test_revoke_not_found(self, populated_file):
        from auth import DynamicTokenVerifier
        v = DynamicTokenVerifier(populated_file)
        assert v.revoke("zzzzzzzz") is False

    def test_revoke_reloads_verifier(self, populated_file):
        from auth import DynamicTokenVerifier
        v = DynamicTokenVerifier(populated_file)
        v.revoke("aabb1122")
        assert "tok_abc" not in v._tokens
```

- [ ] **Étape 2 : Lancer les tests pour vérifier qu'ils échouent**

```bash
cd /path/to/mcp-rgaa && python -m pytest tests/test_admin_api.py::TestDynamicTokenVerifier -v
```

Résultat attendu : `ImportError: cannot import name 'DynamicTokenVerifier' from 'auth'`

- [ ] **Étape 3 : Implémenter DynamicTokenVerifier dans auth.py**

Ajouter ces imports en tête de `files/auth.py` (après les imports existants) :

```python
import threading
from fastmcp.server.auth import TokenVerifier, AccessToken
```

Remplacer la fonction `construire_verifier` et ajouter la classe après elle :

```python
class DynamicTokenVerifier(TokenVerifier):
    def __init__(self, path: Path):
        super().__init__()
        self._path = path
        self._lock = threading.Lock()
        self._tokens: dict = {}
        self.reload()

    def reload(self) -> None:
        tokens = tokens_pour_auth(self._path)
        with self._lock:
            self._tokens = tokens

    async def verify_token(self, token: str) -> AccessToken | None:
        with self._lock:
            info = self._tokens.get(token)
        if not info:
            return None
        return AccessToken(
            token=token,
            client_id=info["client_id"],
            scopes=info.get("scopes", []),
            expires_at=info.get("expires_at"),
            claims=info,
        )

    def create(self, name: str, expires_days: int = 365) -> dict:
        token_value = secrets.token_urlsafe(32)
        token_id = secrets.token_hex(4)
        expires_at = time.time() + expires_days * 86400
        now = datetime.now(timezone.utc).isoformat()
        tokens = charger_tokens(self._path)
        tokens[token_value] = {
            "id": token_id,
            "name": name,
            "created_at": now,
            "expires_at": expires_at,
            "updated_at": now,
        }
        sauvegarder_tokens(self._path, tokens)
        self.reload()
        return {
            "token": token_value,
            "id": token_id,
            "name": name,
            "expires_at": int(expires_at),
            "created_at": now,
        }

    def list_all(self) -> list[dict]:
        now_ts = time.time()
        result = []
        for _token_val, info in charger_tokens(self._path).items():
            token_id = info.get("id")
            if not token_id:
                continue
            expires_at = info.get("expires_at", 0)
            status = "expired" if expires_at and expires_at < now_ts else "active"
            result.append({
                "id": token_id,
                "name": info.get("name", ""),
                "created_at": info.get("created_at", ""),
                "expires_at": int(expires_at) if expires_at else None,
                "updated_at": info.get("updated_at", ""),
                "status": status,
            })
        return result

    def get_by_id(self, token_id: str) -> dict | None:
        now_ts = time.time()
        for _token_val, info in charger_tokens(self._path).items():
            if info.get("id") == token_id:
                expires_at = info.get("expires_at", 0)
                status = "expired" if expires_at and expires_at < now_ts else "active"
                return {
                    "id": token_id,
                    "name": info.get("name", ""),
                    "created_at": info.get("created_at", ""),
                    "expires_at": int(expires_at) if expires_at else None,
                    "updated_at": info.get("updated_at", ""),
                    "status": status,
                }
        return None

    def update(self, token_id: str, name: str | None = None, expires_days: int | None = None) -> dict | None:
        tokens = charger_tokens(self._path)
        for token_val, info in tokens.items():
            if info.get("id") == token_id:
                if name is not None:
                    info["name"] = name
                if expires_days is not None:
                    info["expires_at"] = time.time() + expires_days * 86400
                info["updated_at"] = datetime.now(timezone.utc).isoformat()
                tokens[token_val] = info
                sauvegarder_tokens(self._path, tokens)
                self.reload()
                return self.get_by_id(token_id)
        return None

    def revoke(self, token_id: str) -> bool:
        tokens = charger_tokens(self._path)
        for token_val, info in list(tokens.items()):
            if info.get("id") == token_id:
                del tokens[token_val]
                sauvegarder_tokens(self._path, tokens)
                self.reload()
                return True
        return False


def construire_verifier(path: Path) -> "DynamicTokenVerifier | None":
    verifier = DynamicTokenVerifier(path)
    return verifier if verifier._tokens else None
```

- [ ] **Étape 4 : Lancer les tests pour vérifier qu'ils passent**

```bash
python -m pytest tests/test_admin_api.py::TestDynamicTokenVerifier -v
```

Résultat attendu : tous les tests `PASSED`

- [ ] **Étape 5 : Vérifier que les tests existants passent toujours**

```bash
python -m pytest tests/ -v --tb=short
```

Résultat attendu : aucune régression

- [ ] **Étape 6 : Commit**

```bash
git add files/auth.py tests/test_admin_api.py
git commit -m "feat: add DynamicTokenVerifier with CRUD methods"
```

---

## Task 2 : Câbler DynamicTokenVerifier dans rgaa_mcp.py

**Files:**
- Modify: `files/rgaa_mcp.py`

- [ ] **Étape 1 : Écrire les tests de câblage dans test_admin_api.py**

Ajouter à la fin de `tests/test_admin_api.py` :

```python
class TestRgaaMcpWiring:
    def test_create_mcp_uses_dynamic_verifier_with_tokens(self, monkeypatch, tmp_path):
        import json as _json
        import time as _time
        import rgaa_mcp as mod
        from auth import DynamicTokenVerifier

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
        monkeypatch.setattr(mod, "TOKENS_FILE", str(path))
        mcp_instance = mod._create_mcp()
        assert isinstance(mcp_instance._auth, DynamicTokenVerifier)

    def test_create_mcp_no_auth_when_no_tokens(self, monkeypatch, tmp_path):
        import rgaa_mcp as mod
        path = tmp_path / "tokens.json"
        monkeypatch.setenv("MCP_TRANSPORT", "http")
        monkeypatch.setattr(mod, "TOKENS_FILE", str(path))
        mcp_instance = mod._create_mcp()
        assert mcp_instance._auth is None

    def test_verifier_injected_in_routes(self, monkeypatch, tmp_path):
        import json as _json
        import time as _time
        import rgaa_mcp as mod
        import routes
        from auth import DynamicTokenVerifier

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
        monkeypatch.setattr(mod, "TOKENS_FILE", str(path))
        mod._create_mcp()
        assert isinstance(routes._token_verifier, DynamicTokenVerifier)
```

- [ ] **Étape 2 : Lancer pour vérifier l'échec**

```bash
python -m pytest tests/test_admin_api.py::TestRgaaMcpWiring -v
```

Résultat attendu : `AttributeError` ou `AssertionError` — `_auth` est un `StaticTokenVerifier`, pas `DynamicTokenVerifier`

- [ ] **Étape 3 : Mettre à jour _configure_mcp et _create_mcp dans rgaa_mcp.py**

Trouver la fonction `_configure_mcp` dans `files/rgaa_mcp.py` et la remplacer :

```python
def _configure_mcp(mcp_instance) -> None:
    """Configure auth and HTTP routes on the given mcp instance."""
    from auth import DynamicTokenVerifier
    import routes as _routes_mod

    token_path = Path(TOKENS_FILE)
    verifier = DynamicTokenVerifier(token_path)
    _routes_mod._token_verifier = verifier

    if verifier._tokens:
        mcp_instance.auth = verifier
        mcp_instance._auth = verifier
    else:
        mcp_instance._auth = None

    transport = os.environ.get("MCP_TRANSPORT", "stdio")
    if transport == "http":
        mcp_instance.custom_route("/", methods=["GET"])(_http_homepage)
        mcp_instance.custom_route("/install.sh", methods=["GET"])(_http_install_script)
        mcp_instance.custom_route("/guide", methods=["GET"])(_http_guide)
```

Trouver la fonction `_create_mcp` et la remplacer :

```python
def _create_mcp() -> FastMCP:
    """Create and configure a new FastMCP instance (for testing or fresh instances)."""
    from auth import DynamicTokenVerifier
    import routes as _routes_mod

    token_path = Path(TOKENS_FILE)
    verifier = DynamicTokenVerifier(token_path)
    _routes_mod._token_verifier = verifier

    if verifier._tokens:
        mcp_instance = FastMCP("RGAA MCP", auth=verifier)
        mcp_instance._auth = verifier
    else:
        mcp_instance = FastMCP("RGAA MCP")
        mcp_instance._auth = None

    transport = os.environ.get("MCP_TRANSPORT", "stdio")
    if transport == "http":
        mcp_instance.custom_route("/", methods=["GET"])(_http_homepage)
        mcp_instance.custom_route("/install.sh", methods=["GET"])(_http_install_script)
        mcp_instance.custom_route("/guide", methods=["GET"])(_http_guide)
    return mcp_instance
```

- [ ] **Étape 4 : Lancer les tests**

```bash
python -m pytest tests/test_admin_api.py::TestRgaaMcpWiring -v
```

Résultat attendu : tous `PASSED`

- [ ] **Étape 5 : Vérifier les tests existants (notamment TestCreateMcp)**

```bash
python -m pytest tests/ -v --tb=short
```

Résultat attendu : aucune régression. Note : `TestCreateMcp.test_with_tokens_auth_applied` devra être mis à jour si elle vérifie `isinstance(auth, StaticTokenVerifier)` — remplacer par `DynamicTokenVerifier`.

- [ ] **Étape 6 : Commit**

```bash
git add files/rgaa_mcp.py tests/test_admin_api.py
git commit -m "feat: wire DynamicTokenVerifier into rgaa_mcp and routes"
```

---

## Task 3 : Helper d'auth admin + injection dans routes.py

**Files:**
- Modify: `files/routes.py`
- Test: `tests/test_admin_api.py`

- [ ] **Étape 1 : Écrire les tests du helper auth**

Ajouter à la fin de `tests/test_admin_api.py` :

```python
import routes as routes_module
from starlette.testclient import TestClient
from starlette.applications import Starlette
from starlette.routing import Route


def _make_admin_client(monkeypatch, tmp_path, admin_token="secret123"):
    """Crée un TestClient Starlette avec les routes admin câblées."""
    import json as _json
    import time as _time
    from auth import DynamicTokenVerifier

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
```

- [ ] **Étape 2 : Lancer pour vérifier l'échec**

```bash
python -m pytest tests/test_admin_api.py::TestAdminAuth -v
```

Résultat attendu : `AttributeError: module 'routes' has no attribute '_http_admin_list_tokens'`

- [ ] **Étape 3 : Ajouter l'injection et le helper dans routes.py**

En tête de `files/routes.py`, après `_VERSION = ""`, ajouter :

```python
_token_verifier = None  # Injected by rgaa_mcp.py
```

Après les fonctions utilitaires existantes (`_get_base_url`, `_get_token_request_url`), ajouter :

```python
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
```

- [ ] **Étape 4 : Lancer les tests**

```bash
python -m pytest tests/test_admin_api.py::TestAdminAuth -v
```

Résultat attendu : tous `PASSED`

- [ ] **Étape 5 : Vérifier aucune régression**

```bash
python -m pytest tests/ -v --tb=short
```

- [ ] **Étape 6 : Commit**

```bash
git add files/routes.py tests/test_admin_api.py
git commit -m "feat: add admin auth helper and 5 admin route handlers"
```

---

## Task 4 : Tests CRUD complets des endpoints admin

**Files:**
- Test: `tests/test_admin_api.py`

- [ ] **Étape 1 : Ajouter les tests CRUD**

Ajouter à la fin de `tests/test_admin_api.py` :

```python
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
        assert token_value in routes_module._token_verifier._tokens


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
```

- [ ] **Étape 2 : Lancer tous les tests admin**

```bash
python -m pytest tests/test_admin_api.py -v
```

Résultat attendu : tous `PASSED`

- [ ] **Étape 3 : Suite complète**

```bash
python -m pytest tests/ -v --tb=short
```

- [ ] **Étape 4 : Commit**

```bash
git add tests/test_admin_api.py
git commit -m "test: add full CRUD test coverage for admin token API"
```

---

## Task 5 : Monter les routes admin dans rgaa_mcp.py

**Files:**
- Modify: `files/rgaa_mcp.py`

- [ ] **Étape 1 : Ajouter le montage des routes dans _configure_mcp et _create_mcp**

Dans `_configure_mcp`, après les 3 routes publiques existantes, ajouter :

```python
        mcp_instance.custom_route("/admin/tokens", methods=["GET"])(_routes_mod._http_admin_list_tokens)
        mcp_instance.custom_route("/admin/tokens", methods=["POST"])(_routes_mod._http_admin_create_token)
        mcp_instance.custom_route("/admin/tokens/{id}", methods=["GET"])(_routes_mod._http_admin_get_token)
        mcp_instance.custom_route("/admin/tokens/{id}", methods=["PATCH"])(_routes_mod._http_admin_update_token)
        mcp_instance.custom_route("/admin/tokens/{id}", methods=["DELETE"])(_routes_mod._http_admin_delete_token)
```

Faire la même chose dans `_create_mcp`.

- [ ] **Étape 2 : Lancer la suite de tests**

```bash
python -m pytest tests/ -v --tb=short
```

Résultat attendu : aucune régression

- [ ] **Étape 3 : Commit**

```bash
git add files/rgaa_mcp.py
git commit -m "feat: mount admin token routes in HTTP mode"
```

---

## Task 6 : Mise à jour de la documentation

**Files:**
- Modify: `CLAUDE.md`, `README.md`, `API.md`, `ARCHITECTURE.md`, `CHANGELOG.md`, `docker-compose.yml`

- [ ] **Étape 1 : Mettre à jour CLAUDE.md**

Dans la table des variables d'environnement clés, ajouter une ligne :

```markdown
| `ADMIN_TOKEN`       | vide      | Token admin pour l'API de gestion des tokens (HTTP uniquement) |
```

- [ ] **Étape 2 : Mettre à jour docker-compose.yml**

Dans la section `environment`, après `MCP_TOKEN_REQUEST_URL`, ajouter :

```yaml
      # ADMIN_TOKEN: Secret pour l'API d'administration des tokens
      # - Si défini, active les endpoints /admin/tokens/* (GET, POST, PATCH, DELETE)
      # - Utilisé dans le header: Authorization: Bearer <ADMIN_TOKEN>
      # - Laisser vide pour désactiver l'API admin
      ADMIN_TOKEN: ${ADMIN_TOKEN:-}
```

- [ ] **Étape 3 : Mettre à jour README.md**

Ajouter une section "Gestion des tokens via API" après la section sur la gestion CLI des tokens. Contenu :

```markdown
## Gestion des tokens via API (HTTP)

En mode HTTP, si `ADMIN_TOKEN` est défini, les endpoints `/admin/tokens` sont disponibles.

**Lister les tokens :**
\```bash
curl -H "Authorization: Bearer $ADMIN_TOKEN" http://localhost:8001/admin/tokens
\```

**Créer un token :**
\```bash
curl -X POST -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "Alice", "expires_days": 365}' \
  http://localhost:8001/admin/tokens
\```

**Modifier un token (renommer ou prolonger) :**
\```bash
curl -X PATCH -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"expires_days": 180}' \
  http://localhost:8001/admin/tokens/<id>
\```

**Révoquer un token :**
\```bash
curl -X DELETE -H "Authorization: Bearer $ADMIN_TOKEN" \
  http://localhost:8001/admin/tokens/<id>
\```

> **Note :** si le serveur démarre sans token existant, l'auth MCP n'est pas activée au démarrage. Les tokens créés via l'API prendront effet après un redémarrage.
```

- [ ] **Étape 4 : Mettre à jour API.md**

Ajouter une section "Admin Token API" documentant les 5 endpoints avec leurs paramètres, corps de requête, codes de réponse et exemples (reprendre le contenu de la spec `docs/superpowers/specs/2026-05-01-admin-token-api-design.md`, section Endpoints admin).

- [ ] **Étape 5 : Mettre à jour ARCHITECTURE.md**

Trouver la section sur l'authentification et remplacer toute mention de `StaticTokenVerifier` par `DynamicTokenVerifier`. Préciser que le verifier tient les tokens en mémoire avec rechargement dynamique via `reload()`.

- [ ] **Étape 6 : Mettre à jour CHANGELOG.md**

Ajouter en tête du changelog :

```markdown
## [Unreleased]

### Added
- API HTTP d'administration des tokens (`/admin/tokens`) : créer, lister, détailler, modifier, révoquer
- `DynamicTokenVerifier` : rechargement des tokens sans redémarrage du serveur
- Variable d'environnement `ADMIN_TOKEN` pour sécuriser l'API admin
```

- [ ] **Étape 7 : Lancer la suite de tests une dernière fois**

```bash
python -m pytest tests/ -v --tb=short
```

- [ ] **Étape 8 : Commit**

```bash
git add CLAUDE.md README.md API.md ARCHITECTURE.md CHANGELOG.md docker-compose.yml
git commit -m "docs: document admin token API (README, API.md, ARCHITECTURE, CLAUDE.md, docker-compose)"
```
