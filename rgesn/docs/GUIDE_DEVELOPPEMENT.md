# Guide développeur — MCP RGESN

Le MCP RGESN connecte Claude au référentiel des 78 critères d'écoconception de services numériques (RGESN 2024). Vous pouvez explorer les critères, générer des checklists, et calculer un taux de conformité pondéré.

---

## Outils disponibles

**`rgesn_lister_criteres`** — Liste tous les critères, filtrables par thème (1-9), priorité ou difficulté.

```
"Liste les critères RGESN du thème 3"
"Quels critères RGESN sont de priorité Prioritaire ?"
"Liste les critères de difficulté Faible"
```

**`rgesn_obtenir_critere`** — Détail complet d'un critère : objectif, mise en œuvre, moyen de contrôle, cible, métiers concernés.

```
"Explique le critère RGESN 1.1"
"Donne-moi le détail du critère 4.3 avec son moyen de contrôle"
```

**`rgesn_chercher`** — Recherche par mot-clé dans les critères, optionnellement restreinte à un thème.

```
"Cherche les critères RGESN sur l'hébergement"
"Quels critères parlent d'algorithmie dans le thème 2 ?"
"Trouve les critères liés à la sobriété fonctionnelle"
```

**`rgesn_criteres_prioritaires`** — Les 30 critères de priorité Prioritaire (poids ×1.5), sans paramètre. Point d'entrée idéal pour démarrer une démarche d'écoconception.

```
"Donne-moi les critères RGESN prioritaires"
"Par où commencer pour écoconcevoir mon service ?"
```

**`rgesn_checklist`** — Checklist prête à l'emploi, filtrable par thème(s) et/ou priorité(s).

```
"Génère une checklist RGESN pour les thèmes 1 et 2"
"Checklist des critères Prioritaire du thème 4"
"Checklist complète pour un audit RGESN"
```

**`rgesn_taux_conformite`** — Taux de conformité pondéré (Prioritaire ×1.5, Recommandé ×1.25, Modéré ×1.0) à partir d'un dict de résultats.

```
"Calcule mon taux de conformité RGESN avec ces résultats : {1.1: C, 1.2: NC, 2.1: NA}"
```

**`rgesn_statistiques`** — Distributions du référentiel par priorité, thème et difficulté.

```
"Donne-moi les statistiques du référentiel RGESN"
```

---

## Prompts MCP

Ces prompts sont des workflows préconfigurés invocables directement depuis Claude Code avec `/mcp__rgesn__<nom>`.

| Prompt                        | Paramètres       | Description                                                             |
| ----------------------------- | ---------------- | ----------------------------------------------------------------------- |
| `audit_ecoconception`         | `url`, `themes?` | Audit complet d'un service numérique selon le RGESN 2024                |
| `expliquer_critere`           | `id_critere`     | Explication pédagogique (objectif, mise en œuvre, contrôle)             |
| `checklist_prioritaire`       | `themes?`        | Checklist des 30 critères Prioritaire, groupés par thème                |
| `rapport_conformite`          | `resultats`      | Rapport structuré à partir d'un dict C/NC/NA — calcule le score pondéré |
| `checklist_par_metier`        | `metier?`        | Checklist filtrée par profil (développeur, designer, chef de projet…)   |
| `audit_rapide_rgesn`          | `url`            | Audit express sur les 30 critères Prioritaire (~30 min)                 |
| `plan_action`                 | `service`        | Plan d'action écoconception en 3 horizons (court / moyen / long terme)  |
| `evaluer_score`               | `criteres_nc`    | Simule le gain de score RGESN en corrigeant des critères NC             |
| `criteres_prioritaires_rgesn` | _(aucun)_        | Guide pour explorer et agir sur les 30 critères Prioritaire             |

---

## Exemples de prompts

```
"Quels critères RGESN s'appliquent à l'hébergement ?"

"Explique le critère 1.1 du RGESN et comment le mettre en œuvre"

"Génère une checklist pour les critères Prioritaire du thème 4"

"Calcule le taux de conformité RGESN à partir de ces résultats"

"Quels critères RGESN concernent l'algorithmie et l'IA ?"

"Donne-moi les statistiques du référentiel RGESN"
```

---

## Calcul du taux de conformité

Le taux est pondéré par priorité : `[Σ(C × poids) / Σ(applicables × poids)] × 100`

| Priorité    | Poids |
| ----------- | ----- |
| Prioritaire | 1.5   |
| Recommandé  | 1.25  |
| Modéré      | 1.0   |

Les critères NA sont exclus du calcul.

---

## Structure d'un critère

```json
{
  "id": "1.1",
  "theme": 1,
  "question": "Le service numérique a-t-il défini une politique d'écoconception ?",
  "priorite": "Prioritaire",
  "difficulte": "Faible",
  "objectif": "...",
  "mise_en_oeuvre": "...",
  "moyen_de_controle": "...",
  "cible": ["Décideurs", "Chef de projet"],
  "metiers": ["Product Owner", "Direction"]
}
```
