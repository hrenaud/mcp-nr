# E1 — Documentation utilisateur Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add audit workflow documentation to `_http_guide` in `greenit_mcp_final.py` and create `docs/GUIDE_UTILISATEUR.md` covering the full workflow (audit → manual corrections → remediation plan → iteration).

**Architecture:** Two deliverables, zero new files in `files/`. `_http_guide` gets new HTML sections appended before the closing `</div></body></html>`. `GUIDE_UTILISATEUR.md` mirrors the HTML content as plain markdown for offline use. No tests — validation by reading the final output.

**Tech Stack:** Python 3.11, HTML/CSS (inline), Markdown. No new dependencies.

**Prerequisites:** A2, B1, B2, C1 must be implemented (all tools referenced must exist).

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `files/greenit_mcp_final.py` | Modify (`_http_guide`) | Add audit workflow sections + update tools table |
| `docs/GUIDE_UTILISATEUR.md` | Create | Markdown mirror of the guide for offline use |

---

## Task 1: Update `_http_guide` in `greenit_mcp_final.py`

**Context:** `_http_guide` (line 461) currently renders sections 1-6 (prérequis, accès, installation, installation manuelle, outils, exemples). The tools table lists 8 tools but is missing the 4 new tools. This task:
1. Updates the `tools` list to include all 12 tools in the correct order
2. Adds 7 new sections about the audit workflow after the existing section 6

The function returns an f-string HTML page. The insertion point is just before the closing `</div>\n</body>\n</html>` of the returned `html` variable.

**Files:**
- Modify: `files/greenit_mcp_final.py` (lines 478-587)

- [ ] **Step 1: Update the `tools` list in `_http_guide`**

In `files/greenit_mcp_final.py`, locate the `tools = [...]` list (line 478). Replace it with:

```python
    tools = [
        ("lister_fiches", "Liste les fiches avec filtres (lifecycle, ressource, impact, priorité)"),
        ("fiches_prioritaires", "Retourne les fiches à fort impact et haute priorité"),
        ("chercher_fiche", "Recherche des fiches par mot-clé avec scoring de pertinence"),
        ("comparer_fiches", "Compare plusieurs fiches côte à côte avec recommandation"),
        ("audit_rapide", "Génère une liste de fiches adaptées à un contexte projet"),
        ("obtenir_fiche_complete", "Récupère le contenu complet d'une fiche"),
        ("obtenir_statistiques", "Statistiques du référentiel (distributions, top fiches)"),
        ("lister_lifecycles", "Liste les 7 phases du cycle de vie avec nombre de fiches"),
        ("lister_ressources", "Liste les 8 types de ressources avec nombre de fiches"),
        ("obtenir_checklist_audit", "Retourne les 115 fiches avec statut Non-testé pour audit manuel"),
        ("auditer_url", "Audite un site web et génère un rapport EcoIndex + score de conformité GreenIT"),
        ("planifier_remediations", "Re-crawle, vérifie les corrections front-end, génère un plan de remédiation en 3 phases"),
    ]
```

- [ ] **Step 2: Add the audit workflow sections**

In `files/greenit_mcp_final.py`, locate the closing tags of the `html` f-string in `_http_guide`. The current closing is:

```python
    <div class="note">Donne-moi les statistiques du référentiel GreenIT</div>
  </div>
</body>
</html>"""
```

Replace it with:

