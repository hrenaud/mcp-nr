# Audit Types Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Exposer les 3 types d'audit RGAA (complet, rapide, complémentaire) via 2 nouveaux outils MCP, 3 nouveaux prompts, et les documenter dans le guide HTTP, README et guide développeur.

**Architecture:** Un fichier de données dédié `files/audit_types.json` stocke les métadonnées et listes de critères fixes. Deux fonctions d'accès dans `rgaa_mcp.py` chargent ce fichier avec cache en mémoire (même pattern que `charger_cache()`). Les outils et prompts s'appuient sur ces fonctions.

**Tech Stack:** Python, FastMCP, pytest, JSON

---

## Fichiers concernés

| Fichier | Action |
|---|---|
| `files/audit_types.json` | Créer — données des 3 types d'audit |
| `files/rgaa_mcp.py` | Modifier — loader, 2 outils, 3 prompts, TOOLS_DESCRIPTION, HTML guide |
| `tests/test_tools.py` | Modifier — tests pour les 2 nouveaux outils |
| `README.md` | Modifier — tableau outils + prompts |
| `docs/GUIDE_DEVELOPPEMENT.md` | Modifier — section Types d'audit |

---

## Task 1 : Créer `files/audit_types.json`

**Files:**
- Create: `files/audit_types.json`

- [ ] **Step 1 : Créer le fichier de données**

```json
{
  "complet": {
    "nom": "Audit complet RGAA",
    "description": "Audite tous les critères RGAA 4.2.1. Seul type répondant à l'obligation légale de conformité.",
    "conforme_obligation": true,
    "criteres": null
  },
  "rapide": {
    "nom": "Audit rapide RGAA",
    "description": "25 critères essentiels de niveau A. Diagnostic rapide, ne suffit pas pour l'obligation légale.",
    "conforme_obligation": false,
    "criteres": ["1.1","3.1","4.1","4.10","5.3","5.7","6.1","6.2","7.1","7.3","8.3","8.4","8.5","9.1","10.3","10.6","10.7","11.1","11.2","11.5","11.6","11.9","11.10","12.8","12.9"]
  },
  "complementaire": {
    "nom": "Audit complémentaire RGAA",
    "description": "25 critères complémentaires couvrant images, médias, tableaux, consultation. Complète l'audit rapide.",
    "conforme_obligation": false,
    "criteres": ["1.3","1.5","1.6","1.7","4.2","4.4","4.8","4.9","5.4","5.6","7.2","8.2","8.6","8.10","10.2","10.8","10.9","10.10","13.1","13.3","13.4","13.5","13.6","13.7","13.8"]
  }
}
```

Écrire ce contenu dans `files/audit_types.json`.

- [ ] **Step 2 : Commit**

```bash
git add files/audit_types.json
git commit -m "feat: ajoute audit_types.json avec les 3 types d'audit RGAA"
```

---

## Task 2 : Ajouter le loader `charger_audit_types()` + outil `rgaa_types_audit`

**Files:**
- Modify: `files/rgaa_mcp.py` — après la variable `_cache: dict | None = None` (ligne ~48), ajouter le loader et la variable de cache ; ajouter l'outil après `rgaa_statistiques`
- Test: `tests/test_tools.py`

- [ ] **Step 1 : Écrire les tests qui échouent**

Dans `tests/test_tools.py`, ajouter à la fin du fichier :

```python
# ============================================================================
# rgaa_types_audit
# ============================================================================

class TestTypesAudit:
    def test_returns_three_types(self):
        result = mcp_module.rgaa_types_audit()
        assert len(result["types"]) == 3

    def test_type_slugs(self):
        result = mcp_module.rgaa_types_audit()
        slugs = {t["type"] for t in result["types"]}
        assert slugs == {"complet", "rapide", "complementaire"}

    def test_complet_conforme_obligation(self):
        result = mcp_module.rgaa_types_audit()
        complet = next(t for t in result["types"] if t["type"] == "complet")
        assert complet["conforme_obligation"] is True

    def test_rapide_not_conforme_obligation(self):
        result = mcp_module.rgaa_types_audit()
        rapide = next(t for t in result["types"] if t["type"] == "rapide")
        assert rapide["conforme_obligation"] is False

    def test_complet_has_106_criteres(self):
        result = mcp_module.rgaa_types_audit()
        complet = next(t for t in result["types"] if t["type"] == "complet")
        assert complet["nb_criteres"] == 106

    def test_rapide_has_25_criteres(self):
        result = mcp_module.rgaa_types_audit()
        rapide = next(t for t in result["types"] if t["type"] == "rapide")
        assert rapide["nb_criteres"] == 25

    def test_complementaire_has_25_criteres(self):
        result = mcp_module.rgaa_types_audit()
        complementaire = next(t for t in result["types"] if t["type"] == "complementaire")
        assert complementaire["nb_criteres"] == 25

    def test_each_type_has_required_fields(self):
        result = mcp_module.rgaa_types_audit()
        for t in result["types"]:
            assert "type" in t
            assert "nom" in t
            assert "description" in t
            assert "conforme_obligation" in t
            assert "nb_criteres" in t
```

