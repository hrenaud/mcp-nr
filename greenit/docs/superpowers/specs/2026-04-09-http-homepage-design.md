# Design — HTTP Homepage, Install Script & Guide

**Date:** 2026-04-09  
**Scope:** Mode HTTP uniquement (`MCP_TRANSPORT=http`)

## Contexte

Le serveur MCP GreenIT tourne en mode HTTP (FastMCP + Starlette). Il expose déjà `/mcp` (protégé par token Bearer). Ce design ajoute 3 routes publiques pour faciliter la découverte et l'installation par les utilisateurs finaux (non-développeurs).

## Approche retenue

Routes custom ajoutées directement dans `greenit_mcp_final.py` via le mécanisme de routes Starlette de FastMCP. Pas de container ni de processus supplémentaire.

## Nouvelles variables d'environnement

| Variable | Défaut | Usage |
|---|---|---|
| `MCP_BASE_URL` | `http://<MCP_HOST>:<MCP_PORT>` | URL publique du serveur, injectée dans le script d'install et la page guide |
| `MCP_TOKEN_REQUEST_URL` | `""` | URL du formulaire de demande de token (Google Form ou autre) |

## Routes ajoutées

Toutes publiques (pas d'authentification). Actives uniquement si `MCP_TRANSPORT=http`.

| Route | Content-Type | Description |
|---|---|---|
| `GET /` | `text/html` | Homepage |
| `GET /install.sh` | `text/plain; charset=utf-8` | Script bash d'installation |
| `GET /guide` | `text/html` | Page de documentation |

## Homepage (`/`)

Page HTML sobre :
- Titre "GreenIT MCP" + badge version (depuis `VERSION`)
- Statut dynamique : nombre de fiches chargées (ou avertissement si cache vide)
- Lien vers `/install.sh` et `/guide`
- Design minimaliste, fond sombre, inspiré de mcp.opquast.com

## Script d'installation (`/install.sh`)

Servi dynamiquement — `MCP_BASE_URL` est injectée au moment de la requête.

```
curl -sSL https://…/install.sh | bash -s -- <TOKEN> [--local] [--authorize] [--uninstall]
```

### Étapes d'installation

1. **Vérification prérequis** — `claude` CLI doit être installé
2. **Ajout du serveur MCP** :
   ```
   claude mcp add greenit <MCP_BASE_URL>/mcp -t http -s <scope> -H "Authorization: Bearer <TOKEN>"
   ```
3. **Pré-autorisation** (si `--authorize`) — écrit `mcp__greenit__*` dans `.claude/settings.json`
4. **Résumé** — commandes de démarrage, lien vers `/guide`

### Mode désinstallation (`--uninstall`)

- Détecte si `greenit` est installé dans `~/.claude.json`
- Exécute `claude mcp remove greenit -s <scope>`
- Nettoie `.claude/settings.json` si nécessaire

### Arguments

| Argument | Description |
|---|---|
| `<TOKEN>` | Token Bearer (obligatoire sauf `--uninstall`) |
| `--local` | Scope projet courant (défaut : user = global) |
| `--authorize` | Pré-autorise tous les outils sans confirmation interactive |
| `--uninstall` | Désinstalle le serveur MCP |

Pas de validation de format du token.

### Adaptations par rapport au script Opquast de référence

**Supprimé :**
- Validation format token (préfixe `oqs_mcp_`) — nos tokens n'ont pas de format fixe
- Étape browser tool (Playwright / Chrome DevTools) — hors scope
- Check Node.js / npx — non nécessaire
- Étape statistiques anonymes (`/install-event`) — endpoint inexistant

**Adapté :**
- Nom du serveur MCP : `opquast` → `greenit`
- URL MCP : injectée dynamiquement depuis `MCP_BASE_URL` au moment de servir le script
- Patterns d'autorisation : `mcp__opquast__*` → `mcp__greenit__*`
- Lien demande de token : `MCP_TOKEN_REQUEST_URL` (formulaire admin) à la place du login Opquast
- Exemples de prompts finaux : remplacés par des exemples GreenIT
- 4 étapes → 3 étapes (prérequis, installation, autorisation)

**Conservé :**
- Structure `main()` wrapper (compatibilité `curl | bash`)
- Couleurs ANSI, mise en forme
- Détection scope via `~/.claude.json` (Python inline)
- `claude mcp add/remove` avec gestion scope user/local
- Mode `--uninstall` + nettoyage `.claude/settings.json`
- Gestion interactive / non-interactif (`/dev/tty`)

## Page de documentation (`/guide`)

Page HTML structurée en sections :

1. **Prérequis** — Claude Code CLI (`npm install -g @anthropic-ai/claude-code`)
2. **Demander un accès** — lien vers `MCP_TOKEN_REQUEST_URL` (ou message si non configuré)
3. **Installation** — commande `curl … | bash -s -- <TOKEN>`
4. **Installation manuelle** — snippet JSON pour autres clients MCP (Cursor, VS Code…)
5. **Outils disponibles** — tableau des 8 outils avec description courte
6. **Exemples de prompts** — 4-5 exemples concrets

## Implémentation

- Tout dans `greenit_mcp_final.py` : les 3 handlers sont des fonctions async Starlette ajoutées à l'app FastMCP
- HTML inline (strings Python) — pas de fichiers de templates séparés
- Le script `install.sh` est généré à la volée avec f-string Python (injection de `MCP_BASE_URL`)
- `docker-compose.yml` : ajout des 2 nouvelles variables d'env

## Non concerné

- Mode stdio : aucun changement
- Authentification `/mcp` : inchangée
- Génération de tokens : reste une opération admin (CLI serveur)
