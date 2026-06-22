@/Users/renaudheluin/.claude/plugins/marketplaces/karpathy-skills/skills/karpathy-guidelines/SKILL.md

# RGAA MCP — Contexte projet

Serveur MCP exposant le référentiel RGAA 4.2.1 (106 critères) à Claude et autres clients MCP.
Stack : Python + FastMCP, transport stdio ou HTTP avec auth Bearer token, Docker.

## Structure

```
files/
  rgaa_mcp.py        # Serveur principal — outils, prompts, ressources, startup
  data.py            # Chargement cache, accès critères / glossaire / thèmes
  auth.py            # Gestion des tokens (generate, list, revoke, verify)
  routes.py          # Routes HTTP publiques (/, /install.sh, /guide)
  analyseur.py       # Analyse statique HTML (8 thèmes automatisables)
  rgaa_cache.json    # Données RGAA embarquées (106 critères, glossaire)
  audit_types.json   # Définition des 3 types d'audit
  preparer_donnees.py  # Mise à jour des données depuis GitHub RGAA officiel
tokens/              # Volume Docker — tokens.json (hors image)
tests/               # pytest — test_tools.py, test_analyseur.py, test_referentiel.py, test_conformite.py
```

## Outils MCP (10)

`rgaa_lister_criteres`, `rgaa_obtenir_critere`, `rgaa_chercher`, `rgaa_glossaire`,
`rgaa_statistiques`, `rgaa_analyser` (URL → violations), `rgaa_checklist`, `rgaa_taux_conformite`,
`rgaa_types_audit`, `rgaa_criteres_audit`

## Prompts MCP (8)

`audit_page`, `rapport_audit`, `expliquer_critere`, `criteres_par_sujet`, `checklist_audit`, `criteres_wcag`,
`audit_par_type`, `audit_rapide` / `audit_complementaire`

## Ressources MCP (4)

`rgaa://version`, `rgaa://index`, `rgaa://criteres/{id}`, `rgaa://metadata`

## Variables d'environnement clés

| Variable            | Défaut    | Usage                                        |
| ------------------- | --------- | -------------------------------------------- |
| `MCP_TRANSPORT`     | `stdio`   | `stdio` ou `http`                            |
| `MCP_PORT`          | `8000`    | Port interne conteneur (exposé en 8001)      |
| `MCP_BASE_URL`      | auto      | URL publique si derrière un reverse proxy    |
| `MCP_TOKEN_REQUEST_URL` | vide  | URL formulaire demande de token              |
| `ADMIN_TOKEN`       | vide      | Token admin pour l'API de gestion des tokens (HTTP uniquement) |

## Commandes fréquentes

```bash
# Lancer en stdio (local)
docker run --rm -i rgaa-mcp

# Lancer en HTTP
docker compose up -d

# Générer un token
docker run --rm -v $(pwd)/tokens:/app/tokens rgaa-mcp --generate-token --name "Alice"

# Tests
python -m pytest tests/ -v

# Release (bumpe VERSION, pyproject.toml, commit + tag)
./release.sh 1.2.0
git push && git push origin v1.2.0

# Mettre à jour les données RGAA
cd files && python3 preparer_donnees.py --telecharger
```

## Conventions

- Version dans `files/rgaa_mcp.py` (`VERSION = "x.y.z"`) et `pyproject.toml` — utiliser `release.sh`
- Tokens stockés dans `tokens/tokens.json` (volume Docker, jamais embarqué dans l'image)
- Analyse statique couvre ~57% des critères ; Playwright MCP côté utilisateur pour le reste