- [ ] **Step 2 : Vérifier que les tests échouent**

```bash
python -m pytest tests/test_tools.py::TestTypesAudit -v
```

Attendu : FAILED avec `AttributeError: module 'rgaa_mcp' has no attribute 'rgaa_types_audit'`

- [ ] **Step 3 : Ajouter le loader dans `rgaa_mcp.py`**

Après la ligne `_cache: dict | None = None` (vers ligne 48), insérer :

```python
_audit_types_cache: dict | None = None
AUDIT_TYPES_FILE = _BASE_DIR / "audit_types.json"


def charger_audit_types() -> dict:
    global _audit_types_cache
    if _audit_types_cache is None:
        with open(AUDIT_TYPES_FILE, encoding="utf-8") as f:
            _audit_types_cache = json.load(f)
    return _audit_types_cache
```

- [ ] **Step 4 : Ajouter l'outil `rgaa_types_audit` dans `rgaa_mcp.py`**

Après la fonction `rgaa_statistiques` (section `# OUTILS : Référentiel`), ajouter :

```python
@mcp.tool()
def rgaa_types_audit() -> dict:
    """
    Liste les types d'audit RGAA disponibles et indique lequel répond à l'obligation légale.

    Returns:
        {"types": [{"type": "...", "nom": "...", "description": "...", "conforme_obligation": bool, "nb_criteres": int}]}
    """
    audit_types = charger_audit_types()
    cache = charger_cache()
    nb_complet = len(cache["criteres"])

    result = []
    for slug, info in audit_types.items():
        nb = nb_complet if info["criteres"] is None else len(info["criteres"])
        result.append({
            "type": slug,
            "nom": info["nom"],
            "description": info["description"],
            "conforme_obligation": info["conforme_obligation"],
            "nb_criteres": nb,
        })

    return {"types": result}
```

- [ ] **Step 5 : Vérifier que les tests passent**

```bash
python -m pytest tests/test_tools.py::TestTypesAudit -v
```

Attendu : tous PASSED

- [ ] **Step 6 : Commit**

```bash
git add files/rgaa_mcp.py tests/test_tools.py
git commit -m "feat: ajoute rgaa_types_audit — liste les 3 types d'audit RGAA"
```

---

## Task 3 : Ajouter l'outil `rgaa_criteres_audit`

**Files:**
- Modify: `files/rgaa_mcp.py` — ajouter après `rgaa_types_audit`
- Test: `tests/test_tools.py`

- [ ] **Step 1 : Écrire les tests qui échouent**

Dans `tests/test_tools.py`, ajouter après `TestTypesAudit` :