```python
    <div class="note">Donne-moi les statistiques du référentiel GreenIT</div>
    <div class="note">Audite https://example.com et génère un plan de remédiation</div>
    <div class="note">Quelles fiches GreenIT sont non conformes sur mon site ?</div>

    <h2>7. Workflow d'audit complet</h2>
    <p>Le MCP GreenIT expose un workflow itératif en plusieurs phases :</p>
    <pre><code>1. auditer_url          → rapport initial (json + md + html)
2. Corrections manuelles → éditer audit_complet[*].statut dans le json
3. planifier_remediations → plan de remédiation + vérification front (json + md + html)
4. Nouvelles corrections → éditer audit_complet[*].statut dans le json de remédiation
5. planifier_remediations → nouveau plan mis à jour
   → répéter 4-5 jusqu'à satisfaction</code></pre>
    <p>Les étapes 2-5 sont optionnelles et répétables autant que nécessaire.</p>

    <h2>8. Les fichiers générés</h2>
    <p>Chaque outil écrit trois fichiers dans un sous-dossier daté :</p>
    <pre><code>{{output_dir}}/
  {{YYYY-MM-DD}}/
    greenit-audit-{{domaine}}.json    ← source de vérité, éditable
    greenit-audit-{{domaine}}.md      ← lecture humaine
    greenit-audit-{{domaine}}.html    ← partage / présentation</code></pre>
    <div class="note">Le fichier <code>.json</code> est le seul utile pour la suite du workflow. Les fichiers <code>.md</code> et <code>.html</code> sont pour consultation uniquement.</div>

    <h2>9. Comprendre le score de conformité</h2>
    <p>Score = nombre de fiches Conformes / 115 × 100. Toujours calculé sur les 115 fiches, même les non testées.</p>
    <table>
      <thead><tr><th>Statut</th><th>Signification</th></tr></thead>
      <tbody>
        <tr><td><code>Conforme</code></td><td>La valeur mesurée respecte la limite définie</td></tr>
        <tr><td><code>Non-conforme</code></td><td>La valeur mesurée dépasse la limite définie</td></tr>
        <tr><td><code>Non-applicable</code></td><td>La bonne pratique ne s'applique pas à ce contexte</td></tr>
        <tr><td><code>Indéterminé</code></td><td>Impossible de déterminer sans inspection manuelle</td></tr>
        <tr><td><code>Non-testé</code></td><td>Pas de valeur limite définie ou métrique non mesurée</td></tr>
      </tbody>
    </table>

    <h2>10. Enregistrer des corrections manuelles</h2>
    <p>Pour corriger une fiche après avoir résolu un problème :</p>
    <ol style="padding-left: 20px; margin: 12px 0;">
      <li style="margin-bottom: 8px;">Ouvrir le fichier <code>.json</code> du dernier audit dans un éditeur de texte</li>
      <li style="margin-bottom: 8px;">Trouver la fiche dans <code>audit_complet</code> (chercher par <code>id</code> ou <code>titre</code>)</li>
      <li style="margin-bottom: 8px;">Modifier uniquement le champ <code>"statut"</code> avec l'une des 5 valeurs acceptées</li>
      <li style="margin-bottom: 8px;">Sauvegarder le fichier</li>
      <li style="margin-bottom: 8px;">Passer le chemin du fichier à <code>planifier_remediations</code> via <code>rapport_path</code></li>
    </ol>
    <pre><code>{{
  "id": "RWEB_0047",
  "titre": "Limiter le nombre de requêtes HTTP",
  "statut": "Conforme",  ← modifié de "Non-conforme" à "Conforme"
  ...
}}</code></pre>
    <div class="note"><strong>Important :</strong> Les fiches front-end avec une <code>max_value</code> sont <strong>re-vérifiées automatiquement</strong> par re-crawl — le résultat du crawl prend le dessus sur la valeur manuelle. Les corrections back-end, infrastructure ou contenu (sans <code>max_value</code>) sont <strong>acceptées telles quelles</strong> et comptées dans le score.</div>

    <h2>11. Comprendre le plan de remédiation</h2>
    <p>Le plan de remédiation classe les fiches Non-conformes et Indéterminées en 3 phases par tercile :</p>
    <table>
      <thead><tr><th>Phase</th><th>Horizon</th><th>Sélection</th></tr></thead>
      <tbody>
        <tr><td>Phase 1</td><td>Court terme</td><td>Tiers supérieur (score le plus élevé)</td></tr>
        <tr><td>Phase 2</td><td>Moyen terme</td><td>Tiers médian</td></tr>
        <tr><td>Phase 3</td><td>Long terme</td><td>Tiers inférieur</td></tr>
      </tbody>
    </table>
    <p>Score de priorisation : <code>environmental_impact × 2 − priority_implementation</code> (favorise fort impact + faible effort).</p>
    <p>Le delta cumulatif projette le gain de score si toutes les fiches d'une phase sont corrigées. <code>correction_verifiee: true/false</code> indique si la correction front-end a été re-crawlée et confirmée.</p>

    <h2>12. Exemple de session complète</h2>
    <pre><code># Étape 1 : audit initial
auditer_url("https://mon-site.fr", max_pages=5, output_dir="./audits")
→ ./audits/2026-04-10/greenit-audit-mon-site.fr.json  ✓

# Score initial : 12.2% (14/115 fiches conformes)

# Étape 2 : corrections back-end
# → On corrige le cache HTTP côté serveur
# → On ouvre le JSON et on passe RWEB_0081 de "Non-testé" à "Conforme"

# Étape 3 : plan de remédiation
planifier_remediations(
  rapport_path="./audits/2026-04-10/greenit-audit-mon-site.fr.json",
  output_dir="./audits"
)
→ ./audits/2026-04-10/greenit-remediation-mon-site.fr.json  ✓

# Score après vérification : 18.3% (21/115)
# Phase 1 (court terme) : 6 fiches, gain projeté +5.2%</code></pre>
  </div>
</body>
</html>"""
```

