# Guide développeur — MCP RGESN

Documentation pour les développeurs qui maintiennent ce MCP dans le monorepo `mcp-nr`.

---

## Structure des fichiers

```
rgesn/
├── files/
│   ├── rgesn_mcp.py          # Outils, ressources et prompts MCP
│   ├── data.py               # Chargement du cache
│   ├── preparer_donnees.py   # Mise à jour manuelle des données depuis le PDF
│   └── rgesn_cache.json      # Cache statique (source de vérité)
├── tests/
│   ├── test_tools.py              # Tests unitaires des 7 outils MCP
│   ├── test_routes_http.py        # Tests des routes HTTP (/, /guide, admin)
│   ├── test_rgesn.py              # Tests fonctionnels du référentiel
│   ├── test_prompts.py            # Tests des 9 prompts MCP
│   ├── test_smoke.py              # Smoke tests de démarrage
│   └── test_architecture_parity.py  # Vérifie la parité avec le core
└── docs/
    └── GUIDE_DEVELOPPEMENT.md  (ce fichier)
```

---

## Lancer les tests

```bash
cd rgesn/files && pytest ../tests/ -v
```

Tests ciblés :

```bash
pytest ../tests/test_tools.py -v        # outils MCP uniquement
pytest ../tests/test_rgesn.py -v        # référentiel et pondération
pytest ../tests/test_routes_http.py -v  # routes HTTP
```

---

## Mettre à jour les données

Contrairement à GreenIT et RGAA, les données RGESN n'ont pas d'API publique JSON. Le cache est mis à jour manuellement depuis le PDF officiel ARCEP.

PDF source : `https://www.arcep.fr/uploads/tx_gspublication/referentiel_general_ecoconception_des_services_numeriques_version_2024.pdf`

Pour compléter un critère, utiliser `mettre_a_jour_critere()` dans `preparer_donnees.py` :

```python
# Dans preparer_donnees.py, ajouter en bas :
data = charger()
mettre_a_jour_critere(data, "2.1",
    objectif="...",
    mise_en_oeuvre="...",
    moyen_de_controle="...",
)
sauvegarder(data)
```

Puis exécuter : `cd rgesn/files && python preparer_donnees.py`

État actuel : thème 1 (Stratégie, 10 critères) complet ; thèmes 2–9 ont les métadonnées mais les champs `objectif/mise_en_oeuvre/moyen_de_controle` sont vides.

Structure du cache :

```json
{
  "meta": { "version": "2024", "updated_at": "..." },
  "criteres": {
    "1.1": {
      "id": "1.1",
      "theme": 1,
      "question": "...",
      "priorite": "Prioritaire",
      "difficulte": "Faible",
      "objectif": "...",
      "mise_en_oeuvre": "...",
      "moyen_de_controle": "...",
      "cible": ["Décideurs"],
      "metiers": ["Product Owner"]
    }
  }
}
```

---

## Pondération par priorité

Le calcul du taux de conformité `rgesn_taux_conformite` applique une pondération :

| Priorité    | Poids |
| ----------- | ----- |
| Prioritaire | 1.5   |
| Recommandé  | 1.25  |
| Modéré      | 1.0   |

Formule : `[Σ(C × poids) / Σ(applicables × poids)] × 100`. Les critères NA sont exclus.

Le même poids ×1.5 pour les 30 critères Prioritaire est utilisé dans `rgesn_criteres_prioritaires` pour les trier en tête.

---

## Ajouter un outil MCP

1. Déclarer les métadonnées dans `_rgesn_tool_definitions()` (utilisé par la route `/guide`) :

```python
def _rgesn_tool_definitions() -> list[dict]:
    return [
        # ... outils existants ...
        {
            "name": "rgesn_mon_outil",
            "description": "Description courte.",
            "params": [
                {"name": "param1", "type": "str", "desc": "Description.", "required": True},
            ],
        },
    ]
```

2. Implémenter l'outil avec le décorateur `@mcp.tool()` dans `rgesn_mcp.py` :

```python
@mcp.tool(
    description="Description longue de l'outil.",
    annotations=ToolAnnotations(title="Titre lisible"),
)
def rgesn_mon_outil(param1: str) -> dict:
    criteres = charger_cache().get("criteres", {})
    # ... logique ...
    return {"resultat": ...}
```

3. Écrire le test TDD dans `tests/test_tools.py` avant l'implémentation.

4. Mettre à jour `README.md` avec la description de l'outil.

---

## Variables injectées dans `routes.py`

Ces variables sont injectées via `_routes_mod` en début de `rgesn_mcp.py` :

| Variable                           | Valeur actuelle                           |
| ---------------------------------- | ----------------------------------------- |
| `_routes_mod._VERSION`             | `VERSION` (ex. `"2.0.2"`)                 |
| `_routes_mod._REFERENTIEL_VERSION` | version lue dans le cache JSON            |
| `_routes_mod._MCP_NAME`            | `"RGESN MCP"`                             |
| `_routes_mod._MCP_ID`              | `"rgesn"`                                 |
| `_routes_mod._ITEMS_KEY`           | `"criteres"`                              |
| `_routes_mod._LOGO`                | `"💡"`                                    |
| `_routes_mod._ACCENT`              | `"#f59e0b"`                               |
| `_routes_mod._TAGLINE`             | `"Écoconception des services numériques"` |
| `_rgesn_tool_definitions`          | passé à `factory.create_mcp()`            |
| `_rgesn_guide_extra_sections`      | passé à `factory.create_mcp()`            |

---

## Ressources MCP déclarées

| URI                             | Description                |
| ------------------------------- | -------------------------- |
| `rgesn://version`               | Version du MCP (via core)  |
| `rgesn://criteres/{critere_id}` | Critère complet par ID     |
| `rgesn://index`                 | Index de tous les critères |

---

## Release

Voir les instructions dans `CLAUDE.md` (à la racine du monorepo) : mettre à jour `CHANGELOG.md`, puis `./release.sh <version>` depuis la racine, puis `git push && git push origin v<version>`.