```python
# ============================================================================
# rgaa_criteres_audit
# ============================================================================

class TestCriteresAudit:
    def test_rapide_returns_25_criteres(self):
        result = mcp_module.rgaa_criteres_audit("rapide")
        assert result["nb_criteres"] == 25
        assert len(result["criteres"]) == 25

    def test_complementaire_returns_25_criteres(self):
        result = mcp_module.rgaa_criteres_audit("complementaire")
        assert result["nb_criteres"] == 25
        assert len(result["criteres"]) == 25

    def test_complet_returns_106_criteres(self):
        result = mcp_module.rgaa_criteres_audit("complet")
        assert result["nb_criteres"] == 106
        assert len(result["criteres"]) == 106

    def test_rapide_critere_has_required_fields(self):
        result = mcp_module.rgaa_criteres_audit("rapide")
        for c in result["criteres"]:
            assert "id" in c
            assert "theme" in c
            assert "titre" in c

    def test_rapide_ids_exist_in_cache(self):
        cache = mcp_module.charger_cache()
        result = mcp_module.rgaa_criteres_audit("rapide")
        for c in result["criteres"]:
            assert c["id"] in cache["criteres"], f"Critère {c['id']} absent du cache"

    def test_complementaire_ids_exist_in_cache(self):
        cache = mcp_module.charger_cache()
        result = mcp_module.rgaa_criteres_audit("complementaire")
        for c in result["criteres"]:
            assert c["id"] in cache["criteres"], f"Critère {c['id']} absent du cache"

    def test_complet_conforme_obligation_true(self):
        result = mcp_module.rgaa_criteres_audit("complet")
        assert result["conforme_obligation"] is True

    def test_rapide_conforme_obligation_false(self):
        result = mcp_module.rgaa_criteres_audit("rapide")
        assert result["conforme_obligation"] is False

    def test_invalid_type_returns_error(self):
        result = mcp_module.rgaa_criteres_audit("inconnu")
        assert "erreur" in result

    def test_result_includes_type_and_nom(self):
        result = mcp_module.rgaa_criteres_audit("rapide")
        assert result["type"] == "rapide"
        assert "nom" in result
```

- [ ] **Step 2 : Vérifier que les tests échouent**

```bash
python -m pytest tests/test_tools.py::TestCriteresAudit -v
```

Attendu : FAILED avec `AttributeError: module 'rgaa_mcp' has no attribute 'rgaa_criteres_audit'`

- [ ] **Step 3 : Ajouter l'outil `rgaa_criteres_audit` dans `rgaa_mcp.py`**

Juste après `rgaa_types_audit`, ajouter :

```python
@mcp.tool()
def rgaa_criteres_audit(type: Literal["complet", "rapide", "complementaire"]) -> dict:
    """
    Retourne la liste des critères pour un type d'audit RGAA donné.

    Args:
        type: Type d'audit — "complet" (106 critères, obligation légale), "rapide" (25 critères), "complementaire" (25 critères)

    Returns:
        {"type": "...", "nom": "...", "conforme_obligation": bool, "nb_criteres": int, "criteres": [{"id": "...", "theme": int, "titre": "..."}]}
    """
    audit_types = charger_audit_types()
    if type not in audit_types:
        return {"erreur": f"Type '{type}' inconnu. Valeurs acceptées : complet, rapide, complementaire"}

    info = audit_types[type]
    cache = charger_cache()

    ids = list(cache["criteres"].keys()) if info["criteres"] is None else info["criteres"]

    criteres = []
    for cid in ids:
        c = cache["criteres"].get(cid)
        if c:
            criteres.append({
                "id": c["id"],
                "theme": c["theme"],
                "titre": c["titre"],
            })

    return {
        "type": type,
        "nom": info["nom"],
        "conforme_obligation": info["conforme_obligation"],
        "nb_criteres": len(criteres),
        "criteres": criteres,
    }
```

- [ ] **Step 4 : Vérifier que les tests passent**

```bash
python -m pytest tests/test_tools.py::TestCriteresAudit -v
```

Attendu : tous PASSED

- [ ] **Step 5 : Lancer la suite complète pour vérifier l'absence de régression**

```bash
python -m pytest tests/ -v
```

Attendu : tous PASSED

- [ ] **Step 6 : Commit**

```bash
git add files/rgaa_mcp.py tests/test_tools.py
git commit -m "feat: ajoute rgaa_criteres_audit — retourne les critères par type d'audit"
```

---

## Task 4 : Ajouter les 3 prompts MCP

**Files:**
- Modify: `files/rgaa_mcp.py` — section `# PROMPTS MCP`, après les prompts existants

- [ ] **Step 1 : Ajouter les 3 prompts à la fin de la section `# PROMPTS MCP`**

Après le prompt `criteres_wcag`, ajouter :

