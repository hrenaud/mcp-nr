# GreenIT MCP API Reference

Documentation complète des 9 outils MCP du serveur GreenIT 2.4.1.

**Table des matières:**
1. [lister_fiches](#lister_fiches)
2. [fiches_prioritaires](#fiches_prioritaires)
3. [chercher_fiche](#chercher_fiche)
4. [comparer_fiches](#comparer_fiches)
5. [obtenir_fiche_complete](#obtenir_fiche_complete)
6. [obtenir_statistiques](#obtenir_statistiques)
7. [lister_lifecycles](#lister_lifecycles)
8. [lister_ressources](#lister_ressources)
9. [calculer_ecoindex](#calculer_ecoindex)

---

## lister_fiches

Liste les fiches du référentiel GreenIT avec filtres optionnels par lifecycle, ressource économisée, et seuils d'impact/priorité.

**Paramètres:**
- `lifecycle` (string, optional): Phase du cycle de vie (ex: "3-developement", "2-conception"). Défaut: None (tous)
- `saved_resource` (string, optional): Ressource économisée (ex: "network", "cpu", "requests"). Défaut: None (toutes)
- `impact_min` (integer, optional): Impact environnemental minimum (1-5). Défaut: None
- `priorite_min` (integer, optional): Priorité d'implémentation minimum (1-5). Défaut: None

**Retour:**
```json
{
  "total": 175,
  "fiches": [
    {
      "id": "RWEB_0049",
      "titre": "Minifier les ressources CSS, JavaScript et SVG",
      "impact": 5,
      "priorite": 5,
      "lifecycle": "3-developement",
      "saved_resources": ["network", "requests"],
      "description_courte": "Réduire la taille des ressources..."
    }
  ]
}
```

**Annotations:**
- `readOnlyHint`: true (lecture seule)
- `destructiveHint`: false (non-destructif)
- `idempotentHint`: true (idempotent)
- `openWorldHint`: false (monde fermé)

**Exemples:**
```
# Lister toutes les fiches
lister_fiches()

# Filtrer par lifecycle "developement"
lister_fiches(lifecycle="3-developement")

# Fiches à fort impact réseau
lister_fiches(saved_resource="network", impact_min=4)

# Combiner les filtres
lister_fiches(lifecycle="2-conception", impact_min=4, priorite_min=4)
```

---

## fiches_prioritaires

Retourne les fiches à fort impact et haute priorité d'implémentation, avec seuils configurables.

**Paramètres:**
- `impact_min` (integer, optional): Impact minimum (1-5). Défaut: 4
- `priorite_min` (integer, optional): Priorité minimum (1-5). Défaut: 4

**Retour:**
```json
{
  "total": 28,
  "fiches": [
    {
      "id": "RWEB_0049",
      "titre": "Minifier les ressources CSS, JavaScript et SVG",
      "impact": 5,
      "priorite": 5,
      "score_combine": 25,
      "raison": "Impact maximal + Implémentation facile"
    }
  ]
}
```

**Annotations:**
- `readOnlyHint`: true
- `destructiveHint`: false
- `idempotentHint`: true
- `openWorldHint`: false

**Exemples:**
```
# Fiches prioritaires (defaults: impact_min=4, priorite_min=4)
fiches_prioritaires()

# Impact 5 uniquement
fiches_prioritaires(impact_min=5)

# Seuils plus bas (impact 3+)
fiches_prioritaires(impact_min=3, priorite_min=3)
```

---

## chercher_fiche

Recherche des fiches par mot-clé avec scoring par pertinence dans titres, descriptions et tags.

**Paramètres:**
- `terme` (string, required): Mot-clé à rechercher

**Retour:**
```json
{
  "resultats": [
    {
      "id": "RWEB_0049",
      "titre": "Minifier les ressources CSS, JavaScript et SVG",
      "score": 95,
      "motif": "Correspondance: 'minifier' dans le titre",
      "impact": 5
    }
  ],
  "total": 6
}
```

**Annotations:**
- `readOnlyHint`: true
- `destructiveHint`: false
- `idempotentHint`: true
- `openWorldHint`: true (peut retourner des résultats inattendus)

**Exemples:**
```
# Rechercher "minifier"
chercher_fiche(terme="minifier")

# Rechercher "image"
chercher_fiche(terme="image")

# Rechercher "cache"
chercher_fiche(terme="cache")
```

---

## comparer_fiches

Compare plusieurs fiches côte à côte avec scores, lifecycle, ressources économisées et recommandation.

**Paramètres:**
- `fiche_ids` (array of string, required): Liste d'identifiants de fiches (ex: ["RWEB_0049", "RWEB_0051"])

**Retour:**
```json
{
  "comparaison": [
    {
      "id": "RWEB_0049",
      "titre": "Minifier les ressources...",
      "impact": 5,
      "priorite": 5,
      "lifecycle": "3-developement",
      "saved_resources": ["network", "requests"]
    },
    {
      "id": "RWEB_0051",
      "titre": "Compresser les images...",
      "impact": 5,
      "priorite": 4,
      "lifecycle": "3-developement",
      "saved_resources": ["network"]
    }
  ],
  "recommandation": "RWEB_0049 à implémenter en priorité (impact maximal, moins complexe)"
}
```

**Annotations:**
- `readOnlyHint`: true
- `destructiveHint`: false
- `idempotentHint`: true
- `openWorldHint`: false

**Exemples:**
```
# Comparer deux fiches
comparer_fiches(fiche_ids=["RWEB_0049", "RWEB_0051"])

# Comparer plusieurs fiches
comparer_fiches(fiche_ids=["RWEB_0049", "RWEB_0051", "RWEB_0052"])
```

---

## obtenir_fiche_complete

Retourne le détail complet d'une fiche avec principes de validation, tests et exemples.

**Paramètres:**
- `fiche_id` (string, required): Identifiant de la fiche (ex: "RWEB_0049")

**Retour:**
```json
{
  "id": "RWEB_0049",
  "titre": "Minifier les ressources CSS, JavaScript et SVG",
  "description": "La minification supprime les caractères inutiles...",
  "impact": 5,
  "priorite": 5,
  "lifecycle": "3-developement",
  "saved_resources": ["network", "requests"],
  "principes_validation": [
    "Vérifier que les fichiers .css sont minifiés",
    "Vérifier que les fichiers .js sont minifiés"
  ],
  "exemples": {
    "avant": "body { color: red; margin: 0; }",
    "apres": "body{color:red;margin:0}"
  },
  "références": ["https://greenit.fr/..."]
}
```

**Annotations:**
- `readOnlyHint`: true
- `destructiveHint`: false
- `idempotentHint`: true
- `openWorldHint`: false

**Exemples:**
```
# Obtenir le détail complet
obtenir_fiche_complete(fiche_id="RWEB_0049")

# Obtenir une autre fiche
obtenir_fiche_complete(fiche_id="RWEB_0051")
```

---

## obtenir_statistiques

Retourne les statistiques avancées du référentiel avec distribution par lifecycle et ressource, et top 5 fiches.

**Paramètres:**
(aucun)

**Retour:**
```json
{
  "total_fiches": 175,
  "par_lifecycle": {
    "1-expression-du-besoin": 15,
    "2-conception": 32,
    "3-developement": 48,
    "4-optimisation": 35,
    "5-hebergement": 28,
    "6-deploiement": 12,
    "7-utilisation": 5
  },
  "par_ressource": {
    "network": 42,
    "cpu": 38,
    "requests": 35,
    "memory": 28,
    "storage": 22,
    "database": 15,
    "rendering": 12,
    "javascript": 10
  },
  "top_5_fiches": [
    {
      "id": "RWEB_0049",
      "titre": "Minifier les ressources...",
      "score_combine": 25
    }
  ]
}
```

**Annotations:**
- `readOnlyHint`: true
- `destructiveHint`: false
- `idempotentHint`: true
- `openWorldHint`: false

**Exemples:**
```
# Obtenir les statistiques
obtenir_statistiques()
```

---

## lister_lifecycles

Liste les 7 phases du cycle de vie du référentiel GreenIT avec comptages de fiches.

**Paramètres:**
(aucun)

**Retour:**
```json
{
  "lifecycles": [
    {
      "id": "1-expression-du-besoin",
      "label": "Expression du besoin",
      "count": 15
    },
    {
      "id": "2-conception",
      "label": "Conception",
      "count": 32
    },
    {
      "id": "3-developement",
      "label": "Développement",
      "count": 48
    },
    {
      "id": "4-optimisation",
      "label": "Optimisation",
      "count": 35
    },
    {
      "id": "5-hebergement",
      "label": "Hébergement",
      "count": 28
    },
    {
      "id": "6-deploiement",
      "label": "Déploiement",
      "count": 12
    },
    {
      "id": "7-utilisation",
      "label": "Utilisation",
      "count": 5
    }
  ]
}
```

**Annotations:**
- `readOnlyHint`: true
- `destructiveHint`: false
- `idempotentHint`: true
- `openWorldHint`: false

**Exemples:**
```
# Lister tous les lifecycles
lister_lifecycles()
```

---

## lister_ressources

Liste les 8 types de ressources sauvegardées du référentiel GreenIT avec comptages.

**Paramètres:**
(aucun)

**Retour:**
```json
{
  "ressources": [
    {
      "id": "network",
      "label": "Réseau",
      "count": 42
    },
    {
      "id": "cpu",
      "label": "CPU",
      "count": 38
    },
    {
      "id": "requests",
      "label": "Requêtes HTTP",
      "count": 35
    },
    {
      "id": "memory",
      "label": "Mémoire",
      "count": 28
    },
    {
      "id": "storage",
      "label": "Stockage",
      "count": 22
    },
    {
      "id": "database",
      "label": "Base de données",
      "count": 15
    },
    {
      "id": "rendering",
      "label": "Rendu",
      "count": 12
    },
    {
      "id": "javascript",
      "label": "JavaScript",
      "count": 10
    }
  ]
}
```

**Annotations:**
- `readOnlyHint`: true
- `destructiveHint`: false
- `idempotentHint`: true
- `openWorldHint`: false

**Exemples:**
```
# Lister toutes les ressources
lister_ressources()
```

---

## calculer_ecoindex

Calcule l'EcoIndex à partir des 3 métriques brutes mesurées par Playwright avec score (0-100) et grade (A-G).

**Paramètres:**
- `dom_nodes` (integer, required): Nombre de nœuds dans le DOM
- `requests` (integer, required): Nombre de requêtes HTTP
- `size_kb` (number, required): Taille totale transférée en kilo-octets
- `url` (string, optional): URL de la page mesurée (pour contexte)

**Retour:**
```json
{
  "url": "https://example.com",
  "metriques": {
    "dom_nodes": 2456,
    "requests": 84,
    "size_kb": 2187.5
  },
  "ecoindex": {
    "score": 42,
    "grade": "D",
    "percentile": 35
  },
  "analyse": "Score faible. Réduire le nombre de requêtes et la taille des ressources.",
  "recommandations": [
    "Combiner les fichiers CSS/JS",
    "Compresser les images",
    "Activer le cache navigateur"
  ]
}
```

**Annotations:**
- `readOnlyHint`: true
- `destructiveHint`: false
- `idempotentHint`: false (résultat peut varier selon l'état de la page)
- `openWorldHint`: true (accès externe pour contexte URL)

**Protocole de mesure recommandé avec Playwright:**
1. Ouvrir un contexte avec viewport 1920x1080 (spec EcoIndex officielle)
2. Naviguer vers la page
3. Attendre 3 secondes
4. Faire défiler jusqu'en bas progressivement
5. Attendre 3 secondes
6. Mesurer : nœuds DOM, requêtes HTTP, taille totale en Ko
7. Appeler cet outil avec les 3 métriques

**Exemples:**
```
# Calculer l'EcoIndex
calculer_ecoindex(dom_nodes=2456, requests=84, size_kb=2187.5)

# Avec contexte URL
calculer_ecoindex(
  dom_nodes=2456,
  requests=84,
  size_kb=2187.5,
  url="https://example.com"
)

# Résultat: Score 42/100 (grade D) avec recommandations
```

---

## Format des réponses

Toutes les réponses sont structurées en JSON avec:
- **Succès (200):** Objet JSON avec les données demandées
- **Erreur (4xx/5xx):** Objet JSON avec message d'erreur et suggestions

### Exemple de réponse d'erreur:
```json
{
  "error": "Fiche 'RWEB_9999' non trouvée",
  "suggestions": [
    "Vérifier l'ID de la fiche",
    "Utiliser lister_fiches() pour voir toutes les fiches"
  ]
}
```

---

## Authentification

Pour utiliser les endpoints HTTP (mode `MCP_TRANSPORT=http`):

1. Générer un token:
   ```bash
   docker run --rm -v $(pwd)/tokens:/app/tokens greenit-mcp \
     --generate-token --name "Mon app"
   ```

2. Utiliser le token en header:
   ```bash
   curl -H "Authorization: Bearer <token>" \
     http://localhost:8000/api/tools/lister_fiches
   ```

---

## API Admin — Gestion des tokens

> Mode HTTP uniquement. Requiert `ADMIN_TOKEN` dans les variables d'environnement.

**Codes d'erreur communs à tous les endpoints :**

| Condition | Status | Corps |
|-----------|--------|-------|
| `ADMIN_TOKEN` non configuré | 503 | `{"error": "Admin API disabled"}` |
| Auth absente ou incorrecte | 401 | `{"error": "Unauthorized"}` |
| Token introuvable | 404 | `{"error": "Token not found"}` |
| Corps de requête invalide | 400 | `{"error": "<détail>"}` |

### GET /admin/tokens

Liste tous les tokens enregistrés.

**Auth :** `Authorization: Bearer <ADMIN_TOKEN>`

```bash
curl -H "Authorization: Bearer $ADMIN_TOKEN" http://localhost:8000/admin/tokens
```

**Réponse 200 :**
```json
[
  {
    "id": "4accdde2",
    "name": "Alice",
    "created_at": "2026-05-01T10:00:00+00:00",
    "expires_at": 1780000000,
    "updated_at": "2026-05-01T10:00:00+00:00",
    "status": "active"
  }
]
```

### POST /admin/tokens

Crée un nouveau token Bearer.

**Auth :** `Authorization: Bearer <ADMIN_TOKEN>`

```bash
curl -X POST \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "Alice", "expires_days": 365}' \
  http://localhost:8000/admin/tokens
```

**Corps de la requête :**
| Champ | Type | Requis | Description |
|-------|------|--------|-------------|
| `name` | string | oui | Nom du client |
| `expires_days` | int | non | Durée de validité en jours (défaut : 365) |

**Réponse 201 :**
```json
{
  "token": "<valeur>",
  "id": "4accdde2",
  "name": "Alice",
  "expires_at": 1780000000,
  "created_at": "2026-05-01T10:00:00+00:00"
}
```

> Le champ `token` n'est retourné qu'à la création. À stocker immédiatement.

### GET /admin/tokens/{id}

Récupère les détails d'un token par son identifiant.

**Auth :** `Authorization: Bearer <ADMIN_TOKEN>`

**Réponse 200** : même structure qu'une entrée de `GET /admin/tokens`.

### PATCH /admin/tokens/{id}

Met à jour le nom ou la durée de validité d'un token.

**Auth :** `Authorization: Bearer <ADMIN_TOKEN>`

```bash
curl -X PATCH \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "Bob", "expires_days": 30}' \
  http://localhost:8000/admin/tokens/4accdde2
```

| Champ | Type | Requis | Description |
|-------|------|--------|-------------|
| `name` | string | non | Nouveau nom |
| `expires_days` | int | non | Nouvelle expiration à partir de maintenant |

**Réponse 200** : token mis à jour (même structure que GET par id).

### DELETE /admin/tokens/{id}

Révoque un token (suppression définitive).

**Auth :** `Authorization: Bearer <ADMIN_TOKEN>`

**Réponse 204** : corps vide.

---

## Notes sur les performances

- **Requêtes en cache:** Les données GreenIT sont chargées en mémoire au démarrage
- **Calculateur EcoIndex:** L'analyse peut prendre 5-10 secondes selon la complexité
- **Rate limiting:** Mode HTTP supporte ~100 req/s par défaut
- **Timeout:** Analyser une page avec délai > 30s retourne une erreur

---

## Versioning

API version: 1.0.0 (correspond à `greenit-mcp v2.4.1`)

Dernière mise à jour: 2026-04-26
