# Spec — Authentification OAuth (brouillon incomplet)

> **État : brouillon — questions ouvertes non résolues.**  
> Cette spec ne doit pas être implémentée en l'état.

## Objectif

Ajouter OAuth comme mode d'authentification complémentaire aux tokens Bearer actuels, pour permettre aux utilisateurs de se connecter sans que l'administrateur génère manuellement un token.

## Contexte

Le système actuel repose sur des tokens Bearer stockés dans `tokens/tokens.json` (un par MCP). L'admin crée un token via CLI ou API admin, le transmet à l'utilisateur, peut le révoquer. C'est explicite et contrôlé mais manuel.

FastMCP 3.2.4 fournit nativement :

- `GitHubProvider` — OAuth GitHub clé en main
- `OAuthProxy` — proxy vers n'importe quel provider (Auth0, Google…) avec `JWTVerifier`
- `MultiAuth` — compose plusieurs modes en séquence (premier qui valide gagne)

## Architecture envisagée

```python
# core/mcp_ref_core/auth.py (ou nouveau fichier)
from fastmcp.server.auth import MultiAuth
from fastmcp.server.auth.providers.github import GitHubProvider

auth = MultiAuth(
    server=GitHubProvider(
        client_id=os.environ["GITHUB_CLIENT_ID"],
        client_secret=os.environ["GITHUB_CLIENT_SECRET"],
        base_url=os.environ["MCP_BASE_URL"],
    ),
    verifiers=[existing_bearer_verifier],  # compat tokens actuels
)
```

Les tokens Bearer existants continueraient de fonctionner (comptes de service, machines). OAuth prendrait en charge les utilisateurs interactifs.

## Variables d'environnement à ajouter

| Variable               | Description                      |
| ---------------------- | -------------------------------- |
| `GITHUB_CLIENT_ID`     | Client ID de l'OAuth App GitHub  |
| `GITHUB_CLIENT_SECRET` | Secret de l'OAuth App GitHub     |
| `OAUTH_PROVIDER`       | `github` \| _(autres à définir)_ |

`MCP_BASE_URL` est déjà requis — sert de `base_url` pour le callback OAuth.

## Questions ouvertes (bloquantes)

### 1. Profil des utilisateurs — non défini

Le choix du provider et de la stratégie d'autorisation dépend entièrement de qui sont les utilisateurs :

| Profil                           | Provider recommandé        | Autorisation                                   |
| -------------------------------- | -------------------------- | ---------------------------------------------- |
| Tous dans la même GitHub org     | `GitHubProvider`           | Vérifier l'appartenance à l'org via API GitHub |
| Développeurs externes variés     | `GitHubProvider`           | Allowlist de usernames                         |
| Non-développeurs (pas de GitHub) | Auth0 / Google             | Allowlist d'emails                             |
| Mix des deux                     | `MultiAuth` multi-provider | À définir                                      |

**→ Décision requise : qui sont les utilisateurs ?**

### 2. Stratégie d'autorisation — non définie

OAuth authentifie (qui es-tu ?) mais n'autorise pas (as-tu le droit ?). Une couche d'autorisation est nécessaire après le flow OAuth. Options :

- Org GitHub ouverte — tout membre de l'org est autorisé (aucune gestion individuelle)
- Allowlist explicite — liste de usernames/emails autorisés (remplace `tokens.json` pour les humains)
- Ouverte — tout compte GitHub valide est accepté (déconseillé si accès restreint)

**→ Décision requise : granularité du contrôle d'accès souhaité ?**

### 3. Multi-provider — scope à définir

GitHub est le candidat naturel pour un usage dev. Un second provider (Google, Auth0) n'est à ajouter que si des utilisateurs n'ont pas de compte GitHub.

**→ Décision requise : un seul provider suffit-il ?**

## Ce qui ne change pas

- Les tokens Bearer continuent de fonctionner (comptes de service, CI, machines)
- L'API admin (`/admin/tokens`) reste disponible pour la gestion des tokens de service
- Le flow d'installation pour l'utilisateur final (guide HTML) sera mis à jour pour refléter OAuth

## Prérequis techniques

- Créer une **GitHub OAuth App** (ou GitHub App) dans les settings GitHub de l'organisation
- Définir l'URL de callback : `{MCP_BASE_URL}/auth/callback`
- `MCP_BASE_URL` obligatoire en production (déjà le cas)
