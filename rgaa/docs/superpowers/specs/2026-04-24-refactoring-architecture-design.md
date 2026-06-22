# Design : Refactoring architecture mcp-rgaa

**Date :** 2026-04-24  
**Scope :** mcp-rgaa (appliqué en parallèle avec mcp-115-greenit)  
**Objectifs :** corriger les dettes techniques, séparation des responsabilités, ressource metadata enrichie, uniformisation Python 3.13

---

## Contexte

Le fichier `files/rgaa_mcp.py` (1589 lignes) concentre toutes les responsabilités : chargement des données, gestion des tokens, routes HTTP, tools, prompts, resources et startup. L'objectif est de découper ce fichier en modules à responsabilité unique, en miroir exact de ce qui sera fait dans mcp-115-greenit.

---

## Structure cible

```
files/
  rgaa_mcp.py       # FastMCP instance, tools, prompts, resources, startup
  data.py           # Chargement cache, accès critères / glossaire / thèmes
  auth.py           # Gestion tokens : generate, list, revoke, load, build_verifier
  routes.py         # Routes HTTP publiques : /, /install.sh, /guide
  analyseur.py      # Inchangé — analyse statique HTML
  rgaa_cache.json   # Inchangé
  audit_types.json  # Inchangé
```

---

## Interfaces des modules

### `data.py`

```python
def charger_cache() -> dict
def obtenir_critere(id: str) -> dict | None
def lister_criteres(theme=None, niveau=None) -> list
def chercher(query: str, scope="all") -> list
def obtenir_terme_glossaire(terme: str) -> dict | None
```

Le cache est chargé une fois au démarrage (pattern conservé). Les fonctions remplacent les appels inline dans `rgaa_mcp.py`.

### `auth.py`

```python
def charger_tokens(path: Path) -> dict
def sauvegarder_tokens(path: Path, tokens: dict) -> None
def generer_token(path: Path, name: str, expires_days: int) -> str
def lister_tokens(path: Path) -> list[dict]
def revoquer_token(path: Path, token: str) -> bool
def construire_verifier(path: Path) -> StaticTokenVerifier | None
```

Interface identique à celle de `mcp-115-greenit/files/auth.py` pour maintenir la symétrie.

### `routes.py`

```python
def register_routes(mcp: FastMCP, base_url: str, token_request_url: str) -> None
# Enregistre : GET /, GET /install.sh, GET /guide
```

### `rgaa_mcp.py` (résidu)

Contient uniquement :
- Instance `mcp = FastMCP("RGAA MCP")`
- Tous les `@mcp.tool()` (10 outils)
- Tous les `@mcp.prompt()` (8 prompts)
- Tous les `@mcp.resource()` (4 resources dont la nouvelle)
- `_configure_mcp()` : appelle `auth.construire_verifier()` + `routes.register_routes()`
- `if __name__ == "__main__"` : CLI (--generate-token, --list-tokens, --revoke-token, --health) + startup

---

## Nouvelle ressource `rgaa://metadata`

```python
@mcp.resource("rgaa://metadata")
async def metadata_resource():
    cache = data.charger_cache()
    criteres = cache["criteres"]
    nb_auto = sum(1 for c in criteres.values() if c.get("automatisable"))
    return {
        "languages": ["fr"],
        "versions": [cache["meta"]["version"]],
        "source": "https://github.com/DISIC/RGAA",
        "updated_at": cache["meta"]["updated_at"],
        "nb_criteres": len(criteres),
        "nb_themes": len(cache.get("themes", {})),
        "taux_automatisable": round(nb_auto / len(criteres) * 100, 1)
    }
```

Resources après refactoring : `rgaa://version`, `rgaa://index`, `rgaa://criteres/{id}`, `rgaa://metadata` (4 au total).

---

## Python 3.13

`Dockerfile` : `FROM python:3.11-slim` → `FROM python:3.13-slim`

Pas de `.mcp.json` côté rgaa (stdio via Docker uniquement), aucune autre modification nécessaire.

---

## Tests

- Les tests existants (`test_tools.py`, `test_analyseur.py`, `test_referentiel.py`, `test_conformite.py`) doivent passer sans modification.
- Les imports dans les tests sont à mettre à jour si des fonctions sont déplacées dans `data.py` ou `auth.py`.
- Ajouter des tests unitaires pour `data.py` et `auth.py` si des fonctions sont extraites avec une logique non triviale.

---

## Ce qui ne change pas

- Comportement observable des 10 tools, 8 prompts, 4 resources
- Format du cache JSON et des tokens
- Variables d'environnement
- Interface CLI (`--generate-token`, etc.)
- `analyseur.py` (aucune modification)
- `release.sh` (aucune modification)
