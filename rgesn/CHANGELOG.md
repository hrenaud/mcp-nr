# Changelog — RGESN MCP

## [Unreleased]

---

## [2.1.0] — 2026-06-24

### Ajouté

- **`rgesn://metadata`** : nouvelle ressource MCP exposant les statistiques du référentiel (nb critères, nb thèmes, nb prioritaires, pondérations)
- **`GUIDE_DEVELOPPEMENT.md`** : guide complet pour les mainteneurs (structure, tests, mise à jour des données, ajout d'outil, injection routes)

---

## [2.0.2] — 2026-06-24

### Modifié

- **Documentation** : `README.md` mis à jour — `rgesn_criteres_prioritaires` ajouté, structure 7 outils/9 prompts, données complètes pour les 9 thèmes

---

## [2.0.0] — 2026-06-24

### Ajouté

- **`rgesn_criteres_prioritaires`** : nouvel outil retournant les 30 critères de priorité Prioritaire (poids ×1.5), sans paramètre
- **`criteres_prioritaires_rgesn`** : nouveau prompt guidant l'exploration et la planification des 30 critères Prioritaire

---

## [1.2.0] — 2026-06-22

### Ajouté

- **`rgesn_cache.json` complet** : les 68 critères des thèmes 2 à 9 disposent maintenant de `objectif`, `mise_en_oeuvre` et `moyen_de_controle` extraits du PDF officiel RGESN 2024 (ARCEP)

### Modifié

- **Refactorisation** : utilisation de `factory.create_mcp()` et `factory.run_main()` depuis `core/mcp_ref_core/factory.py`
- **Version du référentiel** : `rgesn_statistiques` retourne désormais `referentiel_version` ("2024")
- **Homepage** : version du référentiel affichée sur la page `/`
- **Tests** : `test_tools.py`, `test_routes_http.py` et `test_architecture_parity.py` ajoutés et adaptés à la nouvelle architecture factory

---

## [1.1.1] — 2026-06-22

### Ajouté

- **Prompts** (5 nouveaux) : `rapport_conformite`, `checklist_par_metier`, `audit_rapide_rgesn`, `plan_action`, `evaluer_score` — passe de 3 à 8 prompts
- **`test_prompts.py`** : tests TDD pour les nouveaux prompts

---

## [1.1.0] — 2026-06-22

### Modifié

- **UI** : thème visuel ambre distinct (`#f59e0b`) pour les pages `/` et `/guide`
- Logo 💡 et tagline « Écoconception des services numériques »

### Corrigé

- Assertions VERSION dans les tests (`isinstance` au lieu de valeur hardcodée)

---

## [1.0.0] — 2026-06-22

Première release dans le monorepo `mcp-nr` (anciennement `0.1.0` en dépôt séparé).

---

## [0.1.0] — 2026-06-22

### Ajouté

- Implémentation initiale du serveur MCP RGESN (Référentiel Général d'Écoconception des Services Numériques 2024)
- Cache statique `rgesn_cache.json` avec les 78 critères RGESN 2024 (30 Prioritaire, 28 Recommandé, 20 Modéré) répartis en 9 thèmes
- Données complètes (objectif, mise en œuvre, moyen de contrôle, cible, métiers) pour le thème 1 (Stratégie, 10 critères)
- 6 outils MCP :
  - `rgesn_lister_criteres` — liste les critères avec filtres par thème, priorité et difficulté
  - `rgesn_obtenir_critere` — détail complet d'un critère
  - `rgesn_chercher` — recherche par mot-clé
  - `rgesn_statistiques` — statistiques du référentiel par priorité, thème et difficulté
  - `rgesn_taux_conformite` — calcul du taux de conformité pondéré (Prioritaire×1.5, Recommandé×1.25, Modéré×1.0)
  - `rgesn_checklist` — génération de checklist filtrée
- 3 ressources MCP : `rgesn://version`, `rgesn://index`, `rgesn://criteres/{id}`
- 3 prompts MCP : `audit_ecoconception`, `expliquer_critere`, `checklist_prioritaire`
- Gestion des tokens d'accès (DynamicTokenVerifier)
- Script `preparer_donnees.py` pour compléter les données des thèmes 2-9 depuis le PDF officiel
- 43 tests (TDD)
