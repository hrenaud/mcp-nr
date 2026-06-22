# MCP RGAA — Brainstorm en cours

## Décisions prises

### Stack technique
- Python + FastMCP (même que GreenIT MCP)
- Docker local, image slim
- Transport : stdio (Claude Code/Desktop) + HTTP avec auth Bearer token
- Volume `tokens/` pour persistance des tokens

### Données
- Source : repo GitHub officiel RGAA (`RGAA/criteres.json` + glossaire + FAQ)
- 106 critères, 13 thèmes
- Pattern : JSON embarqué (`rgaa_cache.json`) + script `preparer_donnees.py` pour re-fetch
- Même pattern que GreenIT MCP

### Playwright
- **Obligatoire** côté utilisateur (MCP Playwright séparé, non embarqué)
- Sans Playwright : outils référentiel disponibles, analyse DOM indisponible
- Architecture : Claude orchestre les deux MCP (RGAA + Playwright)

### Approche d'analyse
- **Approche B** : parsing HTML Python pour critères automatisables (~57%) + Playwright pour DOM rendu
- axe-core écarté pour V1 (pas encore disponible en RGAA, modèle tarifaire incertain) — prévu en V2
- Concept IGT (Intelligent Guided Testing) intégré via outil `rgaa_checklist`

### Rapport
- Généré côté Claude (pas dans le MCP)
- MCP retourne des données structurées, Claude synthétise

## Section 1 validée : Architecture ✅

## À faire : Section 2 — Outils MCP
Voir TODO.md pour la liste complète des outils prévus.

Reprendre le brainstorm à la section 2 : signatures des outils, paramètres, format des réponses.