- [ ] **Step 3: Run the HTTP guide test to verify the page still renders**

```bash
cd /Users/renaudheluin/DEV/DEV_GREENIT/refs/mcp-115-greenit
pytest tests/test_tools.py::TestHttpRoutes -v
```

Expected: all HTTP route tests pass.

- [ ] **Step 4: Run the full test suite to check for regressions**

```bash
pytest tests/test_tools.py -v
```

Expected: all existing tests still pass.

- [ ] **Step 5: Commit**

```bash
git add files/greenit_mcp_final.py
git commit -m "feat(guide): update _http_guide — add audit workflow sections and new tools"
```

---

## Task 2: Create `docs/GUIDE_UTILISATEUR.md`

**Context:** The spec requires a markdown document at `docs/GUIDE_UTILISATEUR.md` that mirrors the HTML guide content for offline use. This is a plain text document — no tests, validation by review.

**Files:**
- Create: `docs/GUIDE_UTILISATEUR.md`

- [ ] **Step 1: Create `docs/GUIDE_UTILISATEUR.md`**

Create the file at `docs/GUIDE_UTILISATEUR.md` with the following content:

````markdown
# Guide utilisateur — MCP GreenIT

Le MCP GreenIT connecte Claude au référentiel des 115 bonnes pratiques d'éco-conception web GreenIT, avec un workflow complet d'audit automatisé.

---

## Workflow d'audit complet

```
1. auditer_url          → rapport initial (json + md + html)
2. Corrections manuelles → éditer audit_complet[*].statut dans le json
3. planifier_remediations → plan de remédiation + vérification front (json + md + html)
4. Nouvelles corrections → éditer audit_complet[*].statut dans le json de remédiation
5. planifier_remediations → nouveau plan mis à jour
   → répéter 4-5 jusqu'à satisfaction
```

Les étapes 2-5 sont optionnelles et répétables autant que nécessaire.

---

## Les fichiers générés

Chaque outil écrit trois fichiers dans un sous-dossier daté :

```
{output_dir}/
  {YYYY-MM-DD}/
    greenit-audit-{domaine}.json    ← source de vérité, éditable
    greenit-audit-{domaine}.md      ← lecture humaine
    greenit-audit-{domaine}.html    ← partage / présentation
```

Le fichier `.json` est le seul utile pour la suite du workflow. Les fichiers `.md` et `.html` sont pour consultation uniquement. Les sous-dossiers par date permettent de garder l'historique des cycles d'audit.

---

## Comprendre le score de conformité

Score = nombre de fiches Conformes / 115 × 100. Toujours calculé sur les 115 fiches, même les non testées.

| Statut | Signification |
|--------|--------------|
| `Conforme` | La valeur mesurée respecte la limite définie |
| `Non-conforme` | La valeur mesurée dépasse la limite définie |
| `Non-applicable` | La bonne pratique ne s'applique pas à ce contexte |
| `Indéterminé` | Impossible de déterminer sans inspection manuelle |
| `Non-testé` | Pas de valeur limite définie ou métrique non mesurée |

---

## Enregistrer des corrections manuelles

1. Ouvrir le fichier `.json` du dernier audit dans un éditeur de texte
2. Trouver la fiche dans `audit_complet` (chercher par `id` ou `titre`)
3. Modifier uniquement le champ `"statut"` avec l'une des 5 valeurs acceptées
4. Sauvegarder le fichier
5. Passer le chemin du fichier à `planifier_remediations` via `rapport_path`

Exemple de modification JSON :

```json
{
  "id": "RWEB_0047",
  "titre": "Limiter le nombre de requêtes HTTP",
  "statut": "Conforme",
  ...
}
```

> **Important :** Les fiches front-end avec une `max_value` sont **re-vérifiées automatiquement** par re-crawl — le résultat du crawl prend le dessus sur la valeur manuelle. Les corrections back-end, infrastructure ou contenu (sans `max_value`) sont **acceptées telles quelles** et comptées dans le score.

---

## Comprendre le plan de remédiation

Le plan classe les fiches Non-conformes et Indéterminées en 3 phases par tercile :

