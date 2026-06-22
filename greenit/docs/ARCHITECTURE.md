# GreenIT MCP — Architecture modulaire (Phase 3)

## Vue d'ensemble

Le serveur MCP GreenIT expose le référentiel des bonnes pratiques d'écoconception web (119 fiches) aux clients MCP avec 9 outils pour consultation, recherche, comparaison et calcul d'EcoIndex. L'architecture est modulaire avec séparation des responsabilités pour maintenabilité et testabilité.

**Transport:** stdio (local) ou HTTP (docker-compose)
**Stack:** Python 3.13 + FastMCP 3.2.4
**Données embarquées:** 119 fiches GreenIT + métadonnées
**Tests:** 191 tests (unitaires + Docker + architecture parity)

## Structure modulaire

### Fichiers principaux

#### `files/greenit_mcp.py` — Serveur MCP et outils

Orchestre le serveur FastMCP et enregistre tous les outils MCP.

**Responsabilités:**
- Initialise FastMCP et configure le transport (stdio ou HTTP)
- Enregistre les 9 outils MCP avec schémas de sortie JSON et annotations
- Enregistre les ressources MCP (version, index, fiches, métadonnées)
- Initialise les routes HTTP (GET /, /install.sh, /guide)
- Gère la ligne de commande pour génération/révocation de tokens
- Initialisation FastMCP au démarrage avec authentification Bearer optionnelle

**Clés:**
- Tous les outils partagent la version unique (`VERSION`) définie dans ce fichier
- Les paramètres et schémas de sortie sont définis à l'enregistrement
- Les annotations MCP (readOnlyHint, idempotentHint, openWorldHint) guident les clients
- La gestion des erreurs utilise `ToolError` pour retourner des messages français

#### `files/data.py` — Source unique pour données GreenIT + EcoIndex

Charge le cache GreenIT et expose une API de lecture. Inclut le calcul EcoIndex (fusionné de ecoindex.py en Phase 3).

**Responsabilités:**
- Charge le cache GreenIT (`greenit_cache.json`) avec les 119 fiches
- Accès aux fiches par ID ou par recherche par lifecycle/ressource
- Charge les métadonnées depuis `greenit_metadata.json`
- Caching en mémoire (global `_cache`, `_metadata`)
- Validation sur chargement (lève exception si fichier corrompu)
- **EcoIndex calculation:** calculer_ecoindex(dom, requests, size_kb) → {score, grade}

**Fonctions clés:**
- `charger_cache()` → Retourne le cache GreenIT complet (119 fiches)
- `charger_metadata()` → Retourne les métadonnées (langues, versions)
- `calculer_ecoindex(dom, requests, size_kb)` → Retourne {score (0-100), grade (A-G)}
- `compter_fiches()` → Compte total fiches
- `compter_lifecycles()` → Compte phases de cycle de vie uniques
- `compter_ressources()` → Compte types de ressources sauvegardées uniques
- `calculer_taux_ecoindex_moyen()` → Calcule moyenne EcoIndex sur un set de fiches

**Algorithme EcoIndex:**
L'EcoIndex utilise le scoring par quantile basé sur 3 métriques brutes:
- **q_dom** = quantile du nombre de nœuds DOM (0-20 quantiles)
- **q_req** = quantile du nombre de requêtes HTTP (0-20 quantiles)
- **q_size** = quantile de la taille totale en KB (0-20 quantiles)

Score = 100 - 5 * (3 * q_dom + 2 * q_req + q_size) / 6

Grade assignment:
- A: score > 80
- B: score > 70
- C: score > 55
- D: score > 40
- E: score > 25
- F: score > 10
- G: score ≤ 10

#### `files/_helpers.py` — Fonctions partagées de validation

Extraites en Phase 3 pour cohérence entre mcp-rgaa et greenit-mcp.

**Responsabilités:**
- Centralise la validation des paramètres pour éviter la duplication entre outils
- Retourne `ToolError` avec messages français exploitables

**Fonctions:**
- `validate_themes(themes)` → Valide les numéros de thème (1-13, RGAA uniquement — non utilisée dans greenit-mcp)
- `validate_score_range(value, min_val, max_val, param_name)` → Valide les plages numériques (impact 1-5, priorité 1-5)
- `validate_nonnegative(value, param_name)` → Valide les valeurs positives (dom_nodes, requests, size_kb dans calculer_ecoindex)