```python
@mcp.prompt()
def audit_par_type(url: str, type: str = "complet") -> str:
    """
    Template pour auditer une page selon un type d'audit RGAA donné.

    Args:
        url: URL de la page à auditer
        type: Type d'audit — "complet", "rapide" ou "complementaire"
    """
    return f"""Tu es un expert en accessibilité numérique RGAA 4.2.1.

Effectue un audit de type "{type}" de la page {url}.

Étapes :
1. Utilise `rgaa_types_audit()` pour vérifier les caractéristiques du type "{type}" (notamment si ce type répond à l'obligation légale de conformité).
2. Utilise `rgaa_criteres_audit` avec type="{type}" pour obtenir la liste exacte des critères à auditer.
3. Utilise `rgaa_analyser` avec l'URL {url} pour obtenir les violations automatiques détectées.
4. Pour les critères du type "{type}" ayant des violations ou nécessitant une vérification manuelle, utilise `rgaa_checklist` avec les IDs de ces critères.
5. Synthétise les résultats dans un rapport structuré :
   - **Type d'audit** — nom, périmètre, et mention explicite si ce type répond ou non à l'obligation légale de conformité RGAA
   - **Résumé** — violations détectées parmi les critères du périmètre
   - **Détail par thème** — violations et recommandations
   - **Prochaines étapes** — si ce n'est pas un audit complet, indiquer ce qu'il reste à couvrir

Commence par récupérer les informations sur le type d'audit."""


@mcp.prompt()
def audit_rapide(url: str) -> str:
    """
    Template pour un audit rapide RGAA (25 critères essentiels niveau A).

    Args:
        url: URL de la page à auditer
    """
    return f"""Tu es un expert en accessibilité numérique RGAA 4.2.1.

Effectue un audit rapide de la page {url}.

⚠️ L'audit rapide couvre 25 critères essentiels de niveau A. Il ne répond pas à l'obligation légale de conformité RGAA — seul l'audit complet (106 critères) y satisfait. Cet audit est un diagnostic de premier niveau.

Étapes :
1. Utilise `rgaa_criteres_audit` avec type="rapide" pour obtenir la liste des 25 critères.
2. Utilise `rgaa_analyser` avec l'URL {url} pour détecter les violations automatiques.
3. Pour les critères de l'audit rapide ayant des violations, utilise `rgaa_checklist` avec leurs IDs pour les tests manuels complémentaires.
4. Synthétise dans un rapport concis :
   - **Violations détectées** — critères NC parmi les 25 de l'audit rapide
   - **Recommandations prioritaires** — corrections à fort impact
   - **Note sur le périmètre** — rappel que cet audit couvre 25 critères sur 106 et ne suffit pas pour l'obligation légale

Commence par récupérer la liste des critères de l'audit rapide."""


@mcp.prompt()
def audit_complementaire(url: str) -> str:
    """
    Template pour un audit complémentaire RGAA (25 critères couvrant images avancées, médias, tableaux, consultation).

    Args:
        url: URL de la page à auditer
    """
    return f"""Tu es un expert en accessibilité numérique RGAA 4.2.1.

Effectue un audit complémentaire de la page {url}.

ℹ️ L'audit complémentaire couvre 25 critères additionnels (images avancées, médias, tableaux complexes, consultation). Il complète l'audit rapide mais ne répond pas seul à l'obligation légale de conformité RGAA.

Étapes :
1. Utilise `rgaa_criteres_audit` avec type="complementaire" pour obtenir la liste des 25 critères.
2. Utilise `rgaa_analyser` avec l'URL {url} pour détecter les violations automatiques sur ces critères.
3. Pour les critères de l'audit complémentaire ayant des violations, utilise `rgaa_checklist` avec leurs IDs.
4. Synthétise dans un rapport :
   - **Violations détectées** — critères NC parmi les 25 de l'audit complémentaire
   - **Recommandations** — corrections par thème
   - **Note sur le périmètre** — rappel que cet audit complète l'audit rapide, et que l'audit complet (106 critères) est requis pour l'obligation légale

Commence par récupérer la liste des critères de l'audit complémentaire."""
```

