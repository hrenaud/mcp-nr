---
name: mcp-nr-release
description: Use when preparing or executing a release in the mcp-nr monorepo — publishing a version, bumping version numbers, running release.sh, pushing tags
---

# Release mcp-nr

Checklist complète pour une release cohérente du monorepo. À suivre dans l'ordre.

---

## 1. Identifier le périmètre

Déterminer quels MCPs sont impactés par cette release (greenit / rgaa / rgesn / core / tous).

---

## 2. Synchroniser la documentation

Pour chaque MCP impacté, vérifier la cohérence entre tous les fichiers. **Ne pas attendre qu'on le signale.**

### Outils modifiés / ajoutés / renommés

| Fichier                                                                      | Ce qui doit être à jour                      |
| ---------------------------------------------------------------------------- | -------------------------------------------- |
| `<mcp>/README.md`                                                            | Nom, description, paramètres de l'outil      |
| `OUTILS.md` (racine)                                                         | Ligne dans le tableau récapitulatif          |
| `<mcp>/docs/GUIDE_DEVELOPPEMENT.md`                                          | Section "Ajouter un outil" si pattern changé |
| `_get_tool_definitions()` dans `<mcp>/files/*_mcp.py`                        | Nom + description pour la route `/guide`     |
| `_*_guide_extra_sections()` dans `*_mcp.py` ou `core/mcp_ref_core/routes.py` | HTML de la page `/guide`                     |
| `README.md` racine                                                           | Section "Claude peut :" si capacité nouvelle |

### Vérification des routes `/guide`

Pour chaque MCP impacté, vérifier que `_*_guide_extra_sections()` est cohérente avec le code réel :

- **Outils** : les noms dans `_*_tool_definitions()` correspondent exactement aux fonctions `@mcp.tool()` déclarées
- **Prompts** : tous les `@mcp.prompt()` sont listés dans la section Prompts de `_*_guide_extra_sections()` (section 5)
- **Ressources** : toutes les `@mcp.resource(...)` + `register_version_resource()` sont dans la section Ressources (section 6)
- **Parité** : GreenIT utilise `_greenit_guide_extra_sections()` dans `core/mcp_ref_core/routes.py` ; RGAA et RGESN ont leur propre fonction dans leur `*_mcp.py`

```bash
# Compter les outils/prompts/ressources déclarés vs listés dans le guide
grep -c "@mcp\.tool\|@mcp\.prompt\|@mcp\.resource" <mcp>/files/<mcp>_mcp.py

# Vérifier les noms d'outils dans _*_tool_definitions() vs @mcp.tool()
python3 -c "
import re; text = open('<mcp>/files/<mcp>_mcp.py').read()
defs = re.findall(r'\"name\": \"([^\"]+)\"', open('core/mcp_ref_core/routes.py' if '<mcp>'=='greenit' else '<mcp>/files/<mcp>_mcp.py').read())
impls = re.findall(r'@mcp\.tool\(.*?\)\s*\ndef (\w+)', text, re.DOTALL)
print('defs only:', set(defs)-set(impls)); print('impls only:', set(impls)-set(defs))
"
```

### Chiffres (nb fiches, nb critères)

| Fichier               | Chiffre concerné                                          |
| --------------------- | --------------------------------------------------------- |
| `README.md` racine    | nb bonnes pratiques / critères dans la description du MCP |
| `<mcp>/README.md`     | titre ou intro                                            |
| `docs/DEPLOIEMENT.md` | nb fiches/critères dans le tableau des MCPs               |

---

## 3. Mettre à jour les CHANGELOGs

Déplacer les entrées `[Unreleased]` vers la nouvelle version datée dans :

- `CHANGELOG.md` (racine) — si changement monorepo ou multi-MCPs
- `<mcp>/CHANGELOG.md` — pour chaque MCP impacté

Format :

```markdown
## [X.Y.Z] — YYYY-MM-DD

### Ajouté

- ...

### Modifié

- ...

### Corrigé

- ...
```

---

## 4. Lancer les tests

Pour chaque MCP impacté :

```bash
cd greenit/files && pytest ../tests/ -v
cd rgaa/files   && pytest ../tests/ -v
cd rgesn/files  && pytest ../tests/ -v
```

Tous les tests doivent passer avant de continuer.

---

## 5. Exécuter la release

Depuis la racine du monorepo :

```bash
./release.sh <version>   # bump VERSION dans les 3 *_mcp.py + pyproject.toml
```

---

## 6. Commit et push

```bash
git add -p                               # stager les changements docs + changelogs
git commit -m "chore(release): bump version to <version>"
git push && git push origin v<version>
```

---

## 7. Vérification post-release

```bash
git tag -l | tail -5        # confirmer que le tag existe
git log --oneline -3        # confirmer le commit de release
```

---

## Règle d'or

Si tu as modifié un nom d'outil, un chiffre, ou une fonctionnalité visible :  
**toujours mettre à jour README, OUTILS.md, GUIDE_DEVELOPPEMENT.md, `_get_tool_definitions()` et `/guide` en même temps — dans la même release.**