#### `files/auth.py` — Gestion des tokens Bearer

Génère, liste, révoque et valide les tokens Bearer pour l'authentification HTTP.

**Responsabilités:**
- Génère tokens signés et stockés dans `tokens/tokens.json` (volume Docker)
- Valide les tokens Bearer pour HTTP (FastMCP crée StaticTokenVerifier)
- Gère l'expiration des tokens (contrôle de validité basé sur `expires_at`)
- Interface CLI pour opérations token (generate-token, list-tokens, revoke-token)

**Fonctions clés:**
- `charger_tokens(path)` → Charge les tokens depuis le volume Docker
- `sauvegarder_tokens(path, tokens)` → Persiste les tokens JSON
- `construire_verifier(path)` → Crée StaticTokenVerifier pour FastMCP
- `cmd_generate_token(path, name, expires_days)` → CLI: génère token
- `cmd_list_tokens(path)` → CLI: énumère tokens actifs
- `cmd_revoke_token(path, token)` → CLI: invalide token

#### `files/routes.py` — Endpoints HTTP

Endpoints HTTP publics accessible via reverse proxy ou docker-compose.

**Responsabilités:**
- Endpoints HTTP GET pour accueil, installation, guide des outils
- HTML pour page d'accueil (avec status des données GreenIT)
- JSON pour /guide (liste tous les outils et paramètres)
- Shell script pour installation rapide
- Génération dynamique de contenu (version injectée par greenit_mcp.py)

**Routes:**
- `GET /` → Page d'accueil HTML (status, liens, instructions)
- `GET /install.sh` → Script shell d'installation avec token
- `GET /guide` → Liste outils + paramètres (JSON ou HTML selon Content-Type)
- `GET /health` → Non incluse dans routes.py (vérification de santé à implémenter optionnellement)

### Fichiers de données

#### `files/greenit_cache.json`

Cache embarqué du référentiel GreenIT (119 fiches).

**Structure:**
```json
{
  "RWEB_0001": {
    "id": "RWEB_0001",
    "titre": "Fiche titre",
    "description": "...",
    "lifecycle": "3-developpement",
    "saved_resources": ["network", "cpu"],
    "impact": 5,
    "priorite": 4
  },
  ...
}
```

#### `files/greenit_metadata.json`

Métadonnées du référentiel (langues, versions supportées).

**Structure:**
```json
{
  "languages": ["fr"],
  "versions": ["latest"],
  "nb_fiches": 119
}
```

## Les 9 outils MCP

| Outil | Description | readonly | destructive | idempotent | openworld |
|-------|-------------|----------|-------------|-----------|-----------|
| `lister_fiches` | Liste fiches avec filtres optionnels (lifecycle, ressource, impact, priorite) | true | false | true | false |
| `fiches_prioritaires` | Retourne fiches à fort impact + haute priorité d'implémentation | true | false | true | false |
| `chercher_fiche` | Recherche fiches par mot-clé avec scoring par pertinence | true | false | true | true |
| `comparer_fiches` | Compare plusieurs fiches côte à côte avec recommandation | true | false | true | false |
| `obtenir_fiche_complete` | Récupère le contenu complet d'une fiche par ID | true | false | true | false |
| `obtenir_statistiques` | Statistiques globales (count, distribution par lifecycle/ressource) | true | false | true | false |
| `lister_lifecycles` | Liste les 7 phases du cycle de vie du référentiel | true | false | true | false |
| `lister_ressources` | Liste les 8 types de ressources sauvegardées | true | false | true | false |
| `calculer_ecoindex` | Calcule l'EcoIndex (score 0-100 + grade A-G) à partir de 3 métriques | true | false | true | false |

**Légende des annotations:**
- `readonly` = Aucun effet destructif (lecteur pur)
- `idempotent` = Résultats stables (pas d'état aléatoire, pas d'I/O côté serveur)
- `openworld` = Données dynamiques ou externes (contenu variable, recherche par mot-clé)

### Détails des outils

#### lister_fiches(lifecycle=None, saved_resource=None, impact_min=None, priorite_min=None)