| Phase | Horizon | Sélection |
|-------|---------|-----------|
| Phase 1 | Court terme | Tiers supérieur (score le plus élevé) |
| Phase 2 | Moyen terme | Tiers médian |
| Phase 3 | Long terme | Tiers inférieur |

**Score de priorisation :** `environmental_impact × 2 − priority_implementation` (favorise fort impact + faible effort).

Le **delta cumulatif** projette le gain de score si toutes les fiches d'une phase sont corrigées. `correction_verifiee: true/false` indique si la correction front-end a été re-crawlée et confirmée ; `null` pour les fiches non testables automatiquement.

---

## Référence des outils

### `auditer_url(url, max_pages, output_dir)`
Lance un audit initial d'un site web. Crawle jusqu'à `max_pages` pages du même domaine, calcule l'EcoIndex par page, auto-valide les fiches testables, génère le score de conformité sur les 115 fiches. Écrit 3 fichiers sous `{output_dir}/{YYYY-MM-DD}/`.

### `obtenir_checklist_audit()`
Retourne les 115 fiches avec `statut: "Non-testé"` pour remplissage manuel, sans crawl. Utile pour préparer un audit manuel ou identifier les fiches non automatiquement vérifiables.

### `planifier_remediations(rapport_path, output_dir, inclure_toutes)`
Lit le rapport JSON à `rapport_path`, re-crawle les pages, vérifie les corrections front-end, génère un plan de remédiation en 3 phases. Accepte un JSON édité manuellement. Écrit 3 fichiers sous `{output_dir}/{YYYY-MM-DD}/`. Le JSON de sortie peut être passé comme `rapport_path` au cycle suivant.

### `lister_lifecycles()`
Liste les 7 phases du cycle de vie avec leur nombre de fiches. Les `id` retournés sont utilisables comme filtre `lifecycle` dans `lister_fiches`.

### `lister_ressources()`
Liste les 8 types de ressources sauvegardées avec leur nombre de fiches. Les `id` retournés sont utilisables comme filtre `saved_resource` dans `lister_fiches`.

### `lister_fiches(lifecycle, saved_resource, impact_min, priorite_min)`
Filtre les fiches du référentiel. `lifecycle` et `saved_resource` acceptent les `id` retournés par `lister_lifecycles` et `lister_ressources`.

### `chercher_fiche(query)`
Recherche des fiches par mot-clé avec scoring de pertinence.

### `comparer_fiches(ids)`
Compare plusieurs fiches côte à côte avec recommandation.

### `fiches_prioritaires()`
Retourne les fiches à fort impact environnemental et haute priorité d'implémentation.

### `audit_rapide(contexte)`
Génère une liste de fiches adaptées à un contexte projet.

### `obtenir_fiche_complete(id)`
Récupère le contenu complet d'une fiche (description, validations, ressources).

### `obtenir_statistiques()`
Statistiques du référentiel (distributions, top fiches).

---

## Exemple de session complète

```
# Étape 1 : audit initial
auditer_url("https://mon-site.fr", max_pages=5, output_dir="./audits")
→ ./audits/2026-04-10/greenit-audit-mon-site.fr.json  ✓

# Score initial : 12.2% (14/115 fiches conformes)

# Étape 2 : corrections back-end
# → On corrige le cache HTTP côté serveur
# → On ouvre le JSON et on passe RWEB_0081 de "Non-testé" à "Conforme"

# Étape 3 : plan de remédiation
planifier_remediations(
  rapport_path="./audits/2026-04-10/greenit-audit-mon-site.fr.json",
  output_dir="./audits"
)
→ ./audits/2026-04-10/greenit-remediation-mon-site.fr.json  ✓

# Score après vérification : 18.3% (21/115)
# Phase 1 (court terme) : 6 fiches, gain projeté +5.2%

# Étape 4 : nouvelles corrections après phase 1
# → On corrige les 6 fiches de la phase 1
# → On édite le JSON de remédiation pour mettre à jour les statuts

# Étape 5 : nouveau plan
planifier_remediations(
  rapport_path="./audits/2026-04-10/greenit-remediation-mon-site.fr.json",
  output_dir="./audits"
)
→ ./audits/2026-04-10/greenit-remediation-mon-site.fr.json  ✓
# Score mis à jour : 23.5% (27/115)
```
````

- [ ] **Step 2: Commit**

```bash
git add docs/GUIDE_UTILISATEUR.md
git commit -m "docs: add GUIDE_UTILISATEUR.md — full audit workflow documentation"
```
