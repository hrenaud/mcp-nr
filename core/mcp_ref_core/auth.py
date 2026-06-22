"""
Gestion des tokens d'authentification pour le serveur MCP GreenIT.

Fonctionnalités:
  - Charger/sauvegarder tokens depuis/vers fichier JSON
  - Construire verifieur auth (StaticTokenVerifier) avec tokens valides
  - Valider expiration des tokens
  - CLI: générer, lister, révoquer tokens
"""

import json
import logging
import secrets
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger("mcp-ref-core")


def charger_tokens(path: Path) -> dict:
    """Charge le fichier tokens.json.

    Args:
        path: Chemin vers le fichier tokens.json

    Returns:
        Dict contenant les tokens ou {} si le fichier n'existe pas
    """
    path = Path(path)
    if path.exists():
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error("Erreur lors du chargement de tokens.json: %s", e)
    return {}


def sauvegarder_tokens(path: Path, tokens: dict) -> None:
    """Sauvegarde le fichier tokens.json.

    Args:
        path: Chemin vers le fichier tokens.json
        tokens: Dict contenant les tokens à sauvegarder
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(tokens, f, ensure_ascii=False, indent=2)


def tokens_pour_auth(path: Path) -> dict:
    """Retourne les tokens valides au format StaticTokenVerifier.

    Filtre les tokens expirés et retourne la structure attendue par
    FastMCP's StaticTokenVerifier.

    Args:
        path: Chemin vers le fichier tokens.json

    Returns:
        Dict au format StaticTokenVerifier:
        {
            "token_string": {
                "client_id": "...",
                "scopes": ["read"],
                "expires_at": <timestamp> (optionnel)
            }
        }
    """
    now = time.time()
    result = {}
    for token, info in charger_tokens(path).items():
        expires_at = info.get("expires_at")
        if expires_at and expires_at < now:
            continue  # token expiré, on le saute
        entry = {
            "client_id": info.get("client_id", token[:8]),
            "scopes": info.get("scopes", ["read"]),
        }
        if expires_at:
            entry["expires_at"] = int(expires_at)
        result[token] = entry
    return result


def _get_token_verifier_base():
    try:
        from fastmcp.server.auth import TokenVerifier
        return TokenVerifier
    except ImportError:
        return object


try:
    from fastmcp.server.auth import AccessToken
except ImportError:
    AccessToken = None


class DynamicTokenVerifier(_get_token_verifier_base()):
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

    @property
    def tokens(self) -> dict:
        with self._lock:
            return dict(self._tokens)

    async def verify_token(self, token: str):
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
            "client_id": token_value[:8],  # GREENIT: store explicitly
            "name": name,
            "scopes": ["read"],
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

    def list_all(self) -> list:
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

    def get_by_id(self, token_id: str) -> Optional[dict]:
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

    def update(self, token_id: str, name: Optional[str] = None, expires_days: Optional[int] = None) -> Optional[dict]:
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


def construire_verifier(path: Path) -> Optional["DynamicTokenVerifier"]:
    """Construit un DynamicTokenVerifier depuis les tokens valides.

    Args:
        path: Chemin vers le fichier tokens.json

    Returns:
        DynamicTokenVerifier ou None si aucun token valide
    """
    verifier = DynamicTokenVerifier(path)
    return verifier if verifier.tokens else None


def cmd_generate_token(path: Path, name: str, expires_days: int = 365) -> None:
    """CLI: Générer un nouveau token.

    Crée un token aléatoire, le stocke dans le fichier tokens.json
    et affiche le token généré (ou l'imprime pour capture).

    Args:
        path: Chemin vers le fichier tokens.json
        name: Nom du client (ex: "Alice", "Cursor")
        expires_days: Durée de validité en jours (défaut: 365)
    """
    token = secrets.token_urlsafe(32)
    now = time.time()
    expires_at = int(now + expires_days * 86400)

    tokens = charger_tokens(path)
    tokens[token] = {
        "client_id": token[:8],
        "name": name or "inconnu",
        "scopes": ["read"],
        "created_at": now,
        "expires_at": expires_at,
    }
    sauvegarder_tokens(path, tokens)

    expires_str = datetime.fromtimestamp(expires_at, tz=timezone.utc).strftime("%Y-%m-%d")
    print(token)
    logger.info("Attribué à : %s", name or "inconnu")
    logger.info("Expire le  : %s (%d jours)", expires_str, expires_days)


def cmd_list_tokens(path: Path) -> None:
    """CLI: Lister tous les tokens avec leur statut.

    Affiche un tableau avec ID, Nom, dates de création/expiration et statut.

    Args:
        path: Chemin vers le fichier tokens.json
    """
    tokens = charger_tokens(path)
    now = time.time()
    if not tokens:
        print("Aucun token enregistré.")
        return

    fmt = "{:<12}  {:<20}  {:<12}  {:<12}  {}"
    print(fmt.format("ID", "Nom", "Créé le", "Expire le", "Statut"))
    print("-" * 70)
    for token, info in tokens.items():
        created = datetime.fromtimestamp(info.get("created_at", 0), tz=timezone.utc).strftime("%Y-%m-%d")
        expires_at = info.get("expires_at")
        expires = datetime.fromtimestamp(expires_at, tz=timezone.utc).strftime("%Y-%m-%d") if expires_at else "jamais"
        statut = "EXPIRÉ" if (expires_at and expires_at < now) else "actif"
        print(fmt.format(info.get("client_id", token[:8]), info.get("name", "?"), created, expires, statut))


def cmd_revoke_token(path: Path, token: str) -> None:
    """CLI: Révoquer (supprimer) un token.

    Supprime le token du fichier tokens.json.
    Lève une ValueError si le token n'existe pas.

    Args:
        path: Chemin vers le fichier tokens.json
        token: Token à révoquer

    Raises:
        ValueError: Si le token n'existe pas
    """
    tokens = charger_tokens(path)
    if token not in tokens:
        raise ValueError("Token non trouvé.")
    name = tokens[token].get("name", "?")
    del tokens[token]
    sauvegarder_tokens(path, tokens)
    print(f"Token de '{name}' révoqué.")