- [ ] **Step 2 : Vérifier que les prompts sont enregistrés (pas de crash à l'import)**

```bash
python -c "import sys; sys.path.insert(0, 'files'); import rgaa_mcp; print('OK')"
```

Attendu : `OK`

- [ ] **Step 3 : Commit**

```bash
git add files/rgaa_mcp.py
git commit -m "feat: ajoute prompts audit_par_type, audit_rapide, audit_complementaire"
```

---

## Task 5 : Mettre à jour `TOOLS_DESCRIPTION` et le HTML du guide HTTP

**Files:**
- Modify: `files/rgaa_mcp.py` — constante `TOOLS_DESCRIPTION` et fonction `_http_guide`

- [ ] **Step 1 : Mettre à jour `TOOLS_DESCRIPTION`**

Trouver la liste `TOOLS_DESCRIPTION` (vers ligne 586) et ajouter les 2 nouvelles entrées à la fin :

```python
TOOLS_DESCRIPTION = [
    ("rgaa_lister_criteres", "Liste les critères RGAA, filtrables par thème"),
    ("rgaa_obtenir_critere", "Retourne le détail d'un critère (tests, WCAG, niveau)"),
    ("rgaa_chercher", "Recherche dans les critères et le glossaire par mot-clé"),
    ("rgaa_glossaire", "Retourne la définition d'un terme du glossaire RGAA"),
    ("rgaa_statistiques", "Statistiques du référentiel (niveaux, thèmes, tests)"),
    ("rgaa_analyser", "Analyse statique d'une URL (thèmes 1,2,5,6,8,9,11,12)"),
    ("rgaa_checklist", "Checklist de tests manuels par thème ou critère"),
    ("rgaa_taux_conformite", "Calcule le taux de conformité RGAA à partir des résultats"),
    ("rgaa_types_audit", "Liste les 3 types d'audit RGAA et indique lequel répond à l'obligation légale"),
    ("rgaa_criteres_audit", "Retourne la liste des critères pour un type d'audit (complet, rapide, complémentaire)"),
]
```

- [ ] **Step 2 : Ajouter une section "Types d'audit" dans le HTML de `_http_guide`**

Dans la fonction `_http_guide`, après la section `<h2>4. Outils disponibles</h2>` (et son tableau `{tools_rows}`), insérer une nouvelle section avant `<h2>5. Exemples de prompts</h2>` :

```html
    <h2>5. Types d'audit RGAA</h2>
    <p>Trois types d'audit sont disponibles selon votre objectif :</p>
    <table>
      <thead><tr><th>Type</th><th>Critères</th><th>Obligation légale</th><th>Usage</th></tr></thead>
      <tbody>
        <tr><td><code>complet</code></td><td>106</td><td>✅ Oui</td><td>Conformité RGAA officielle</td></tr>
        <tr><td><code>rapide</code></td><td>25</td><td>❌ Non</td><td>Diagnostic rapide — critères essentiels niveau A</td></tr>
        <tr><td><code>complementaire</code></td><td>25</td><td>❌ Non</td><td>Critères avancés images, médias, tableaux, consultation</td></tr>
      </tbody>
    </table>
    <div class="note">Seul l'audit complet (106 critères) satisfait à l'obligation légale de conformité RGAA. Les audits rapide et complémentaire sont des outils de diagnostic.</div>
```

Puis renuméroter les sections suivantes : `<h2>5. Exemples de prompts</h2>` → `<h2>6. Exemples de prompts</h2>` et `<h2>6. Thèmes analysés automatiquement</h2>` → `<h2>7. Thèmes analysés automatiquement</h2>`.

Ajouter aussi les exemples de prompts liés aux types d'audit dans la section exemples (après les notes existantes) :

```html
    <div class="note">Quels types d'audit RGAA existent et lequel est obligatoire légalement ?</div>
    <div class="note">Donne-moi les critères de l'audit rapide RGAA</div>
    <div class="note">Effectue un audit rapide de https://example.com</div>
```

- [ ] **Step 3 : Vérifier que le guide HTTP s'affiche correctement**

```bash
python -m pytest tests/test_tools.py::TestHttpRoutes::test_guide_status_200 tests/test_tools.py::TestHttpRoutes::test_guide_contains_tools_list -v
```

Attendu : PASSED

- [ ] **Step 4 : Vérifier que les nouveaux outils apparaissent dans le guide**

Ajouter ce test temporaire et le lancer (ou vérifier manuellement) :

```bash
python -c "
import sys; sys.path.insert(0, 'files')
import asyncio
from starlette.testclient import TestClient
from starlette.applications import Starlette
from starlette.routing import Route
import rgaa_mcp as m
app = Starlette(routes=[Route('/guide', m._http_guide, methods=['GET'])])
client = TestClient(app)
r = client.get('/guide')
assert 'rgaa_types_audit' in r.text, 'FAIL: rgaa_types_audit absent'
assert 'rgaa_criteres_audit' in r.text, 'FAIL: rgaa_criteres_audit absent'
assert 'Types d\\'audit' in r.text, 'FAIL: section types absent'
print('OK')
"
```

Attendu : `OK`

- [ ] **Step 5 : Commit**

```bash
git add files/rgaa_mcp.py
git commit -m "feat: met à jour le guide HTTP avec les types d'audit et les nouveaux outils"
```

---

## Task 6 : Mettre à jour `README.md`

**Files:**
- Modify: `README.md`

- [ ] **Step 1 : Ajouter les 2 nouveaux outils dans le tableau "Outils disponibles"**

Dans `README.md`, trouver le tableau `## Outils disponibles` et ajouter après `rgaa_taux_conformite` :

```markdown
| `rgaa_types_audit`     | Liste les 3 types d'audit et indique lequel répond à l'obligation légale    | —                                        |
| `rgaa_criteres_audit`  | Retourne la liste des critères pour un type d'audit donné                   | `type: "complet"\|"rapide"\|"complementaire"` |
```

- [ ] **Step 2 : Ajouter une section "Types d'audit" dans les exemples d'utilisation**

Trouver le bloc d'exemples dans `README.md` (section `### Exemples d'utilisation dans Claude`) et ajouter :

```
"Quels types d'audit RGAA existent et lequel est obligatoire légalement ?"

"Donne-moi la liste des critères de l'audit rapide RGAA"

"Effectue un audit rapide de https://example.com"

"Effectue un audit complémentaire de https://example.com"
```

- [ ] **Step 3 : Mettre à jour le compteur d'outils dans la section "Fonctionnalités"**

Remplacer `**8 outils MCP**` par `**10 outils MCP**` dans la section `## Fonctionnalités`.

- [ ] **Step 4 : Mettre à jour la structure du projet dans README.md**

Dans le bloc `files/`, ajouter la ligne `audit_types.json` :

```
│   ├── rgaa_mcp.py              # Serveur MCP principal
│   ├── analyseur.py             # Analyseur statique HTML (8 thèmes)
│   ├── rgaa_cache.json          # 106 critères RGAA (données embarquées)
│   ├── audit_types.json         # Définition des 3 types d'audit (complet, rapide, complémentaire)
│   └── preparer_donnees.py      # Script de mise à jour des données
```

- [ ] **Step 5 : Commit**

```bash
git add README.md
git commit -m "docs: met à jour README avec les 2 nouveaux outils et les types d'audit"
```

---

## Task 7 : Mettre à jour `docs/GUIDE_DEVELOPPEMENT.md`

**Files:**
- Modify: `docs/GUIDE_DEVELOPPEMENT.md`

- [ ] **Step 1 : Ajouter une section "Types d'audit" après la section "Analyse statique HTML"**

```markdown
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
```

- [ ] **Step 2 : Mettre à jour le compteur d'outils en en-tête**

Si le guide mentionne "8 outils MCP", remplacer par "10 outils MCP".

- [ ] **Step 3 : Commit**

```bash
git add docs/GUIDE_DEVELOPPEMENT.md
git commit -m "docs: ajoute section types d'audit dans le guide développeur"
```

---

## Self-Review

**Couverture spec :**
- ✅ `files/audit_types.json` — Task 1
- ✅ Loader `charger_audit_types()` — Task 2
- ✅ Outil `rgaa_types_audit()` — Task 2
- ✅ Outil `rgaa_criteres_audit(type)` — Task 3
- ✅ Prompt `audit_par_type(url, type)` — Task 4
- ✅ Prompt `audit_rapide(url)` — Task 4
- ✅ Prompt `audit_complementaire(url)` — Task 4
- ✅ `TOOLS_DESCRIPTION` mis à jour — Task 5
- ✅ HTML guide `/guide` mis à jour — Task 5
- ✅ `README.md` mis à jour — Task 6
- ✅ `docs/GUIDE_DEVELOPPEMENT.md` mis à jour — Task 7

**Cohérence des types :** `charger_audit_types()` retourne un dict avec les clés `"complet"`, `"rapide"`, `"complementaire"`. Ces mêmes clés sont utilisées comme valeur du paramètre `type` dans `rgaa_criteres_audit`. Cohérent.

**Placeholder scan :** aucun TBD/TODO dans le plan.
