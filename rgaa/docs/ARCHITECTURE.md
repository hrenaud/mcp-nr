# MCP RGAA — Architecture modulaire (Phase 3)

## Vue d'ensemble

Le serveur MCP RGAA expose le référentiel RGAA 4.2.1 (106 critères) aux clients MCP avec 10 outils pour consultation, recherche et audit. L'architecture est modulaire avec séparation des responsabilités pour maintenabilité et testabilité.

**Transport:** stdio (local) ou HTTP (docker-compose)
**Stack:** Python 3.13 + FastMCP 3.2.4
**Données embarquées:** 106 critères RGAA + glossaire
**Tests:** 227 tests (unitaires + Docker)

## Structure modulaire

### Fichiers principaux

#### `files/rgaa_mcp.py` — Serveur MCP et outils

Orchestre le serveur FastMCP et enregistre tous les outils MCP.

**Responsabilités:**
- Initialise FastMCP et configure le transport (stdio ou HTTP)
- Enregistre les 10 outils MCP avec schémas de sortie JSON et annotations
- Enregistre 8 prompts MCP pour workflows courants
- Enregistre 4 ressources MCP (version, index, critères, métadonnées)
- Initialise les routes HTTP (GET /, /health, /guide)
- Gère la ligne de commande pour génération/révocation de tokens
- Initialisation FastMCP au démarrage avec authentification Bearer optionnelle

**Clés:**
- Tous les outils partagent la version unique (`VERSION`) définie dans ce fichier
- Les paramètres et schémas de sortie sont définis à l'enregistrement
- Les annotations MCP (readOnlyHint, idempotentHint, openWorldHint) guident les clients
- La gestion des erreurs utilise `ToolError` pour retourner des messages français

#### `files/data.py` — Source unique pour données RGAA

Charge le cache RGAA et expose une API de lecture pour tous les outils.

**Responsabilités:**
- Charge le cache RGAA (`rgaa_cache.json`) avec les 106 critères + glossaire
- Accès aux critères par ID ou par recherche par thème/niveau WCAG
- Charge les 3 types d'audit depuis `audit_types.json`
- Caching en mémoire (global `_cache`, `_audit_types_cache`)
- Validation sur charger (lève exception si fichier corrompu)

**Fonctions clés:**
- `charger_cache()` → Retourne le cache RGAA complet (critères, glossaire, thèmes)
- `charger_audit_types()` → Retourne les 3 types d'audit (complet 106, rapide 25, complémentaire 25)

#### `files/_helpers.py` — Fonctions partagées de validation

Extractes en Phase 3 pour cohérence entre mcp-rgaa et greenit-mcp.

**Responsabilités:**
- Centralise la validation des paramètres pour éviter la duplication entre outils
- Retourne `ToolError` avec messages français exploitables

**Fonctions:**
- `validate_themes(themes)` → Valide les numéros de thème (1-13), lève ToolError sinon
- `validate_score_range(value, min_val, max_val, param_name)` → Valide les scores (0-100 ou 0-5)
- `validate_nonnegative(value, param_name)` → Valide les entiers positifs

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
- Endpoints HTTP GET pour accueil, santé, guide des outils
- HTML pour page d'accueil (avec status des données RGAA)
- JSON pour /guide (liste tous les outils et paramètres)
- Génération dynamique de contenu (version injectée par rgaa_mcp.py)

**Routes:**
- `GET /` → Page d'accueil HTML (status, liens, instructions)
- `GET /health` → Probe de santé JSON ({"status": "ok", "criteria_count": 106})
- `GET /guide` → Liste outils + paramètres (JSON ou HTML selon Content-Type)

#### `files/analyseur.py` — Analyse statique HTML

Analyse une URL et détecte violations RGAA basées sur analyse HTML statique.

**Responsabilités:**
- Récupère le HTML d'une URL via httpx
- Analyse le HTML avec BeautifulSoup pour 8 thèmes automatisables
- Détecte violations par critère (ex: images sans alt, iframes sans title)
- Retourne violations groupées par critère avec sélecteurs et suggestions

