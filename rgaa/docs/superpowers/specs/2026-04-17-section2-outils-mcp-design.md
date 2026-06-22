# MCP RGAA — Section 2 : Outils MCP — Design

## Décisions structurantes

- **Format de réponse** : JSON structuré strict pour tous les outils (pas de champ `summary`)
- **Ressources MCP** supprimées — outils seulement
- **`rgaa_analyser`** : prend une URL (le MCP fait le fetch), 1 outil côté utilisateur, complexité interne masquée
- **Résultats d'analyse** : groupés par critère, puis par élément incriminé
- **`rgaa_taux_conformite`** : calcul pur, pas de validation de couverture
- **Rapport** : généré côté Claude (décision Section 1 confirmée)

---

## Outils référentiel

### `rgaa_lister_criteres`

```python
rgaa_lister_criteres(theme: int | None = None) -> dict
```

- `theme` : 1–13, optionnel (None = tous les thèmes)

Réponse :
```json
{
  "total": 106,
  "criteres": [
    {"id": "1.1", "theme": 1, "titre": "Chaque image...", "automatisable": true}
  ]
}
```

---

### `rgaa_obtenir_critere`

```python
rgaa_obtenir_critere(id: str) -> dict
```

- `id` : ex. `"1.1"`, `"11.3"`

Réponse :
```json
{
  "id": "1.1",
  "theme": 1,
  "titre": "Chaque image porteuse d'information a-t-elle une alternative textuelle ?",
  "niveau": "A",
  "automatisable": true,
  "tests": ["1.1.1", "1.1.2"],
  "wcag": ["1.1.1"],
  "cas_particuliers": "...",
  "note_technique": "..."
}
```

---

### `rgaa_chercher`

```python
rgaa_chercher(query: str, scope: list[str] = ["criteres", "glossaire"]) -> dict
```

- `scope` : filtrer sur `"criteres"` et/ou `"glossaire"`

Réponse :
```json
{"criteres": [...], "termes_glossaire": [...]}
```

---

### `rgaa_glossaire`

```python
rgaa_glossaire(terme: str) -> dict
```

Réponse :
```json
{"terme": "...", "definition": "...", "exemples": [...]}
```

---

### `rgaa_statistiques`

```python
rgaa_statistiques() -> dict
```

Réponse : nb critères par thème, nb automatisables vs manuels, total

---

## Outil d'analyse

### `rgaa_analyser`

```python
rgaa_analyser(url: str, themes: list[int] | None = None) -> dict
```

- `url` : page à analyser (le MCP fait le fetch)
- `themes` : liste de thèmes à cibler, optionnel (None = tous les automatisables)

Réponse :
```json
{
  "url": "https://...",
  "date": "2026-04-17T...",
  "themes_analyses": [1, 2, 5, 6, 8, 9, 11, 12],
  "nb_violations": 7,
  "criteres": [
    {
      "id": "1.1",
      "statut": "NC",
      "nb_elements": 3,
      "elements": [
        {
          "selecteur": "img#logo",
          "html": "<img id=\"logo\" src=\"...\">",
          "probleme": "Attribut alt manquant"
        }
      ]
    },
    {
      "id": "8.1",
      "statut": "C",
      "elements": []
    }
  ],
  "note": "Analyse statique uniquement. Utiliser Playwright MCP pour l'analyse DOM rendu (contrastes, ARIA dynamique, focus visible)."
}
```

- Le champ `note` est toujours présent (le MCP ne peut pas détecter si Playwright est actif)
- Thèmes automatisables couverts : 1, 2, 5, 6, 8, 9, 11, 12

---

## Outil de guidage (IGT)

### `rgaa_checklist`

```python
rgaa_checklist(themes: list[int] | None = None, criteres: list[str] | None = None) -> dict
```

- Au moins un des deux paramètres requis

Réponse :
```json
{
  "criteres": [
    {
      "id": "1.1",
      "titre": "...",
      "tests": [
        {
          "description": "Vérifier que chaque image a un alt",
          "methode": "Inspecter le DOM ou désactiver les images",
          "outils": ["DevTools", "Web Developer Toolbar", "NVDA"]
        }
      ]
    }
  ]
}
```

---

## Outil de reporting

### `rgaa_taux_conformite`

```python
rgaa_taux_conformite(resultats: dict[str, str]) -> dict
```

- `resultats` : `{"1.1": "C", "1.2": "NC", "1.3": "NA", ...}`
- Valeurs acceptées : `C` (Conforme), `NC` (Non Conforme), `NA` (Non Applicable)
- Formule officielle : `C / (C + NC) * 100` — les NA sont exclus du calcul

Réponse :
```json
{
  "taux": 62.5,
  "nb_conformes": 10,
  "nb_non_conformes": 6,
  "nb_non_applicables": 4,
  "criteres_evalues": 16
}
```

---

## Prompts MCP

### `audit_page`
- Paramètres : `url` (requis), `themes` (optionnel)
- Template guidant Claude pour orchestrer `rgaa_analyser` + `rgaa_checklist`

### `rapport_audit`
- Paramètre : `resultats`
- Template pour générer un rapport Markdown structuré

---

## Récapitulatif des outils V1

| Outil | Catégorie |
|---|---|
| `rgaa_lister_criteres` | Référentiel |
| `rgaa_obtenir_critere` | Référentiel |
| `rgaa_chercher` | Référentiel |
| `rgaa_glossaire` | Référentiel |
| `rgaa_statistiques` | Référentiel |
| `rgaa_analyser` | Analyse |
| `rgaa_checklist` | Guidage (IGT) |
| `rgaa_taux_conformite` | Reporting |
