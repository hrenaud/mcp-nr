# RGAA MCP API Reference

Documentation complète des 10 outils MCP du serveur RGAA 4.2.1.

**Table des matières:**
1. [rgaa_lister_criteres](#rgaa_lister_criteres)
2. [rgaa_obtenir_critere](#rgaa_obtenir_critere)
3. [rgaa_chercher](#rgaa_chercher)
4. [rgaa_glossaire](#rgaa_glossaire)
5. [rgaa_statistiques](#rgaa_statistiques)
6. [rgaa_types_audit](#rgaa_types_audit)
7. [rgaa_criteres_audit](#rgaa_criteres_audit)
8. [rgaa_analyser](#rgaa_analyser)
9. [rgaa_checklist](#rgaa_checklist)
10. [rgaa_taux_conformite](#rgaa_taux_conformite)

---

## rgaa_lister_criteres

Liste les critères RGAA avec filtres optionnels par thème et/ou niveau WCAG.

**Paramètres:**
- `theme` (integer, optional): Numéro de thème (1-13). Défaut: None (tous les thèmes)
- `niveau_wcag` (string, optional): Niveau WCAG à filtrer (A, AA, AAA). Défaut: None (tous les niveaux)

**Retour:**
```json
{
  "total": 106,
  "criteres": [
    {
      "id": "1.1",
      "theme": 1,
      "titre": "Alternatives textuelles",
      "automatisable": true,
      "niveau": "A"
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
# Lister tous les critères
rgaa_lister_criteres()

# Filtrer par thème 5 (Éléments nécessaires)
rgaa_lister_criteres(theme=5)

# Filtrer par niveau WCAG AA
rgaa_lister_criteres(niveau_wcag="AA")

# Combiner les filtres
rgaa_lister_criteres(theme=3, niveau_wcag="AAA")
```

---

## rgaa_obtenir_critere

Retourne le détail complet d'un critère RGAA avec ses tests et références WCAG.

**Paramètres:**
- `id` (string, required): Identifiant du critère (ex: "1.1", "11.3")

**Retour:**
```json
{
  "id": "1.1",
  "theme": 1,
  "titre": "Alternatives textuelles des images",
  "tests": {
    "M1": "L'image est-elle un élément <img> ?",
    "M2": "L'image a-t-elle un attribut alt ?"
  },
  "wcag": [
    "WCAG21:1.1.1 (A)"
  ],
  "cas_particuliers": "Les images décoratives doivent avoir un alt vide.",
  "niveau": "A",
  "automatisable": true
}
```

**Annotations:**
- `readOnlyHint`: true
- `destructiveHint`: false
- `idempotentHint`: true
- `openWorldHint`: false

**Exemples:**
```
# Obtenir le détail du critère 1.1
rgaa_obtenir_critere(id="1.1")

# Obtenir les détails du critère 11.3
rgaa_obtenir_critere(id="11.3")
```

---

## rgaa_chercher

Recherche des critères par mot-clé dans les titres, descriptions et tags avec scoring par pertinence.

**Paramètres:**
- `terme` (string, required): Mot-clé à rechercher

**Retour:**
```json
{
  "resultats": [
    {
      "id": "1.1",
      "theme": 1,
      "titre": "Alternatives textuelles des images",
      "score": 95,
      "motif": "Correspondance: 'image' dans le titre"
    }
  ],
  "total": 5
}
```

**Annotations:**
- `readOnlyHint`: true
- `destructiveHint`: false
- `idempotentHint`: true
- `openWorldHint`: true (peut retourner des résultats inattendus)

**Exemples:**
```
# Rechercher "image"
rgaa_chercher(terme="image")

# Rechercher "formulaire"
rgaa_chercher(terme="formulaire")

# Rechercher "contraste"
rgaa_chercher(terme="contraste")
```

---

## rgaa_glossaire

Retourne la définition d'un terme du glossaire RGAA.

**Paramètres:**
- `terme` (string, required): Terme à rechercher (insensible à la casse)

**Retour:**
```json
{
  "terme": "Alternative textuelle",
  "definition": "Contenu textuel équivalent à l'image qui permet...",
  "references": [
    "WCAG21:1.1.1",
    "Critère 1.1"
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
# Rechercher une définition
rgaa_glossaire(terme="Alternative textuelle")

# Termes insensibles à la casse
rgaa_glossaire(terme="CONTEXTE ADJACENT")
```

---

## rgaa_statistiques

Retourne les statistiques du référentiel RGAA.

**Paramètres:**
(aucun)

**Retour:**
```json
{
  "total_criteres": 106,
  "par_theme": {
    "1": 11,
    "2": 8,
    "3": 7,
    "4": 13,
    "5": 6,
    "6": 7,
    "7": 9,
    "8": 4,
    "9": 7,
    "10": 10,
    "11": 11,
    "12": 9,
    "13": 8
  },
  "automatisables": 58,
  "manuels": 48,
  "par_niveau_wcag": {
    "A": 65,
    "AA": 32,
    "AAA": 9
  }
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
rgaa_statistiques()
```

---

## rgaa_types_audit

Liste les types d'audit RGAA disponibles et indique lequel répond à l'obligation légale.

**Paramètres:**
(aucun)

**Retour:**
```json
{
  "types": [
    {
      "type": "complet",
      "nom": "Audit complet",
      "description": "Évalue les 106 critères",
      "conforme_obligation": true,
      "nb_criteres": 106
    },
    {
      "type": "rapide",
      "nom": "Audit rapide",
      "description": "Évalue 25 critères prioritaires",
      "conforme_obligation": false,
      "nb_criteres": 25
    },
    {
      "type": "complementaire",
      "nom": "Audit complémentaire",
      "description": "Évalue 25 critères supplémentaires",
      "conforme_obligation": false,
      "nb_criteres": 25
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
# Lister les types d'audit
rgaa_types_audit()
```

---

## rgaa_criteres_audit

Retourne la liste des critères pour un type d'audit donné.

**Paramètres:**
- `type` (string, required): Type d'audit ("complet", "rapide", "complementaire")

**Retour:**
```json
{
  "type": "rapide",
  "description": "Audit rapide - 25 critères prioritaires",
  "total": 25,
  "criteres": [
    {
      "id": "1.1",
      "theme": 1,
      "titre": "Alternatives textuelles",
      "niveau": "A"
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
# Audit complet (106 critères - obligation légale)
rgaa_criteres_audit(type="complet")

# Audit rapide (25 critères prioritaires)
rgaa_criteres_audit(type="rapide")

# Audit complémentaire (25 critères supplémentaires)
rgaa_criteres_audit(type="complementaire")
```

---

## rgaa_analyser

Analyse une page HTML (via URL) pour détecter les violations RGAA automatisables.

**Paramètres:**
- `url` (string, required): URL de la page à analyser
- `themes` (array of integer, optional): Liste de thèmes à cibler (1-13). Défaut: [1,2,5,6,8,9,11,12] (automatisables)

**Retour:**
```json
{
  "url": "https://example.com",
  "violations": [
    {
      "theme": 1,
      "critere": "1.1",
      "titre": "Alternatives textuelles",
      "element": "<img src='logo.png'>",
      "probleme": "Image sans attribut alt",
      "severite": "élevée"
    }
  ],
  "total_violations": 3,
  "conformite_potentielle": "65%"
}
```

**Annotations:**
- `readOnlyHint`: true
- `destructiveHint`: false
- `idempotentHint`: false (résultat peut varier selon l'état de la page)
- `openWorldHint`: true (accès externe)

**Exemples:**
```
# Analyser une page
rgaa_analyser(url="https://example.com")

# Analyser des thèmes spécifiques
rgaa_analyser(url="https://example.com", themes=[1, 2, 5])
```

---

## rgaa_checklist

Génère une checklist de test manuel RGAA basée sur des critères ou thèmes.

**Paramètres:**
- `themes` (array of integer, optional): Liste de thèmes (ex: [1, 6, 11])
- `criteres` (array of string, optional): Liste d'identifiants de critères (ex: ["1.1", "6.1"])

**Retour:**
```json
{
  "checklist": [
    {
      "critere": "1.1",
      "titre": "Alternatives textuelles",
      "tests": [
        "[ ] Vérifier que chaque image a un attribut alt",
        "[ ] Vérifier que le texte de l'alt est pertinent"
      ]
    }
  ],
  "total_items": 15
}
```

**Annotations:**
- `readOnlyHint`: true
- `destructiveHint`: false
- `idempotentHint`: true
- `openWorldHint`: false

**Exemples:**
```
# Checklist pour le thème 1
rgaa_checklist(themes=[1])

# Checklist pour des critères spécifiques
rgaa_checklist(criteres=["1.1", "1.2", "1.3"])

# Checklist pour plusieurs thèmes
rgaa_checklist(themes=[1, 3, 5])
```

---

## rgaa_taux_conformite

Calcule le taux de conformité RGAA selon la formule officielle.

**Paramètres:**
- `resultats` (object, required): Dict {id_critere: statut} avec statuts "C" (conforme), "NC" (non-conforme), ou "NA" (non-applicable)

**Retour:**
```json
{
  "taux": 75.5,
  "conformes": 45,
  "non_conformes": 15,
  "non_applicables": 5,
  "total_evalues": 60,
  "statut": "Partiellement conforme",
  "recommandations": [
    "Prioriser les critères en NC avec severité élevée"
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
# Calculer le taux de conformité
rgaa_taux_conformite(resultats={
  "1.1": "C",
  "1.2": "NC",
  "1.3": "NA",
  "2.1": "C",
  "2.2": "NC"
})

# Résultat: 66.7% (2 conformes, 2 non-conformes, 1 non-applicable)
```

---

## Format des réponses

Toutes les réponses sont structurées en JSON avec:
- **Succès (200):** Objet JSON avec les données demandées
- **Erreur (4xx/5xx):** Objet JSON avec message d'erreur et suggestions

### Exemple de réponse d'erreur:
```json
{
  "error": "Critère '99.99' non trouvé",
  "suggestions": [
    "Vérifier l'ID du critère (format: X.Y)",
    "Utiliser rgaa_lister_criteres() pour voir tous les critères"
  ]
}
```

---

## Authentification

Pour utiliser les endpoints HTTP (mode `MCP_TRANSPORT=http`):

1. Générer un token:
   ```bash
   docker run --rm -v $(pwd)/tokens:/app/tokens rgaa-mcp \
     --generate-token --name "Mon app"
   ```

2. Utiliser le token en header:
   ```bash
   curl -H "Authorization: Bearer <token>" \
     http://localhost:8001/api/tools/rgaa_lister_criteres
   ```

---

## Notes sur les performances

- **Requêtes en cache:** Les données RGAA sont chargées en mémoire au démarrage
- **Analyseur HTML:** L'analyse de pages peut prendre 5-10 secondes selon la taille
- **Rate limiting:** Mode HTTP supporte ~100 req/s par défaut
- **Timeout:** Analyser une page avec délai > 30s retourne une erreur

---

## Versioning

API version: 1.0.0 (correspond à `mcp-rgaa v1.0.0`)

Dernière mise à jour: 2026-04-26
