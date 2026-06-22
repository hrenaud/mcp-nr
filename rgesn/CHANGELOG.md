# Changelog — RGESN MCP

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
