# E1 — Documentation utilisateur

**Date:** 2026-04-10
**Statut:** Approuvé

## Contexte

Le MCP GreenIT expose désormais un workflow complet d'audit en plusieurs phases, avec des fichiers écrits sur disque et un cycle itératif de correction. Sans documentation, l'utilisateur ne sait pas dans quel ordre appeler les outils, comment interpréter les fichiers générés, ni comment enregistrer ses corrections manuelles.

La documentation utilisateur est servie en HTTP par le container Docker sur la route `/guide` (`_http_guide` dans `files/greenit_mcp_final.py`). C'est la page que les utilisateurs voient quand ils accèdent au serveur. Elle contient actuellement uniquement le guide d'installation et la liste des outils de base.

Ce spec décrit les additions à apporter à cette page HTML pour couvrir le nouveau workflow d'audit.

## Fichier modifié

`files/greenit_mcp_final.py` — fonction `_http_guide` : ajout de sections HTML pour le workflow d'audit.

## Structure du document

### 1. Vue d'ensemble du workflow

Schéma textuel du cycle complet :

```
1. auditer_url          → rapport initial (json + md + html)
2. Corrections manuelles → éditer audit_complet[*].statut dans le json
3. planifier_remediations → plan de remédiation + vérification front (json + md + html)
4. Nouvelles corrections → éditer audit_complet[*].statut dans le json de remédiation
5. planifier_remediations → nouveau plan mis à jour
   → répéter 4-5 jusqu'à satisfaction
```

Préciser que les étapes 2-5 sont optionnelles et répétables.

### 2. Les fichiers générés

Expliquer la structure de dossiers :

```
{output_dir}/
  {YYYY-MM-DD}/
    greenit-audit-{domaine}.json    ← source de vérité, éditable
    greenit-audit-{domaine}.md      ← lecture humaine
    greenit-audit-{domaine}.html    ← partage / présentation
```

Préciser que :
- `.json` est le seul fichier utile pour la suite du workflow
- `.md` et `.html` sont pour consultation uniquement
- Les sous-dossiers par date permettent de garder l'historique des cycles d'audit

### 3. Comprendre le score de conformité

Expliquer :
- Score = nombre de fiches Conformes / 115 × 100
- Toujours calculé sur 115 fiches, même les non testées
- Les 5 statuts possibles et leur signification :

| Statut | Signification |
|--------|--------------|
| Conforme | La valeur mesurée respecte la limite définie |
| Non-conforme | La valeur mesurée dépasse la limite définie |
| Non-applicable | La bonne pratique ne s'applique pas à ce contexte |
| Indéterminé | Impossible de déterminer sans inspection manuelle |
| Non-testé | Pas de valeur limite définie ou métrique non mesurée |

### 4. Enregistrer des corrections manuelles

Section critique — expliquer étape par étape :

1. Ouvrir le fichier `.json` du dernier audit dans un éditeur de texte
2. Trouver la fiche dans `audit_complet` (chercher par `id` ou `titre`)
3. Modifier uniquement le champ `"statut"` avec l'une des 5 valeurs acceptées
4. Sauvegarder le fichier
5. Passer le chemin du fichier (modifié, renommé ou déplacé) à `planifier_remediations` via `rapport_path`

Donner un exemple concret de modification JSON :

```json
{
  "id": "RWEB_0047",
  "titre": "Limiter le nombre de requêtes HTTP",
  "statut": "Conforme",  ← modifié de "Non-conforme" à "Conforme"
  ...
}
```

Préciser que :
- Les corrections front-end vérifiables (celles avec une `max_value`) seront **re-vérifiées automatiquement** par le re-crawl — le résultat du crawl prend le dessus sur la valeur manuelle
- Les corrections back-end, infrastructure ou contenu (sans `max_value`) sont **acceptées telles quelles** et comptées dans le score

### 5. Comprendre le plan de remédiation

Expliquer :
- Score de priorisation : `environmental_impact × 2 − priority_implementation` (favorise fort impact + faible effort)
- 3 phases par tercile : Court terme / Moyen terme / Long terme
- Le delta cumulatif : projection du gain de score si toutes les fiches d'une phase sont corrigées
- `correction_verifiee: true/false` pour les fiches re-crawlées, `null` pour les non-testables

### 6. Référence des outils

Pour chaque outil, une fiche courte :

#### `auditer_url(url, max_pages, output_dir)`
Lance un audit initial d'un site web. Crawle jusqu'à `max_pages` pages du même domaine, calcule l'EcoIndex par page, auto-valide les fiches testables, génère le score de conformité sur les 115 fiches.

#### `obtenir_checklist_audit()`
Retourne les 115 fiches avec `statut: "Non-testé"` pour remplissage manuel, sans crawl.

#### `planifier_remediations(rapport_path, output_dir, inclure_toutes)`
Re-crawle les pages de l'audit fourni, vérifie les corrections front-end, génère un plan de remédiation en 3 phases. Accepte un JSON édité manuellement.

#### `lister_lifecycles()`
Liste les 7 phases du cycle de vie avec leur nombre de fiches. Les `id` retournés sont utilisables comme filtre dans `lister_fiches`.

#### `lister_ressources()`
Liste les 8 types de ressources sauvegardées avec leur nombre de fiches. Les `id` retournés sont utilisables comme filtre dans `lister_fiches`.

#### `lister_fiches(lifecycle, saved_resource, impact_min, priorite_min)`
Filtre les fiches du référentiel. `lifecycle` et `saved_resource` acceptent les `id` retournés par `lister_lifecycles` et `lister_ressources`.

### 7. Exemple de session complète

Dérouler un exemple fictif bout en bout :

```
# Étape 1 : audit initial
auditer_url("https://mon-site.fr", max_pages=5, output_dir="./audits")
→ ./audits/2026-04-10/greenit-audit-mon-site.fr.json  ✓

# Score initial : 12.2% (14/115 fiches conformes)

# Étape 2 : corrections
# → On corrige le cache HTTP côté serveur (back-end)
# → On ouvre le JSON et on passe RWEB_0081 de "Non-testé" à "Conforme"

# Étape 3 : plan de remédiation
planifier_remediations(
  rapport_path="./audits/2026-04-10/greenit-audit-mon-site.fr.json",
  output_dir="./audits"
)
→ ./audits/2026-04-15/greenit-remediation-mon-site.fr.json  ✓

# Score après vérification : 18.3% (21/115)
# Phase 1 (court terme) : 6 fiches, gain projeté +5.2%
```

## Fichiers modifiés

- `docs/GUIDE_UTILISATEUR.md` (nouveau) — document de référence pour les utilisateurs du MCP GreenIT

## Tests

Ce spec ne génère pas de tests automatisés — il s'agit de documentation. La validation se fait par relecture :
- Chaque outil documenté correspond à un outil réellement implémenté
- Les exemples JSON sont valides et cohérents avec les structures définies dans les specs A1, A2, B1, B2, C1, D1
- Le workflow décrit correspond à l'ordre d'implémentation A1 → B1 → A2 → C1 → B2 → D1