Liste les 119 fiches avec filtres optionnels par lifecycle, ressource sauvegardée, impact minimum, ou priorité minimum.

**Paramètres:**
- `lifecycle` (str, optionnel) — Filtre sur une phase (ex: "3-developpement")
- `saved_resource` (str, optionnel) — Filtre sur une ressource (ex: "network")
- `impact_min` (int, optionnel) — Impact minimum (1-5)
- `priorite_min` (int, optionnel) — Priorité minimum (1-5)

**Retour:**
```json
{
  "total": 119,
  "fiches": [
    {"id": "RWEB_0001", "titre": "...", "lifecycle": "3-developpement", "impact": 5, "priorite": 4},
    ...
  ]
}
```

#### fiches_prioritaires(impact_min=4, priorite_min=4)

Retourne les fiches avec fort impact (≥4) et haute priorité (≥4) d'implémentation.

**Paramètres:**
- `impact_min` (int, optionnel) — Seuil d'impact (défaut: 4)
- `priorite_min` (int, optionnel) — Seuil de priorité (défaut: 4)

**Retour:**
```json
{
  "total": N,
  "fiches": [...]
}
```

#### chercher_fiche(terme)

Recherche par mot-clé dans les titres, descriptions et tags des fiches.

**Paramètres:**
- `terme` (str, requis) — Terme à chercher

**Retour:**
```json
{
  "correspondances": [
    {"id": "RWEB_0001", "titre": "...", "score": 0.95},
    ...
  ]
}
```

#### comparer_fiches(fiche_ids)

Compare plusieurs fiches côte à côte avec matrice comparative et recommandation.

**Paramètres:**
- `fiche_ids` (list[str], requis) — IDs de fiches à comparer (ex: ["RWEB_0049", "RWEB_0051"])

**Retour:**
```json
{
  "fiches": [...],
  "recommandation": "Fiche X conseillée pour raison Y"
}
```

#### obtenir_fiche_complete(fiche_id)

Récupère le détail complet d'une fiche par ID.

**Paramètres:**
- `fiche_id` (str, requis) — Identifiant de la fiche (ex: "RWEB_0001")

**Retour:** Fiche complète avec tous les champs (titre, description, lifecycle, ressources, impact, priorité, etc.).

**Gestion des erreurs:**
- Fiche inexistante → ToolError avec suggestion similaire
- ID invalide → ToolError avec format attendu

#### obtenir_statistiques()

Retourne les statistiques du référentiel (counts, distribution par lifecycle et par ressource).

**Retour:**
```json
{
  "total_fiches": 119,
  "par_lifecycle": {
    "1-conception": {"count": 15},
    "2-design": {"count": 20},
    ...
  },
  "par_ressource": {
    "network": {"count": 45},
    "cpu": {"count": 38},
    ...
  }
}
```

#### lister_lifecycles()

Liste les 7 phases du cycle de vie du référentiel GreenIT.

**Retour:**
```json
{
  "phases": [
    {"id": "1-conception", "label": "Conception", "count": 15},
    {"id": "2-design", "label": "Design", "count": 20},
    ...
  ]
}
```

#### lister_ressources()

Liste les 8 types de ressources sauvegardées par les bonnes pratiques.

**Retour:**
```json
{
  "ressources": [
    {"id": "network", "label": "Réseau", "count": 45},
    {"id": "cpu", "label": "CPU", "count": 38},
    ...
  ]
}
```

#### calculer_ecoindex(dom_nodes, requests, size_kb, url="")

Calcule l'EcoIndex (score 0-100 et grade A-G) à partir de 3 métriques brutes mesurées par Playwright.

**Paramètres:**
- `dom_nodes` (int, requis) — Nombre de nœuds dans le DOM
- `requests` (int, requis) — Nombre de requêtes HTTP
- `size_kb` (float, requis) — Taille totale transférée en kilo-octets
- `url` (str, optionnel) — URL de la page mesurée (pour contexte)

**Retour:**
```json
{
  "url": "https://example.com",
  "dom_nodes": 1250,
  "requests": 85,
  "size_kb": 2150.5,
  "score": 65.3,
  "grade": "C"
}
```

**Gestion des erreurs:**
- Valeurs négatives → ToolError
- Métriques invalides → ToolError avec format attendu

