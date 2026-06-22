# Design : Refactoring architecture mcp-115-greenit

**Date :** 2026-04-24  
**Scope :** mcp-115-greenit (appliqué en parallèle avec mcp-rgaa)  
**Objectifs :** corriger les dettes techniques, séparation des responsabilités, uniformisation Python 3.13

---

## Contexte

Le fichier `files/greenit_mcp_final.py` (~1700 lignes) concentre toutes les responsabilités : chargement des données, calcul EcoIndex, gestion des tokens, routes HTTP, tools, prompts, resources et startup. Des modules legacy inutilisés (`audit_url.py`, `checklist.py`, `report.py`, `remediation.py`) encombrent le répertoire. L'objectif est de découper ce fichier en modules à responsabilité unique, en miroir exact de ce qui est fait dans mcp-rgaa.

---

## Dettes techniques à corriger

1. **Renommage** : `greenit_mcp_final.py` → `greenit_mcp.py` (suffixe `_final` = artefact de développement)
2. **Suppression** des modules legacy inutilisés : `audit_url.py`, `checklist.py`, `report.py`, `remediation.py`
3. **Version Python incohérente** : 3.14 en local (`.mcp.json`), 3.12 en Docker → uniformisé à 3.13

---

## Structure cible

```
files/
  greenit_mcp.py        # FastMCP instance, tools, prompts, resources, startup
  data.py               # Chargement cache et metadata, accès fiches
  auth.py               # Gestion tokens : generate, list, revoke, load, build_verifier
  routes.py             # Routes HTTP publiques : /, /install.sh, /guide
  ecoindex.py           # Quantiles, calcul score 0–100, grade A–G
  greenit_cache.json    # Inchangé
  greenit_metadata.json # Inchangé
```

---

## Interfaces des modules

### `data.py`

```python
def charger_cache() -> dict
def charger_metadata() -> dict
def obtenir_fiche(fiche_id: str) -> dict | None
def lister_fiches(lifecycle=None, resource=None, impact_min=None, priorite_min=None) -> list
def chercher_fiches(terme: str) -> list[dict]   # scoring multi-champs conservé
```

### `auth.py`

```python
def charger_tokens(path: Path) -> dict
def sauvegarder_tokens(path: Path, tokens: dict) -> None
def generer_token(path: Path, name: str, expires_days: int) -> str
def lister_tokens(path: Path) -> list[dict]
def revoquer_token(path: Path, token: str) -> bool
def construire_verifier(path: Path) -> StaticTokenVerifier | None
```

Interface identique à celle de `mcp-rgaa/files/auth.py` pour maintenir la symétrie.

### `ecoindex.py`

```python
QUANTILES_DOM: list[int]
QUANTILES_REQ: list[int]
QUANTILES_SIZE: list[float]

def calculer_score(dom: int, requests: int, size_kb: float) -> float   # 0–100
def score_to_grade(score: float) -> str                                 # A–G
def calculer_ecoindex(dom: int, requests: int, size_kb: float) -> dict
```

Les quantiles hardcodés dans `greenit_mcp_final.py` (lignes 38–50) sont déplacés ici.

### `routes.py`

```python
def register_routes(mcp: FastMCP, base_url: str, token_request_url: str) -> None
# Enregistre : GET /, GET /install.sh, GET /guide
```

### `greenit_mcp.py` (résidu)

Contient uniquement :
- Instance `mcp = FastMCP("GreenIT MCP")`
- Tous les `@mcp.tool()` (9 outils)
- Tous les `@mcp.prompt()` (5 prompts)
- Tous les `@mcp.resource()` (4 resources)
- `_configure_mcp()` : appelle `auth.construire_verifier()` + `routes.register_routes()`
- `if __name__ == "__main__"` : CLI + startup

---

## Python 3.13

| Fichier | Avant | Après |
|---------|-------|-------|
| `Dockerfile` | `python:3.12-slim` | `python:3.13-slim` |
| `.mcp.json` | `python3.14` | `python3.13` |

---

## Tests

- Les tests existants (`tests/test_tools.py`) doivent passer sans modification comportementale.
- Les imports sont à mettre à jour si des fonctions sont déplacées dans `data.py`, `auth.py` ou `ecoindex.py`.
- Ajouter des tests unitaires pour `ecoindex.py` (calcul score, grade) — logique pure, facile à tester isolément.

---

## Ce qui ne change pas

- Comportement observable des 9 tools, 5 prompts, 4 resources
- Format du cache JSON et des tokens
- Variables d'environnement
- Interface CLI (`--generate-token`, etc.)
- `greenit_cache.json`, `greenit_metadata.json` (aucune modification)
