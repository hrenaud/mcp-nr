# D1 — Persistance des rapports

**Date:** 2026-04-10
**Statut:** Approuvé

## Contexte

Les outils MCP s'exécutent dans le contexte de l'agent IA (Claude Desktop, CLI). Sans persistance fichier, les rapports ne survivent pas à un redémarrage de session et l'utilisateur ne peut pas les consulter indépendamment. Ce spec définit la politique d'écriture sur disque pour tous les outils produisant un rapport.

## Principe

Chaque outil qui produit un rapport écrit **trois fichiers** dans un répertoire de sortie :
- `.json` — rapport structuré, réutilisable par les outils suivants
- `.md` — rapport lisible, pour consultation humaine
- `.html` — rapport présentable, autonome (CSS embarqué, aucune dépendance externe), partageable

L'outil retourne toujours le markdown à l'agent pour affichage immédiat (comportement inchangé). L'écriture disque est un effet de bord systématique. La génération HTML est faite côté Python (templating pur) — zéro token LLM consommé.

## Paramètre `output_dir`

Tous les outils concernés acceptent un paramètre optionnel `output_dir` (string, défaut : `"."`).

| Valeur | Comportement |
|--------|-------------|
| `"."` (défaut) | Répertoire courant au moment de l'appel |
| `"/chemin/absolu"` | Chemin absolu fourni par l'utilisateur |
| `"./rapports"` | Chemin relatif au répertoire courant |

Le répertoire est créé automatiquement s'il n'existe pas (`mkdir -p`).

## Structure des dossiers et nommage

Les fichiers sont organisés en sous-dossiers par date :

```
{output_dir}/
  {YYYY-MM-DD}/
    greenit-{type}-{domaine}.json
    greenit-{type}-{domaine}.md
    greenit-{type}-{domaine}.html
```

- `{YYYY-MM-DD}` : date du jour → sous-dossier créé automatiquement
- `{type}` : `audit` pour `auditer_url`, `remediation` pour `planifier_remediations`
- `{domaine}` : domaine extrait de l'URL auditée (ex: `example.com`)

Exemple :
```
./rapports/
  2026-04-10/
    greenit-audit-example.com.json
    greenit-audit-example.com.md
    greenit-audit-example.com.html
  2026-04-15/
    greenit-remediation-example.com.json
    greenit-remediation-example.com.md
    greenit-remediation-example.com.html
```

Si un fichier du même nom existe déjà dans le sous-dossier du jour, il est écrasé.

## Outils concernés

### `auditer_url`

Nouveau paramètre : `output_dir: str = "."`

Écrit :
- `greenit-audit-{domaine}.json` — rapport JSON complet (structure A2)
- `greenit-audit-{domaine}.md` — rapport markdown
- `greenit-audit-{domaine}.html` — rapport HTML autonome (CSS embarqué)

Retourne : le chemin des fichiers écrits en pied de rapport markdown :

```
---
Rapport sauvegardé :
- `./rapports/2026-04-10/greenit-audit-example.com.json`
- `./rapports/2026-04-10/greenit-audit-example.com.md`
- `./rapports/2026-04-10/greenit-audit-example.com.html`
```

### `planifier_remediations`

Le paramètre `rapport` (JSON string) est remplacé par `rapport_path` (chemin vers le fichier JSON produit par `auditer_url` ou un appel précédent de `planifier_remediations`).

Nouveau paramètre : `output_dir: str = "."` (peut différer du répertoire du rapport d'entrée)

Lit : `rapport_path` → JSON
Écrit :
- `greenit-remediation-{domaine}.json` — plan + `rapport_mis_a_jour`
- `greenit-remediation-{domaine}.md` — plan markdown
- `greenit-remediation-{domaine}.html` — rapport HTML autonome (CSS embarqué)

Le `rapport_mis_a_jour` est inclus dans le JSON de sortie et peut être passé comme `rapport_path` à un appel suivant.

## JSON comme source de vérité pour les corrections manuelles

Le fichier JSON produit par `auditer_url` est conçu pour être édité manuellement par l'utilisateur entre deux cycles d'audit.

**Seul champ à modifier :** `audit_complet[*].statut`

L'utilisateur ouvre le fichier JSON, change le `"statut"` des fiches qu'il a corrigées (ex: `"Non-conforme"` → `"Conforme"` pour une correction back-end ou infrastructure), puis passe le chemin de ce fichier à `planifier_remediations` via `rapport_path`. Le fichier peut avoir été renommé ou déplacé — `rapport_path` accepte n'importe quel chemin valide.

`planifier_remediations` respecte les statuts manuels pour les fiches non testables en front-end, et re-vérifie automatiquement les fiches auto-testables (le re-crawl prend le dessus sur le statut manuel pour ces fiches).

## Workflow itératif sur disque

```
auditer_url("https://example.com", output_dir="./rapports")
→ ./rapports/2026-04-10/greenit-audit-example.com.json
→ ./rapports/2026-04-10/greenit-audit-example.com.md
→ ./rapports/2026-04-10/greenit-audit-example.com.html

[corrections manuelles : éditer audit_complet[*].statut dans le JSON]

planifier_remediations(
  rapport_path="./rapports/2026-04-10/greenit-audit-example.com.json",
  output_dir="./rapports"
)
→ ./rapports/2026-04-15/greenit-remediation-example.com.json
→ ./rapports/2026-04-15/greenit-remediation-example.com.md
→ ./rapports/2026-04-15/greenit-remediation-example.com.html

[nouvelles corrections]

planifier_remediations(
  rapport_path="./rapports/2026-04-15/greenit-remediation-example.com.json",
  output_dir="./rapports"
)
→ ./rapports/2026-04-20/greenit-remediation-example.com.json
→ ./rapports/2026-04-20/greenit-remediation-example.com.md
→ ./rapports/2026-04-20/greenit-remediation-example.com.html
```

## Fichiers modifiés

- `files/greenit_mcp_final.py` — ajout de `output_dir` sur `auditer_url` et `planifier_remediations` ; logique d'écriture disque (JSON, MD, HTML)
- `files/report.py` — ajout de `render_html(data: dict) -> str` : génère le HTML depuis le JSON (détecte audit vs remédiation selon les clés présentes)
- `files/audit_url.py` — `build_report` retourne toujours un dict JSON ; le markdown et HTML sont générés séparément
- `tests/test_tools.py` — tests d'écriture disque (trois fichiers créés, chemins corrects, contenu valide)

## Tests

- `auditer_url` avec `output_dir` crée les trois fichiers `.json`, `.md` et `.html`
- `planifier_remediations` lit `rapport_path` et écrit les trois fichiers de sortie
- Le HTML généré est un fichier autonome valide (pas de dépendance externe)
- `rapport_mis_a_jour` dans le JSON de sortie est passable comme `rapport_path` au cycle suivant
- `output_dir` inexistant est créé automatiquement
- Le pied de rapport markdown indique les chemins des trois fichiers écrits