## Gestion des erreurs

### Niveaux d'erreur

1. **ToolError (erreurs utilisateur)**
   - Paramètres invalides (ex: fiche inexistante)
   - Valeurs hors limites (ex: impact > 5)
   - Format JSON mal formé
   - IDs invalides ou manquants
   - Message français exploitable avec suggestions
   - Exemple: `"Fiche inexistante. ID doit être au format 'RWEB_XXXX'."`

2. **Erreurs système**
   - Fichiers JSON corrompus ou manquants
   - I/O système
   - Loggées en ERROR, retour générique au client
   - FastMCP retourne erreur 500

### Pattern TDD

Chaque outil a:
- Tests positifs (entrées valides → résultats corrects)
- Tests négatifs (paramètres invalides → ToolError avec message français)
- Tests d'intégration (appels multiples, interaction avec données)

## Tests

**Suite complète:** 191 tests passant

| Fichier | Tests | Couverture |
|---------|-------|-----------|
| `tests/test_tools.py` | 91 tests | Les 9 outils + paramètres + erreurs |
| `tests/test_ecoindex.py` | 6 tests | EcoIndex calculation + grade assignment |
| `tests/test_data.py` | 5 tests | Cache loading + metadata + helper functions |
| `tests/test_architecture_parity.py` | 60 tests | Parity with mcp-rgaa patterns |
| `tests/test_docker_integration.py` | 8 tests | Docker deployment + HTTP mode |
| `tests/test_metadata.py` | 9 tests | Metadata handling + content validation |
| `tests/test_prompts.py` | 12 tests | Prompts + resource endpoints |

**Exécution:**
```bash
# Tous les tests
python -m pytest tests/ -v

# Outil spécifique
python -m pytest tests/ -k "lister_fiches"

# Avec couverture
python -m pytest tests/ --cov=files --cov-report=html
```

**Exemple de test:**
```python
def test_lister_fiches_with_lifecycle_filter():
    """Test listing fiches by valid lifecycle."""
    result = lister_fiches(lifecycle="3-developpement")
    assert result["total"] > 0
    assert all(f["lifecycle"] == "3-developpement" for f in result["fiches"])

def test_lister_fiches_with_invalid_lifecycle():
    """Test listing fiches with invalid lifecycle raises ToolError."""
    with pytest.raises(ToolError):
        lister_fiches(lifecycle="invalid-phase")
```

## Déploiement

### Modes de transport

#### Mode stdio (local)

Terminal ou IDE avec FastMCP connecté.

```bash
# Lancer le serveur
python files/greenit_mcp.py

# Avec logging
LOG_LEVEL=DEBUG python files/greenit_mcp.py
```

Variables d'environnement:
- `LOG_LEVEL` — Python logging level (DEBUG, INFO, WARNING, ERROR)

#### Mode HTTP (docker-compose)

Serveur HTTP derrière reverse proxy avec authentification Bearer.

```yaml
services:
  greenit-mcp:
    build: .
    ports:
      - "8002:8000"
    environment:
      MCP_TRANSPORT: http
      MCP_PORT: 8000
      LOG_LEVEL: INFO
    volumes:
      - ./tokens:/app/tokens
```

Lancer:
```bash
docker-compose up -d
```

### Variables d'environnement

| Variable | Défaut | Usage |
|----------|--------|-------|
| `MCP_TRANSPORT` | `stdio` | `stdio` ou `http` |
| `MCP_PORT` | `8000` | Port interne (exposé en 8002 via docker-compose) |
| `MCP_BASE_URL` | auto | URL publique si derrière un reverse proxy |
| `MCP_TOKEN_REQUEST_URL` | vide | URL formulaire demande de token |
| `LOG_LEVEL` | `INFO` | Python logging level (DEBUG, INFO, WARNING, ERROR) |

### Authentification Bearer

Si `MCP_TRANSPORT=http`, les outils requièrent un Bearer token.

**Générer un token:**
```bash
# Dans le conteneur Docker
docker run --rm -v $(pwd)/tokens:/app/tokens greenit-mcp --generate-token --name "Alice" --expires-days 365
# Output: Token généré pour 'Alice' (expire dans 365 jours):
#         abc123def456...

# Ou en local
python files/greenit_mcp.py --generate-token --name "Alice"
```

