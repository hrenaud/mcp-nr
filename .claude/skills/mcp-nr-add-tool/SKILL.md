---
name: mcp-nr-add-tool
description: Use when adding a new tool or prompt to one of the mcp-nr MCPs (greenit, rgaa, rgesn) — guides the full checklist to keep all files consistent
---

# Ajouter un outil MCP

Checklist pour ajouter un outil ou un prompt à l'un des MCPs du monorepo. À suivre dans l'ordre — chaque étape a une vérification.

---

## 0. Identifier le MCP cible

Déterminer dans quel MCP va le nouvel outil : `greenit`, `rgaa` ou `rgesn`.

Fichiers principaux à modifier :

| Fichier                     | Rôle                                         |
| --------------------------- | -------------------------------------------- |
| `<mcp>/files/<mcp>_mcp.py`  | Implémentation (`@mcp.tool` / `@mcp.prompt`) |
| `<mcp>/tests/test_tools.py` | Tests TDD                                    |
| `<mcp>/README.md`           | Documentation utilisateur                    |
| `OUTILS.md` (racine)        | Tableau récapitulatif personnel              |
| `<mcp>/CHANGELOG.md`        | Entrée `[Unreleased]`                        |

---

## 1. Écrire le test TDD d'abord

Dans `<mcp>/tests/test_tools.py`, ajouter les tests **avant** l'implémentation :

```python
def test_mon_outil_retourne_resultats(self):
    result = mcp_module.rgesn_mon_outil(param1="valeur")
    assert "cle_attendue" in result

def test_mon_outil_param_invalide_leve_erreur(self):
    with pytest.raises(ToolError):
        mcp_module.rgesn_mon_outil(param1="invalide")
```

Vérifier que les tests **échouent** :

```bash
cd <mcp>/files && pytest ../tests/test_tools.py -v -k "mon_outil"
```

---

## 2. Déclarer les métadonnées dans `_get_tool_definitions()`

Dans `<mcp>/files/<mcp>_mcp.py`, ajouter l'entrée dans la fonction `_<mcp>_tool_definitions()` (utilisée par la route `/guide`) :

```python
{
    "name": "<mcp>_mon_outil",
    "description": "Description courte affichée sur /guide.",
    "params": [
        {"name": "param1", "type": "str", "desc": "Description.", "required": True},
        {"name": "param2", "type": "int", "desc": "Optionnel.", "required": False},
    ],
},
```

---

## 3. Implémenter l'outil

Dans `<mcp>/files/<mcp>_mcp.py`, ajouter la fonction avec le décorateur `@mcp.tool()` :

```python
@mcp.tool(
    annotations=ToolAnnotations(title="Titre lisible"),
)
def <mcp>_mon_outil(param1: str, param2: int = 10) -> dict:
    """Description longue (docstring)."""
    criteres = charger_cache().get("criteres", {})
    # ... logique ...
    return {"resultat": ...}
```

Vérifier que les tests **passent** :

```bash
cd <mcp>/files && pytest ../tests/test_tools.py -v -k "mon_outil"
```

Puis lancer la suite complète pour détecter les régressions :

```bash
cd <mcp>/files && pytest ../tests/ -v
```

---

## 4. Mettre à jour la documentation

### `<mcp>/README.md`

Ajouter une ligne dans la section **Outils** :

```markdown
| `<mcp>_mon_outil` | Description courte. |
```

### `OUTILS.md` (racine)

Ajouter la même ligne dans le tableau du MCP concerné.

### `<mcp>/CHANGELOG.md`

Ajouter sous `[Unreleased]` :

```markdown
### Ajouté

- `<mcp>_mon_outil` : description courte.
```

---

## Règle d'or

Un outil n'est terminé que quand **toutes** ces cases sont cochées :

- [ ] Test TDD écrit et passant
- [ ] Implémentation dans `<mcp>_mcp.py`
- [ ] Entrée dans `_<mcp>_tool_definitions()`
- [ ] README mis à jour
- [ ] OUTILS.md mis à jour
- [ ] CHANGELOG mis à jour