**Thèmes couverts:**
1. Images (1.1 — alt requis)
2. Cadres (2.1 — title requis)
5. Tableaux (5.1, 5.7 — structure requise)
6. Liens (6.1 — texte requis)
8. Code et langages (8.1 — validité HTML5)
9. Navigation (9.1, 9.2 — headings et skips requis)
11. Formulaires (11.1, 11.2 — labels requis)
12. Navigation au clavier (12.1 — order logique)

**Fonctions clés:**
- `fetcher_html(url)` → Récupère le HTML via httpx
- `analyser_html(html, themes)` → Analyse et retourne violations
- `_theme1(soup)`, `_theme2(soup)`, etc. → Analyseurs par thème

### Fichiers de données

#### `files/rgaa_cache.json`

Cache embarqué du référentiel RGAA 4.2.1.

**Structure:**
```json
{
  "criteres": {
    "1.1": {
      "id": "1.1",
      "theme": 1,
      "titre": "Chaque image a-t-elle une alternative textuelle ?",
      "tests": { "T1.1": "...", "T1.2": "..." },
      "wcag": ["4.1.2 (A)", "1.4.5 (AAA)"],
      "niveau": "A",
      "automatisable": true
    },
    ...
  },
  "glossaire": {
    "alternative textuelle": {
      "terme": "alternative textuelle",
      "definition": "...",
      "examples": [...] 
    },
    ...
  },
  "themes": {
    "1": "Images",
    "2": "Cadres",
    ...
    "13": "Consultation"
  }
}
```

#### `files/audit_types.json`

Définition des 3 types d'audit RGAA.

**Structure:**
```json
{
  "complet": {
    "nom": "Audit complet",
    "description": "106 critères — répond à l'obligation légale",
    "criteres": null,
    "conforme_obligation": true
  },
  "rapide": {
    "nom": "Audit rapide",
    "description": "25 critères essentiels",
    "criteres": ["1.1", "2.1", ...],
    "conforme_obligation": false
  },
  "complementaire": {
    "nom": "Audit complémentaire",
    "description": "25 critères supplémentaires",
    "criteres": ["1.2", "2.2", ...],
    "conforme_obligation": false
  }
}
```

#### `tokens/tokens.json`

