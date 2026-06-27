"""Parité du périmètre infra/auth entre les 3 MCP.

CLAUDE.md impose un fonctionnement identique. Sur le périmètre infra (Dockerfile,
docker-compose, gestion des tokens), les seules divergences permises sont : nom/id
du MCP, port externe, et dépendances réelles (rgaa = beautifulsoup4 lxml).

Ce test échoue à la moindre divergence non autorisée — il garde contre la dérive
qui a désactivé silencieusement l'auth de rgesn en prod (volume nommé vide).
"""

import re
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
MCPS = ["greenit", "rgaa", "rgesn"]


def _norm_dockerfile(text: str, mcp: str) -> str:
    text = text.replace(mcp, "<MCP>")
    text = text.replace(" beautifulsoup4 lxml", "")  # dépendance légitime rgaa
    lines = [l.rstrip() for l in text.splitlines()]
    lines = [l for l in lines if l and not l.lstrip().startswith("#")]
    return "\n".join(lines)


def test_dockerfiles_identiques_modulo_nom_et_deps():
    norms = {m: _norm_dockerfile((ROOT / m / "Dockerfile").read_text(), m) for m in MCPS}
    assert norms["greenit"] == norms["rgesn"], "Dockerfile greenit diverge de rgesn"
    assert norms["rgaa"] == norms["rgesn"], "Dockerfile rgaa diverge de rgesn (hors deps)"


def test_compose_bind_mount_tokens_partout():
    for m in MCPS:
        txt = (ROOT / m / "docker-compose.yml").read_text()
        assert "./tokens:/app/tokens" in txt, f"{m}: doit bind-monter ./tokens:/app/tokens"
        assert f"{m}_tokens:" not in txt, f"{m}: ne doit PAS utiliser de volume nommé {m}_tokens"


def test_compose_invariants_communs():
    for m in MCPS:
        txt = (ROOT / m / "docker-compose.yml").read_text()
        assert "restart: unless-stopped" in txt, f"{m}: restart policy manquante"
        assert "traefik.enable=true" in txt, f"{m}: labels reverse-proxy manquants"
        assert "context: .." in txt, f"{m}: build context doit être la racine du monorepo"


def test_tokens_file_resolu_identiquement():
    """Les 3 *_mcp.py doivent résoudre TOKENS_FILE depuis ../tokens (parent de files/)."""
    canonical = '_BASE_DIR.parent / "tokens" / "tokens.json"'
    for m in MCPS:
        src = (ROOT / m / "files" / f"{m}_mcp.py").read_text()
        assert canonical in src, f"{m}_mcp.py: TOKENS_FILE doit utiliser {canonical}"