**Utiliser le token:**
```bash
curl -H "Authorization: Bearer abc123def456..." http://localhost:8002/guide
```

**Lister les tokens:**
```bash
docker run --rm -v $(pwd)/tokens:/app/tokens greenit-mcp --list-tokens
# Output:   abc123def456...  Alice  [actif]
#           xyz789qrs012...  Bob    [EXPIRÉ]
```

**Révoquer un token:**
```bash
docker run --rm -v $(pwd)/tokens:/app/tokens greenit-mcp --revoke-token abc123def456...
```

## Architecture parity avec mcp-rgaa

Phase 3 a aligné les deux services MCP pour cohérence et maintenabilité.

### Structure commune

Les deux services partagent:
- `data.py` — Chargement cache + accès données
- `auth.py` — Gestion tokens Bearer
- `routes.py` — Endpoints HTTP (/, /install.sh, /guide)
- `_helpers.py` — Validation centralisée
- `greenit_mcp.py` / `rgaa_mcp.py` — Serveur principal
- Tests complets avec pytest
- Docker et docker-compose
- Documentation identique (README.md, ARCHITECTURE.md)

### Patterns unifiés

1. **Validation centralisée** — `_helpers.py` pour éviter duplication
2. **Gestion des erreurs** — ToolError avec messages français
3. **Annotations MCP** — readOnlyHint, destructiveHint, idempotentHint, openWorldHint cohérents
4. **Tokens Bearer** — `auth.py` avec `DynamicTokenVerifier` partagé
5. **Routes HTTP** — /, /install.sh, /guide, /admin/tokens
6. **API admin** — GET/POST/PATCH/DELETE /admin/tokens protégés par `ADMIN_TOKEN`
7. **Tests** — test_tools.py, test_data.py, test_architecture_parity.py

### Différences intentionnelles

| Aspect | mcp-rgaa | greenit-mcp |
|--------|----------|-------------|
| **Outils** | 10 (consultation + analyse HTML) | 9 (recherche + comparaison + EcoIndex) |
| **Données** | 106 critères RGAA + glossaire | 119 fiches GreenIT |
| **Analyseur** | HTML statique (8 thèmes) | EcoIndex quantile-based scoring |
| **Types d'audit** | 3 types (complet, rapide, complémentaire) | N/A (lifecycle + ressources) |
| **Nombre de tests** | 227 tests | 191 tests |

### Maintenance

Quand une amélioration est faite dans un service:
1. Implémenter dans le premier service
2. Tester avec pytest
3. Appliquer au second service
4. Synchroniser documentation et tests

Exemples:
- Nouveau pattern d'erreur → Mettre à jour _helpers.py dans les deux
- Nouvelle dépendance → Mettre à jour pyproject.toml et requirements.txt
- Changement API FastMCP → Sync greenit_mcp.py et rgaa_mcp.py

## Fichiers clés

- `/Users/renaudheluin/DEV/DEV_GREENIT/refs/mcp-115-greenit/files/greenit_mcp.py` — Serveur FastMCP, 9 outils
- `/Users/renaudheluin/DEV/DEV_GREENIT/refs/mcp-115-greenit/files/data.py` — Cache GreenIT + EcoIndex calculation
- `/Users/renaudheluin/DEV/DEV_GREENIT/refs/mcp-115-greenit/files/auth.py` — Gestion tokens Bearer
- `/Users/renaudheluin/DEV/DEV_GREENIT/refs/mcp-115-greenit/files/routes.py` — Endpoints HTTP
- `/Users/renaudheluin/DEV/DEV_GREENIT/refs/mcp-115-greenit/files/_helpers.py` — Validation centralisée
- `/Users/renaudheluin/DEV/DEV_GREENIT/refs/mcp-115-greenit/files/greenit_cache.json` — 119 fiches GreenIT embarquées
- `/Users/renaudheluin/DEV/DEV_GREENIT/refs/mcp-115-greenit/files/greenit_metadata.json` — Métadonnées
- `/Users/renaudheluin/DEV/DEV_GREENIT/refs/mcp-115-greenit/tests/` — 191 tests (7 fichiers)