Tokens générés à la demande (volume Docker, jamais dans l'image).

**Structure:**
```json
{
  "token_hash_1": {
    "name": "Alice",
    "created_at": "2026-01-01T00:00:00+00:00",
    "expires_at": 1735689600
  },
  ...
}
```

## Les 10 outils MCP

| Outil | Description | Annotations |
|-------|-------------|-------------|
| `rgaa_lister_criteres` | Liste critères avec filtres thème/WCAG | readonly, idempotent |
| `rgaa_obtenir_critere` | Récupère détails d'un critère par ID | readonly, idempotent |
| `rgaa_chercher` | Recherche critères par mot-clé | readonly, openworld, idempotent |
| `rgaa_glossaire` | Définitions du glossaire RGAA | readonly, idempotent |
| `rgaa_statistiques` | Statistiques globales (count, distribution) | readonly, idempotent |
| `rgaa_analyser` | Analyse URL pour violations (HTML statique) | readonly, openworld |
| `rgaa_checklist` | Génère checklist manuelle d'audit | readonly, idempotent |
| `rgaa_taux_conformite` | Calcule taux de conformité RGAA | readonly, idempotent |
| `rgaa_types_audit` | Liste des 3 types d'audit | readonly, idempotent |
| `rgaa_criteres_audit` | Critères pour un type d'audit donné | readonly, idempotent |

**Légende des annotations:**
- `readonly` = Aucun effet destructif (lecteur pur)
- `idempotent` = Résultats stables (pas d'état aléatoire, pas d'I/O côté serveur)
- `openworld` = Données dynamiques ou externes (URL utilisateur, contenu variable)

### Détails des outils

#### rgaa_lister_criteres(theme=None, niveau_wcag=None)
Liste les 106 critères avec filtres optionnels par thème (1-13) ou niveau WCAG (A, AA, AAA).

**Paramètres:**
- `theme` (int, optionnel) — Filtre sur un thème (1-13)
- `niveau_wcag` (str, optionnel) — Filtre sur un niveau WCAG (A, AA, AAA)

**Retour:**
```json
{
  "total": 106,
  "criteres": [
    {"id": "1.1", "theme": 1, "titre": "...", "automatisable": true, "niveau": "A"},
    ...
  ]
}
```

#### rgaa_obtenir_critere(id)
Récupère le détail complet d'un critère par ID (ex: "1.1").

**Paramètres:**
- `id` (str, requis) — Identifiant du critère (ex: "1.1", "13.13")

**Retour:** Critère complet avec tests, références WCAG, cas particuliers.

**Gestion des erreurs:**
- Critère inexistant → ToolError avec suggestion similaire (difflib)
- ID invalide → ToolError avec format attenda

#### rgaa_chercher(query, scope=None)
Recherche par mot-clé dans les critères et/ou le glossaire.

**Paramètres:**
- `query` (str, requis) — Terme à chercher
- `scope` (list[str], optionnel) — Périmètre: ["criteres", "glossaire"]. None = tous.

**Retour:**
```json
{
  "criteres": [{"id": "1.1", "theme": 1, "titre": "..."}],
  "termes_glossaire": [{"terme": "...", "definition": "...", "examples": [...]}]
}
```

#### rgaa_glossaire(terme)
Retourne la définition d'un terme du glossaire RGAA.

**Paramètres:**
- `terme` (str, requis) — Terme à chercher (insensible à la casse)

**Retour:** Définition avec exemples et suggestions si terme introuvable.

**Gestion des erreurs:**
- Terme inexistant → ToolError avec suggestion (sous-chaîne ou difflib)

#### rgaa_statistiques()
Retourne les statistiques du référentiel (counts, distribution par thème).

**Retour:**
```json
{
  "total_criteres": 106,
  "automatisables": 57,
  "manuels": 49,
  "par_theme": {
    "1": {"titre": "Images", "nb_criteres": 4, "automatisables": 2},
    ...
  }
}
```

#### rgaa_types_audit()
Liste les 3 types d'audit RGAA et indique lequel répond à l'obligation légale (complet).

**Retour:**
```json
{
  "types": [
    {
      "type": "complet",
      "nom": "Audit complet",
      "description": "106 critères — obligation légale",
      "conforme_obligation": true,
      "nb_criteres": 106
    },
    ...
  ]
}
```

#### rgaa_criteres_audit(type)
Retourne la liste des critères pour un type d'audit (complet, rapide, complémentaire).

**Paramètres:**
- `type` (str, requis) — Type d'audit: "complet", "rapide", "complementaire"

**Retour:**
```json
{
  "type": "complet",
  "nom": "Audit complet",
  "conforme_obligation": true,
  "nb_criteres": 106,
  "criteres": [{"id": "1.1", "theme": 1, "titre": "..."}]
}
```

#### rgaa_analyser(url, themes=None)
Analyse une page web pour détecter les violations RGAA automatisables.

**Paramètres:**
- `url` (str, requis) — URL de la page
- `themes` (list[int], optionnel) — Thèmes à analyser (1-13). None = tous les automatisables [1,2,5,6,8,9,11,12].

**Retour:**
```json
{
  "url": "https://example.com",
  "date": "2026-01-01T12:00:00+00:00",
  "themes_analyses": [1, 2, 5, 6, 8, 9, 11, 12],
  "nb_violations": 3,
  "criteres": [
    {
      "id": "1.1",
      "titre": "...",
      "statut": "NC",
      "violations": [
        {"selecteur": "img.logo", "html": "<img...>", "probleme": "alt manquant"}
      ]
    }
  ],
  "note": "Analyse statique uniquement. Utiliser Playwright MCP pour DOM rendu."
}
```

**Gestion des erreurs:**
- URL vide → ToolError
- URL invalide (pas http://) → ToolError
- URL inaccessible → ToolError avec détails de l'erreur HTTP

#### rgaa_checklist(themes=None, criteres=None)
Génère une checklist manuelle d'audit RGAA.

**Paramètres:**
- `themes` (list[int], optionnel) — Thèmes (ex: [1, 6, 11])
- `criteres` (list[str], optionnel) — Critères (ex: ["1.1", "6.1"])
- Au moins un paramètre requis.

**Retour:**
```json
{
  "criteres": [
    {
      "id": "1.1",
      "titre": "Chaque image a-t-elle une alternative textuelle ?",
      "tests": [
        {
          "description": "Vérifier que chaque <img> a un attribut alt",
          "methode": "Inspecter le HTML avec DevTools",
          "outils": ["DevTools (onglet Éléments)", "Web Developer Toolbar", "NVDA + Firefox"]
        }
      ]
    }
  ]
}
```

#### rgaa_taux_conformite(resultats)
Calcule le taux de conformité RGAA selon la formule officielle: C / (C + NC) × 100

**Paramètres:**
- `resultats` (dict, requis) — Dictionnaire {id_critere: statut} avec statuts "C", "NC", "NA"

**Retour:**
```json
{
  "total_criteres": 106,
  "conformes": 98,
  "non_conformes": 8,
  "non_applicables": 0,
  "taux_conformite": 92.45,
  "taux_formaté": "92,45%"
}
```

## Gestion des erreurs

### Niveaux d'erreur

1. **ToolError (erreurs utilisateur)**
   - Paramètres invalides (ex: theme > 13)
   - Format JSON mal formé
   - IDs invalides ou manquants
   - Message français exploitable avec suggestions
   - Exemple: `"Thème invalide. Doit être un entier entre 1 et 13."`

2. **Erreurs système**
   - Fichiers JSON corrompus ou manquants
   - I/O système
   - Loggées en ERROR, retour générique au client
   - FastMCP retourne erreur 500

3. **Erreurs réseau** (rgaa_analyser)
   - URL invalide ou inaccessible
   - Timeout (30s)
   - Retour JSON: `{"error": "URL inaccessible: <reason>"}`

### Pattern TDD

Chaque outil a:
- Tests positifs (entrées valides → résultats corrects)
- Tests négatifs (paramètres invalides → ToolError avec message français)
- Tests d'intégration (appels multiples, interaction avec données)

## Tests

**Suite complète:** 227 tests passant

| Fichier | Tests | Couverture |
|---------|-------|-----------|
| `tests/test_tools.py` | 134 tests | Tous les 10 outils + paramètres + erreurs |
| `tests/test_analyseur.py` | 38 tests | HTML analysis + violations detection |
| `tests/test_conformite.py` | 42 tests | Compliance rate computation + edge cases |
| `tests/test_referentiel.py` | 13 tests | Criteria loading + data integrity |

**Exécution:**
```bash
# Tous les tests
python -m pytest tests/ -v

# Outil spécifique
python -m pytest tests/ -k "rgaa_lister"

# Avec couverture
python -m pytest tests/ --cov=files --cov-report=html
```

**Exemple de test:**
```python
def test_rgaa_lister_criteres_valid_theme():
    """Test listing criteria by valid theme."""
    result = rgaa_lister_criteres(theme=1)
    assert result["total"] > 0
    assert all(c["theme"] == 1 for c in result["criteres"])

def test_rgaa_lister_criteres_invalid_theme():
    """Test listing criteria with invalid theme raises ToolError."""
    with pytest.raises(ToolError):
        rgaa_lister_criteres(theme=99)
```

## Déploiement

### Modes de transport

#### Mode stdio (local)

Terminal ou IDE avec FastMCP connecté.

```bash
# Lancer le serveur
python files/rgaa_mcp.py

# Avec logging
LOG_LEVEL=DEBUG python files/rgaa_mcp.py
```

Variables d'environnement:
- `LOG_LEVEL` — Python logging level (DEBUG, INFO, WARNING, ERROR)

#### Mode HTTP (docker-compose)

Serveur HTTP derrière reverse proxy avec authentification Bearer.

```yaml
services:
  rgaa-mcp:
    build: .
    ports:
      - "8001:8000"
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
| `MCP_PORT` | `8000` | Port interne (exposé en 8001 via docker-compose) |
| `MCP_BASE_URL` | auto | URL publique si derrière un reverse proxy |
| `MCP_TOKEN_REQUEST_URL` | vide | URL formulaire demande de token |
| `LOG_LEVEL` | `INFO` | Python logging level (DEBUG, INFO, WARNING, ERROR) |

### Authentification Bearer

Si `MCP_TRANSPORT=http`, les outils requièrent un Bearer token.

**Générer un token:**
```bash
# Dans le conteneur Docker
docker run --rm -v $(pwd)/tokens:/app/tokens rgaa-mcp --generate-token --name "Alice" --expires-days 365
# Output: Token généré pour 'Alice' (expire dans 365 jours):
#         abc123def456...

# Ou en local
python files/rgaa_mcp.py --generate-token --name "Alice"
```

**Utiliser le token:**
```bash
curl -H "Authorization: Bearer abc123def456..." http://localhost:8001/guide
```

**Lister les tokens:**
```bash
docker run --rm -v $(pwd)/tokens:/app/tokens rgaa-mcp --list-tokens
# Output:   abc123def456...  Alice  [actif]
#           xyz789qrs012...  Bob    [EXPIRÉ]
```

**Révoquer un token:**
```bash
docker run --rm -v $(pwd)/tokens:/app/tokens rgaa-mcp --revoke-token abc123def456...
```

## Architecture parity avec greenit-mcp

Phase 3 a aligné les deux services MCP pour cohérence et maintenabilité.

### Structure commune

Ambos services partagent:
- `data.py` — Chargement cache + accès données
- `auth.py` — Gestion tokens Bearer
- `routes.py` — Endpoints HTTP (/, /health, /guide)
- `_helpers.py` — Validation centralisée
- `rgaa_mcp.py` / `greenit_mcp.py` — Serveur principal
- Tests complets avec pytest
- Docker et docker-compose
- Documentation identique (README.md, ARCHITECTURE.md)

### Patterns unifiés

1. **Validation centralisée** — `_helpers.py` pour éviter duplication
2. **Gestion des erreurs** — ToolError avec messages français
3. **Annotations MCP** — readonly, idempotent, openWorldHint cohérents
4. **Tokens Bearer** — auth.py et StaticTokenVerifier partagés
5. **Routes HTTP** — /health, /guide templates
6. **Tests** — test_tools.py, test_referentiel.py, test_integration_annotations.py

### Différences intentionnelles

| Aspect | mcp-rgaa | greenit-mcp |
|--------|----------|-------------|
| **Outils** | 10 (consultation + analyse) | 9 (recherche + comparaison) |
| **Données** | 106 critères RGAA | 119 fiches GreenIT |
| **Analyseur** | HTML statique (8 thèmes) | EcoIndex scores |
| **Types d'audit** | 3 types (complet, rapide, complémentaire) | N/A |

### Maintenance

Quand une amélioration est faite dans un service:
1. Implémenter dans le premier service
2. Tester avec pytest
3. Appliquer au second service
4. Synchroniser documentation et tests

Exemples:
- Nouveau pattern d'erreur → Mettre à jour _helpers.py dans les deux
- Nouvelle dépendance → Mettre à jour pyproject.toml et requirements.txt
- Changement API FastMCP → Sync rgaa_mcp.py et greenit_mcp.py

## Fichiers clés

- `/Users/renaudheluin/DEV/mcp-rgaa/files/rgaa_mcp.py` — Serveur FastMCP, 10 outils
- `/Users/renaudheluin/DEV/mcp-rgaa/files/data.py` — Cache RGAA et API lecture
- `/Users/renaudheluin/DEV/mcp-rgaa/files/auth.py` — Gestion tokens Bearer
- `/Users/renaudheluin/DEV/mcp-rgaa/files/routes.py` — Endpoints HTTP
- `/Users/renaudheluin/DEV/mcp-rgaa/files/analyseur.py` — Analyse HTML (8 thèmes)
- `/Users/renaudheluin/DEV/mcp-rgaa/files/_helpers.py` — Validation centralisée
- `/Users/renaudheluin/DEV/mcp-rgaa/files/rgaa_cache.json` — 106 critères RGAA embarqués
- `/Users/renaudheluin/DEV/mcp-rgaa/files/audit_types.json` — 3 types d'audit
- `/Users/renaudheluin/DEV/mcp-rgaa/tests/` — 227 tests (6 fichiers)
