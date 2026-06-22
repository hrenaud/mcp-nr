# Guide développeur — RGAA MCP

Le MCP RGAA connecte Claude au référentiel RGAA 4.2.1 (106 critères). Explorez les critères, recherchez des recommandations adaptées à votre contexte, et analysez statiquement du HTML selon le référentiel officiel.

---

## Outils disponibles

### Parcourir le référentiel

**`rgaa_lister_criteres`** — Liste tous les critères, filtrables par thème ou niveau WCAG. Sans filtre, retourne les 106 critères. Pour le détail d'un critère, utilisez `rgaa_obtenir_critere`.

```
"Liste tous les critères RGAA du thème Images"
"Quels critères RGAA sont de niveau A ?"
"Liste les critères du thème Formulaires"
```

**`rgaa_obtenir_critere`** — Contenu complet d'un critère : description, tests, conditions, références WCAG.

```
"Donne-moi le détail complet du critère 1.1"
"Explique le critère 11.1 et comment le tester manuellement"
"Quels sont les tests associés au critère 4.1 ?"
```

**`rgaa_chercher`** — Recherche par mot-clé dans les critères et le glossaire avec scoring de pertinence (titre, description, tests, références).

```
"Cherche les critères sur les alternatives textuelles"
"Trouve les recommandations liées aux contrastes de couleur"
"Recherche 'aria-label' dans le glossaire RGAA"
```

**`rgaa_glossaire`** — Définition d'un terme du glossaire RGAA avec correspondance approchante.

```
"Qu'est-ce que la 'restitution' dans le glossaire RGAA ?"
"Définis le terme 'élément porteur de rôle landmark'"
"Que signifie 'intitulé accessible' ?"
```

**`rgaa_statistiques`** — Distributions détaillées par thème et par niveau WCAG, avec nombre de tests par critère.

```
"Donne-moi les statistiques du référentiel RGAA"
"Combien de critères RGAA sont de niveau AA ?"
```

**`rgaa_checklist`** — Génère une checklist de tests manuels avec outils recommandés, filtrable par thème ou liste de critères.

```
"Génère une checklist d'audit pour les thèmes Formulaires et Navigation"
"Génère une checklist pour les critères 1.1, 1.2 et 1.3"
"Quels outils utiliser pour tester le critère 9.1 ?"
```

**`rgaa_taux_conformite`** — Calcule le taux de conformité officiel RGAA à partir des résultats d'un audit (C / NC / NA par critère).

```
"Sur 42 critères applicables, 30 sont conformes et 12 non conformes. Quel est le taux ?"
"Calcule le taux de conformité à partir de : {\"1.1\": \"C\", \"1.2\": \"NC\", \"6.1\": \"NA\"}"
```

---

## Analyse statique HTML

**`rgaa_analyser`** — Analyse statique d'une URL et détecte les violations RGAA sur les thèmes automatisables.

```
"Analyse l'accessibilité de https://example.com selon le RGAA 4.2.1"
"Audite le thème Images et Formulaires de https://mon-site.fr"
"Quelles violations RGAA détectes-tu sur https://example.com ?"
```

### Thèmes couverts automatiquement

| Thème | Critères vérifiés |
|-------|-------------------|
| 1 — Images | Attribut `alt` manquant (1.1) |
| 2 — Cadres | `title` sur les iframes (2.1) |
| 5 — Tableaux | Caption et `scope` sur `th` (5.1, 5.7) |
| 6 — Liens | Intitulé accessible des liens (6.1) |
| 8 — Éléments obligatoires | Lang, title, charset (8.3, 8.5, 8.6) |
| 9 — Structuration | H1 présent, hiérarchie des titres (9.1, 9.2) |
| 11 — Formulaires | Étiquettes des champs (11.1) |
| 12 — Navigation | Liens d'évitement (12.11) |

L'analyse automatique couvre ~57% des critères applicables. Les critères restants nécessitent des tests manuels avec lecteur d'écran — utilisez `rgaa_checklist` pour les obtenir.

---

## Types d'audit RGAA

Trois types d'audit sont disponibles, chacun avec un périmètre différent :

| Type | Critères | Obligation légale | Usage recommandé |
|------|----------|-------------------|-----------------|
| `complet` | 106 | ✅ Oui | Conformité RGAA officielle (DINUM, collectivités, établissements publics) |
| `rapide` | 25 | ❌ Non | Premier diagnostic rapide — critères essentiels niveau A |
| `complementaire` | 25 | ❌ Non | Approfondissement sur images avancées, médias, tableaux, consultation |

**`rgaa_types_audit`** — Aucun paramètre. Retourne la liste des types avec leurs métadonnées.

```
"Quels types d'audit RGAA existent ?"
"Quel type d'audit répond à l'obligation légale ?"
```

**`rgaa_criteres_audit`** — Retourne la liste enrichie des critères (id, thème, titre) pour le type demandé.

```
"Donne-moi les critères de l'audit rapide RGAA"
"Liste les critères de l'audit complémentaire"
"Quels sont les 106 critères de l'audit complet ?"
```

### Combiner les outils pour un audit guidé

```
"Effectue un audit rapide de https://example.com"
→ utilise audit_rapide prompt ou : rgaa_criteres_audit(rapide) + rgaa_analyser + rgaa_checklist

"Effectue un audit complémentaire de https://example.com"
→ utilise audit_complementaire prompt ou : rgaa_criteres_audit(complementaire) + rgaa_checklist

"Fais un audit de type rapide de https://example.com"
→ utilise le prompt générique audit_par_type(url, type)
```

> **Note :** Seul l'audit complet couvre l'obligation légale RGAA. Les audits rapide et complémentaire sont des diagnostics — utiles en développement ou pour prioriser, mais insuffisants pour une déclaration d'accessibilité.

---

## Exemples de prompts

```
"Liste tous les critères RGAA du thème Images"

"Donne-moi le détail complet du critère 1.1"

"Cherche les critères sur les alternatives textuelles"

"Analyse l'accessibilité de https://example.com selon le RGAA 4.2.1"

"Génère une checklist de tests manuels pour le thème Formulaires"

"Sur 42 critères applicables, 30 sont conformes et 12 non conformes. Quel est le taux ?"

"Quels critères RGAA correspondent à WCAG 2.1 AA ?"

"Qu'est-ce que la 'restitution' dans le glossaire RGAA ?"
```

---

## Structure d'un critère

```json
{
  "id": "1.1",
  "titre": "Chaque image porteuse d'information a-t-elle une alternative textuelle ?",
  "theme": "1",
  "theme_nom": "Images",
  "niveau_wcag": "A",
  "tests": [
    "1.1.1 : L'image (balise <img> ou balise possédant l'attribut WAI-ARIA role=\"img\") possède-t-elle une alternative textuelle ?"
  ],
  "references": {
    "wcag": ["1.1.1 Non-text Content"]
  }
}
```

Les champs `niveau_wcag` valent `A`, `AA` ou `AAA`.
