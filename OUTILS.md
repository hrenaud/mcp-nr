# Outils et prompts MCP

## GreenIT MCP

### Outils (9)

| Outil                            | Description                                                            |
| -------------------------------- | ---------------------------------------------------------------------- |
| `greenit_lister_fiches`          | Liste les fiches avec filtres (lifecycle, ressource, impact, priorité) |
| `greenit_fiches_prioritaires`    | Fiches à fort impact et haute priorité d'implémentation                |
| `greenit_chercher_fiche`         | Recherche par mot-clé avec scoring de pertinence                       |
| `greenit_comparer_fiches`        | Compare plusieurs fiches côte à côte avec recommandation               |
| `greenit_obtenir_fiche_complete` | Détail complet d'une fiche                                             |
| `greenit_obtenir_statistiques`   | Statistiques avancées du référentiel                                   |
| `greenit_lister_lifecycles`      | Liste les 7 phases du cycle de vie                                     |
| `greenit_lister_ressources`      | Liste les 8 types de ressources sauvegardées                           |
| `greenit_calculer_ecoindex`      | Calcule l'EcoIndex (score + grade) à partir de DOM, requests, size     |

### Prompts (8)

| Prompt                   | Paramètres            | Description                                                   |
| ------------------------ | --------------------- | ------------------------------------------------------------- |
| `audit_ecoindex`         | `url`, `focus`        | Analyse l'impact environnemental d'une page via EcoIndex      |
| `rapport_impact`         | `resultats`           | Rapport structuré d'impact avec recommandations               |
| `expliquer_fiche`        | `fiche_id`            | Explique une fiche en détail avec exemples de code            |
| `fiches_par_lifecycle`   | `phase`, `impact_min` | Checklist priorisée des fiches pour une phase du cycle de vie |
| `checklist_ecoindex`     | `domaines`            | Checklist manuelle d'optimisation (DOM, requêtes, taille)     |
| `ressources_comparaison` | `fiche_ids`           | Compare l'impact de plusieurs fiches côte à côte              |
| `audit_rapide_greenit`   | `url`                 | Audit rapide sur les 10 fiches prioritaires                   |
| `audit_par_ressource`    | `ressource`, `budget` | Plan d'action ciblé par type de ressource (network, cpu…)     |

---

## RGAA MCP

### Outils (11)

| Outil                        | Description                                                     |
| ---------------------------- | --------------------------------------------------------------- |
| `rgaa_lister_criteres`       | Liste les critères filtrables par thème ou niveau WCAG          |
| `rgaa_obtenir_critere`       | Détail d'un critère (tests, WCAG, niveau)                       |
| `rgaa_chercher`              | Recherche dans les critères et le glossaire                     |
| `rgaa_glossaire`             | Définition d'un terme du glossaire                              |
| `rgaa_statistiques`          | Statistiques (niveaux, thèmes, tests)                           |
| `rgaa_analyser`              | Analyse statique d'une URL (thèmes 1,2,5,6,8,9,11,12)           |
| `rgaa_checklist`             | Checklist de tests manuels par thème ou critère                 |
| `rgaa_taux_conformite`       | Calcule le taux de conformité à partir des résultats            |
| `rgaa_types_audit`           | Les 3 types d'audit RGAA et leur cadre légal                    |
| `rgaa_criteres_audit`        | Critères pour un type d'audit (complet, rapide, complémentaire) |
| `rgaa_criteres_prioritaires` | Critères classés par priorité WCAG (A > AA > AAA)               |

### Prompts (11)

| Prompt                 | Paramètres        | Description                                                          |
| ---------------------- | ----------------- | -------------------------------------------------------------------- |
| `audit_page`           | `url`, `themes`   | Audit complet avec analyse automatique + checklist manuelle          |
| `rapport_audit`        | `resultats`       | Rapport structuré au format Markdown avec taux de conformité         |
| `expliquer_critere`    | `id_critere`      | Explication pédagogique d'un critère (objectif, tests, WCAG)         |
| `criteres_par_sujet`   | `sujet`, `niveau` | Critères RGAA liés à un sujet, filtrés par niveau WCAG               |
| `checklist_audit`      | `themes`          | Checklist de tests manuels par thème                                 |
| `criteres_wcag`        | `niveau_wcag`     | Tous les critères RGAA d'un niveau WCAG (A/AA/AAA)                   |
| `audit_par_type`       | `url`, `type`     | Audit selon un type (complet, rapide, complémentaire)                |
| `audit_rapide`         | `url`             | Audit rapide sur 25 critères niveau A                                |
| `audit_complementaire` | `url`             | Audit complémentaire 25 critères (images avancées, médias, tableaux) |
| `plan_correction`      | `violations`      | Plan de correction priorisé (bloquant/majeur/mineur)                 |
| `formuler_exigences`   | `contexte`        | Exigences d'accessibilité pour un projet donné                       |

---

## RGESN MCP

### Outils (7)

| Outil                         | Description                                                                  |
| ----------------------------- | ---------------------------------------------------------------------------- |
| `rgesn_lister_criteres`       | Liste les critères filtrables par thème, priorité et difficulté              |
| `rgesn_obtenir_critere`       | Détail complet (objectif, mise en œuvre, moyen de contrôle)                  |
| `rgesn_chercher`              | Recherche par mot-clé, restreinte à un thème si besoin                       |
| `rgesn_statistiques`          | Statistiques par priorité, thème et difficulté                               |
| `rgesn_taux_conformite`       | Taux de conformité pondéré (Prioritaire ×1.5, Recommandé ×1.25, Modéré ×1.0) |
| `rgesn_checklist`             | Checklist filtrable par thème(s) et/ou priorité(s)                           |
| `rgesn_criteres_prioritaires` | Les 30 critères de priorité Prioritaire (poids ×1.5)                         |

### Prompts (9)

| Prompt                        | Paramètres      | Description                                                                |
| ----------------------------- | --------------- | -------------------------------------------------------------------------- |
| `audit_ecoconception`         | `url`, `themes` | Évaluation écoconception complète d'un service                             |
| `expliquer_critere`           | `id_critere`    | Explication pédagogique d'un critère RGESN                                 |
| `checklist_prioritaire`       | `themes`        | Checklist des 30 critères Prioritaire                                      |
| `rapport_conformite`          | `resultats`     | Rapport de conformité avec score pondéré                                   |
| `checklist_par_metier`        | `metier`        | Checklist filtrée par profil (dev, designer, chef de projet…)              |
| `audit_rapide_rgesn`          | `url`           | Audit rapide sur les 30 critères Prioritaire (~30 min)                     |
| `plan_action`                 | `service`       | Plan d'action en 3 horizons (court/moyen/long terme)                       |
| `evaluer_score`               | `criteres_nc`   | Simule le gain de score critère par critère pour prioriser les corrections |
| `criteres_prioritaires_rgesn` | _(aucun)_       | Guide pour explorer et agir sur les 30 critères Prioritaire                |
