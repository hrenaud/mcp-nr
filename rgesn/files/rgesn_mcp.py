"""
Serveur MCP RGESN 2024
Expose les outils d'écoconception numérique à Claude.

Variables d'environnement :
  MCP_TRANSPORT   stdio (défaut) | http
  MCP_HOST        0.0.0.0 (défaut, mode http)
  MCP_PORT        8000 (défaut, mode http)

Gestion des tokens :
  python rgesn_mcp.py --generate-token --name <nom> [--expires-days <N>]
  python rgesn_mcp.py --list-tokens
  python rgesn_mcp.py --revoke-token <token>
"""

from fastmcp.exceptions import ToolError
from data import charger_cache
from mcp_ref_core import routes as _routes_mod, factory
import json
import logging
import os
import sys
from pathlib import Path
from difflib import get_close_matches
from typing import Optional, Any

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
    stream=sys.stderr,
)
logger = logging.getLogger("rgesn-mcp")

_BASE_DIR = Path(__file__).parent
TOKENS_FILE = str(_BASE_DIR.parent / "tokens" / "tokens.json")

VERSION = "1.2.0"
_routes_mod._VERSION = VERSION
_routes_mod._REFERENTIEL_VERSION = charger_cache().get("meta", {}).get("version", "")
_routes_mod._MCP_NAME = "RGESN MCP"
_routes_mod._MCP_ID = "rgesn"
_routes_mod._ITEMS_KEY = "criteres"
_routes_mod._LOGO = "💡"
_routes_mod._ACCENT = "#f59e0b"
_routes_mod._ACCENT_DARK = "#92400e"
_routes_mod._ACCENT_LIGHT = "#fde68a"
_routes_mod._ACCENT_BTN_TEXT = "#000"
_routes_mod._TAGLINE = "Écoconception des services numériques"

_get_base_url = _routes_mod._get_base_url
_get_token_request_url = _routes_mod._get_token_request_url

_VALID_PRIORITES = {"Prioritaire", "Recommandé", "Modéré"}
_VALID_DIFFICULTES = {"Faible", "Moyen", "Fort"}
_NB_THEMES = 9


def _validate_theme(theme: int) -> None:
    if theme not in range(1, _NB_THEMES + 1):
        raise ToolError(
            f"Thème '{theme}' invalide. Les thèmes vont de 1 à {_NB_THEMES}. "
            f"Utilise rgesn_statistiques() pour voir la liste des thèmes."
        )


def _rgesn_tool_definitions() -> list[dict[str, Any]]:
    tool_defs = [
        {
            "name": "rgesn_lister_criteres",
            "description": "Liste les critères RGESN, filtrables par thème, priorité et/ou difficulté",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "theme": {"type": ["integer", "null"], "description": "Numéro de thème (1-9)"},
                    "priorite": {"type": ["string", "null"], "description": "Priorité (Prioritaire, Recommandé, Modéré)"},
                    "difficulte": {"type": ["string", "null"], "description": "Difficulté (Faible, Moyen, Fort)"}
                }
            }
        },
        {
            "name": "rgesn_obtenir_critere",
            "description": "Retourne le détail complet d'un critère RGESN (objectif, mise en œuvre, moyen de contrôle)",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "id": {"type": "string", "description": "Identifiant du critère (ex: 1.1, 8.3)"}
                },
                "required": ["id"]
            }
        },
        {
            "name": "rgesn_chercher",
            "description": "Recherche par mot-clé dans les critères RGESN",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Terme à rechercher"},
                    "theme": {"type": ["integer", "null"], "description": "Restreindre la recherche à un thème (1-9)"}
                },
                "required": ["query"]
            }
        },
        {
            "name": "rgesn_statistiques",
            "description": "Statistiques du référentiel RGESN (priorités, thèmes, difficultés)",
            "inputSchema": {
                "type": "object",
                "properties": {}
            }
        },
        {
            "name": "rgesn_taux_conformite",
            "description": "Calcule le taux de conformité RGESN pondéré par priorité à partir des résultats d'audit",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "resultats": {
                        "type": "object",
                        "description": "Dict {id_critere: statut} avec statuts C (conforme), NC (non-conforme), NA (non-applicable)"
                    }
                },
                "required": ["resultats"]
            }
        },
        {
            "name": "rgesn_checklist",
            "description": "Génère une checklist RGESN prête à l'emploi, filtrable par thème et/ou priorité",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "themes": {"type": ["array", "null"], "description": "Liste de thèmes (1-9)"},
                    "priorites": {"type": ["array", "null"], "description": "Liste de priorités (Prioritaire, Recommandé, Modéré)"}
                }
            }
        }
    ]

    for tool in tool_defs:
        assert "name" in tool
        assert "description" in tool
        assert "inputSchema" in tool

    return tool_defs


def _rgesn_guide_extra_sections() -> str:
    return """
    <h2>5. Prompts MCP</h2>
    <p>Ces prompts sont des workflows préconfigurés invocables directement depuis Claude&nbsp;Code avec <code>/mcp__rgesn__&lt;nom&gt;</code>.</p>
    <table>
      <thead><tr><th>Prompt</th><th>Paramètres</th><th>Description</th></tr></thead>
      <tbody>
        <tr><td><code>audit_ecoconception</code></td><td><code>url</code>, <code>themes?</code></td><td>Audit complet d'un service numérique selon le RGESN 2024</td></tr>
        <tr><td><code>expliquer_critere</code></td><td><code>id_critere</code></td><td>Explication pédagogique d'un critère (objectif, mise en œuvre, contrôle)</td></tr>
        <tr><td><code>checklist_prioritaire</code></td><td><code>themes?</code></td><td>Checklist des 30 critères Prioritaire (poids ×1.5), groupés par thème</td></tr>
        <tr><td><code>rapport_conformite</code></td><td><code>resultats</code></td><td>Rapport structuré à partir d'un dict C/NC/NA — calcule le score pondéré</td></tr>
        <tr><td><code>checklist_par_metier</code></td><td><code>metier?</code></td><td>Checklist filtrée par profil (développeur, designer, chef de projet…)</td></tr>
        <tr><td><code>audit_rapide_rgesn</code></td><td><code>url</code></td><td>Audit express sur les 30 critères Prioritaire (~30 min)</td></tr>
        <tr><td><code>plan_action</code></td><td><code>service</code></td><td>Plan d'action écoconception en 3 horizons (court / moyen / long terme)</td></tr>
        <tr><td><code>evaluer_score</code></td><td><code>criteres_nc</code></td><td>Simule le gain de score RGESN en corrigeant des critères NC</td></tr>
      </tbody>
    </table>

    <h2>6. Exemples de questions</h2>
    <div class="note">Quels critères RGESN s'appliquent à l'hébergement ?</div>
    <div class="note">Explique le critère 1.1 du RGESN et comment le mettre en œuvre</div>
    <div class="note">Génère une checklist pour les critères Prioritaire du thème 4</div>
    <div class="note">Calcule le taux de conformité RGESN à partir de ces résultats</div>
    <div class="note">Quels critères RGESN concernent l'algorithmie et l'IA ?</div>
    <div class="note">Donne-moi les statistiques du référentiel RGESN</div>"""


mcp = factory.create_mcp("RGESN MCP", TOKENS_FILE, _rgesn_tool_definitions, _rgesn_guide_extra_sections)


# ============================================================================
# OUTILS : Référentiel
# ============================================================================

@mcp.tool(
    output_schema={
        "type": "object",
        "properties": {
            "total": {"type": "integer"},
            "criteres": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "theme": {"type": "integer"},
                        "question": {"type": "string"},
                        "priorite": {"type": "string"},
                        "difficulte": {"type": "string"}
                    },
                    "required": ["id", "theme", "question", "priorite", "difficulte"]
                }
            }
        },
        "required": ["total", "criteres"]
    },
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
def rgesn_lister_criteres(
    theme: Optional[int] = None,
    priorite: Optional[str] = None,
    difficulte: Optional[str] = None,
) -> dict:
    """
    Liste les critères RGESN avec filtres optionnels.

    Args:
        theme: Numéro de thème (1-9). None = tous les thèmes.
        priorite: Priorité (Prioritaire, Recommandé, Modéré). None = toutes.
        difficulte: Difficulté (Faible, Moyen, Fort). None = toutes.

    Returns:
        {"total": N, "criteres": [...]}
    """
    if theme is not None:
        _validate_theme(theme)

    if priorite is not None and priorite not in _VALID_PRIORITES:
        raise ToolError(
            f"Priorité '{priorite}' invalide. "
            f"Valeurs acceptées : {', '.join(sorted(_VALID_PRIORITES))}."
        )

    if difficulte is not None and difficulte not in _VALID_DIFFICULTES:
        raise ToolError(
            f"Difficulté '{difficulte}' invalide. "
            f"Valeurs acceptées : {', '.join(sorted(_VALID_DIFFICULTES))}."
        )

    cache = charger_cache()
    criteres = list(cache["criteres"].values())

    if theme is not None:
        criteres = [c for c in criteres if c["theme"] == theme]
    if priorite is not None:
        criteres = [c for c in criteres if c["priorite"] == priorite]
    if difficulte is not None:
        criteres = [c for c in criteres if c["difficulte"] == difficulte]

    return {
        "total": len(criteres),
        "criteres": [
            {
                "id": c["id"],
                "theme": c["theme"],
                "question": c["question"],
                "priorite": c["priorite"],
                "difficulte": c["difficulte"],
            }
            for c in criteres
        ],
    }


@mcp.tool(
    output_schema={
        "type": "object",
        "properties": {
            "id": {"type": "string"},
            "theme": {"type": "integer"},
            "question": {"type": "string"},
            "priorite": {"type": "string"},
            "difficulte": {"type": "string"},
            "cible": {"type": "string"},
            "metiers": {"type": "array", "items": {"type": "string"}},
            "objectif": {"type": "string"},
            "mise_en_oeuvre": {"type": "string"},
            "moyen_de_controle": {"type": "string"}
        },
        "required": ["id", "theme", "question", "priorite", "difficulte"]
    },
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
def rgesn_obtenir_critere(id: str) -> dict:
    """
    Retourne le détail complet d'un critère RGESN.

    Args:
        id: Identifiant du critère (ex: "1.1", "8.3")

    Returns:
        Détail complet : question, priorité, difficulté, cible, métiers, objectif, mise en œuvre, moyen de contrôle
    """
    cache = charger_cache()
    critere = cache["criteres"].get(id)
    if critere is None:
        valid_ids = list(cache["criteres"].keys())
        suggestions = get_close_matches(id, valid_ids, n=1, cutoff=0.4)
        suggest_msg = f" As-tu voulu dire '{suggestions[0]}'?" if suggestions else ""
        raise ToolError(
            f"Critère '{id}' n'existe pas.{suggest_msg} "
            f"Les IDs valides vont de 1.1 à 9.7. "
            f"Utilise rgesn_lister_criteres() pour lister tous les critères."
        )
    return critere


@mcp.tool(
    output_schema={
        "type": "object",
        "properties": {
            "total": {"type": "integer"},
            "criteres": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "theme": {"type": "integer"},
                        "question": {"type": "string"},
                        "priorite": {"type": "string"}
                    },
                    "required": ["id", "theme", "question", "priorite"]
                }
            }
        },
        "required": ["total", "criteres"]
    },
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
def rgesn_chercher(query: str, theme: Optional[int] = None) -> dict:
    """
    Recherche par mot-clé dans les questions et objectifs des critères RGESN.

    Args:
        query: Terme à rechercher
        theme: Restreindre la recherche à un thème (1-9). None = tous.

    Returns:
        {"total": N, "criteres": [...]}
    """
    if not query or not query.strip():
        raise ToolError(
            "La requête de recherche ne peut pas être vide. "
            "Fournis un terme ou un mot-clé (ex: 'hébergement', 'vidéo', 'données')."
        )

    if theme is not None:
        _validate_theme(theme)

    cache = charger_cache()
    q = query.lower()
    criteres_trouves = []

    for c in cache["criteres"].values():
        if theme is not None and c["theme"] != theme:
            continue
        texte = " ".join([
            c.get("question", ""),
            c.get("objectif", ""),
            c.get("mise_en_oeuvre", ""),
            c.get("moyen_de_controle", ""),
            c.get("cible", ""),
        ]).lower()
        if q in texte:
            criteres_trouves.append({
                "id": c["id"],
                "theme": c["theme"],
                "question": c["question"],
                "priorite": c["priorite"],
            })

    return {"total": len(criteres_trouves), "criteres": criteres_trouves}


@mcp.tool(
    output_schema={
        "type": "object",
        "properties": {
            "referentiel_version": {"type": "string"},
            "total_criteres": {"type": "integer"},
            "par_priorite": {
                "type": "object",
                "additionalProperties": {"type": "integer"}
            },
            "par_theme": {
                "type": "object",
                "additionalProperties": {
                    "type": "object",
                    "properties": {
                        "titre": {"type": "string"},
                        "nb_criteres": {"type": "integer"}
                    },
                    "required": ["titre", "nb_criteres"]
                }
            },
            "par_difficulte": {
                "type": "object",
                "additionalProperties": {"type": "integer"}
            }
        },
        "required": ["referentiel_version", "total_criteres", "par_priorite", "par_theme", "par_difficulte"]
    },
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
def rgesn_statistiques() -> dict:
    """
    Retourne les statistiques du référentiel RGESN.

    Returns:
        Version du référentiel, total de critères, répartition par priorité, par thème et par difficulté
    """
    cache = charger_cache()
    criteres = list(cache["criteres"].values())

    par_priorite = {}
    for p in _VALID_PRIORITES:
        par_priorite[p] = sum(1 for c in criteres if c["priorite"] == p)

    par_theme = {}
    for num, titre in cache["themes"].items():
        num_int = int(num)
        subset = [c for c in criteres if c["theme"] == num_int]
        par_theme[num] = {
            "titre": titre,
            "nb_criteres": len(subset),
        }

    par_difficulte = {}
    for d in _VALID_DIFFICULTES:
        par_difficulte[d] = sum(1 for c in criteres if c["difficulte"] == d)

    return {
        "referentiel_version": charger_cache().get("meta", {}).get("version", ""),
        "total_criteres": len(criteres),
        "par_priorite": par_priorite,
        "par_theme": par_theme,
        "par_difficulte": par_difficulte,
    }


@mcp.tool(
    output_schema={
        "type": "object",
        "properties": {
            "score": {"type": "number"},
            "nb_conformes": {"type": "integer"},
            "nb_non_conformes": {"type": "integer"},
            "nb_non_applicables": {"type": "integer"},
            "detail_ponderations": {
                "type": "object",
                "additionalProperties": {"type": "number"}
            }
        },
        "required": ["score", "nb_conformes", "nb_non_conformes", "nb_non_applicables"]
    },
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
def rgesn_taux_conformite(resultats: dict) -> dict:
    """
    Calcule le taux de conformité RGESN pondéré par priorité.

    Formule : [Σ(C × poids) / Σ(applicables × poids)] × 100
    Pondérations : Prioritaire=1.5, Recommandé=1.25, Modéré=1.0
    Les NA sont exclus du calcul.

    Args:
        resultats: Dict {id_critere: statut} avec statuts "C", "NC", ou "NA"
                   Exemple: {"1.1": "C", "1.2": "NC", "1.3": "NA"}

    Returns:
        {"score": float, "nb_conformes": int, "nb_non_conformes": int, "nb_non_applicables": int}
    """
    if not resultats:
        raise ToolError(
            "Les résultats ne peuvent pas être vides. "
            "Fournis un dictionnaire avec au moins un critère et son statut (C, NC ou NA). "
            "Exemple : {'1.1': 'C', '1.2': 'NC'}."
        )

    valides_statuts = {"C", "NC", "NA"}
    invalid_statuts = [(cid, s) for cid, s in resultats.items() if s not in valides_statuts]
    if invalid_statuts:
        details = ", ".join(f"'{cid}': '{s}'" for cid, s in invalid_statuts)
        raise ToolError(
            f"Statuts invalides : {details}. "
            f"Les statuts acceptés sont : C (conforme), NC (non-conforme), NA (non-applicable)."
        )

    cache = charger_cache()
    criteres = cache["criteres"]
    ponderations = cache["ponderations"]

    invalid_ids = [cid for cid in resultats if cid not in criteres]
    if invalid_ids:
        raise ToolError(
            f"Critères inconnus : {invalid_ids}. "
            f"Utilise rgesn_lister_criteres() pour voir les IDs valides."
        )

    somme_conformes = 0.0
    somme_applicables = 0.0
    nb_c = nb_nc = nb_na = 0

    for cid, statut in resultats.items():
        if statut == "NA":
            nb_na += 1
            continue
        poids = ponderations[criteres[cid]["priorite"]]
        somme_applicables += poids
        if statut == "C":
            somme_conformes += poids
            nb_c += 1
        else:
            nb_nc += 1

    score = round(somme_conformes / somme_applicables * 100, 2) if somme_applicables > 0 else 0.0

    return {
        "score": score,
        "nb_conformes": nb_c,
        "nb_non_conformes": nb_nc,
        "nb_non_applicables": nb_na,
        "detail_ponderations": {
            p: v for p, v in ponderations.items()
        },
    }


@mcp.tool(
    output_schema={
        "type": "object",
        "properties": {
            "total": {"type": "integer"},
            "criteres": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "theme": {"type": "integer"},
                        "question": {"type": "string"},
                        "priorite": {"type": "string"},
                        "difficulte": {"type": "string"},
                        "statut": {"type": "string"}
                    },
                    "required": ["id", "theme", "question", "priorite", "difficulte", "statut"]
                }
            }
        },
        "required": ["total", "criteres"]
    },
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
def rgesn_checklist(
    themes: Optional[list] = None,
    priorites: Optional[list] = None,
) -> dict:
    """
    Génère une checklist RGESN prête à l'emploi.

    Args:
        themes: Liste de thèmes (ex: [1, 8]). None = tous.
        priorites: Liste de priorités (ex: ["Prioritaire"]). None = toutes.

    Returns:
        {"total": N, "criteres": [{id, question, priorite, difficulte, statut="NE"}, ...]}
    """
    if themes is not None:
        for t in themes:
            _validate_theme(t)

    if priorites is not None:
        invalid_p = [p for p in priorites if p not in _VALID_PRIORITES]
        if invalid_p:
            raise ToolError(
                f"Priorités invalides : {invalid_p}. "
                f"Valeurs acceptées : {', '.join(sorted(_VALID_PRIORITES))}."
            )

    cache = charger_cache()
    criteres = list(cache["criteres"].values())

    if themes is not None:
        criteres = [c for c in criteres if c["theme"] in themes]
    if priorites is not None:
        criteres = [c for c in criteres if c["priorite"] in priorites]

    result = [
        {
            "id": c["id"],
            "theme": c["theme"],
            "question": c["question"],
            "priorite": c["priorite"],
            "difficulte": c["difficulte"],
            "statut": "NE",
        }
        for c in criteres
    ]

    return {"total": len(result), "criteres": result}


# ============================================================================
# RESSOURCES MCP
# ============================================================================

_routes_mod.register_version_resource(mcp, charger_cache)


@mcp.resource("rgesn://criteres/{critere_id}")
async def resource_critere(critere_id: str) -> str:
    """Détail complet d'un critère RGESN."""
    cache = charger_cache()
    critere = cache["criteres"].get(critere_id)
    if critere is None:
        return json.dumps({"erreur": f"Critère '{critere_id}' introuvable"}, ensure_ascii=False)
    return json.dumps(critere, ensure_ascii=False, indent=2)


@mcp.resource("rgesn://index")
async def resource_index() -> str:
    """Index léger de tous les critères RGESN (id, thème, question, priorité)."""
    cache = charger_cache()
    index = [
        {
            "id": c["id"],
            "theme": c["theme"],
            "question": c["question"],
            "priorite": c["priorite"],
            "difficulte": c["difficulte"],
        }
        for c in cache["criteres"].values()
    ]
    return json.dumps(index, ensure_ascii=False, indent=2)


# ============================================================================
# PROMPTS MCP
# ============================================================================

@mcp.prompt()
def audit_ecoconception(url: str, themes: str = "") -> str:
    """
    Template pour auditer l'écoconception d'un service numérique.

    Args:
        url: URL du service à auditer
        themes: Thèmes à cibler, séparés par virgule (ex: "1,4,8"). Vide = tous.
    """
    themes_str = f"en ciblant les thèmes {themes}" if themes else "sur tous les thèmes"
    return f"""Tu es un expert en écoconception numérique RGESN 2024.

Réalise une évaluation de l'écoconception du service {url} {themes_str}.

Étapes :
1. Utilise rgesn_statistiques() pour avoir une vue d'ensemble du référentiel.
2. Utilise rgesn_lister_criteres() pour lister les critères pertinents.
3. Utilise rgesn_checklist() pour générer une liste de vérification.
4. Pour les critères complexes, utilise rgesn_obtenir_critere() pour le détail complet (objectif, mise en œuvre, moyen de contrôle).
5. Synthétise dans un rapport structuré avec : résumé exécutif, points positifs, axes d'amélioration, prochaines étapes.

Commence par récupérer les statistiques du référentiel."""


@mcp.prompt()
def expliquer_critere(id_critere: str) -> str:
    """
    Template pour expliquer un critère RGESN et comment le mettre en œuvre.

    Args:
        id_critere: Identifiant du critère (ex: "1.1", "8.3")
    """
    return f"""Tu es un expert en écoconception numérique RGESN 2024.

Explique le critère RGESN {id_critere} de façon pédagogique.

Étapes :
1. Utilise rgesn_obtenir_critere("{id_critere}") pour obtenir le détail complet.
2. Présente une explication structurée :
   - **Objectif** — pourquoi ce critère existe et quel impact environnemental il adresse
   - **Qui est concerné** — métiers impliqués
   - **Comment mettre en œuvre** — étapes concrètes et bonnes pratiques
   - **Comment vérifier** — moyen de contrôle officiel
   - **Applicabilité** — cible et cas où le critère est NA"""


@mcp.prompt()
def checklist_prioritaire(themes: str = "") -> str:
    """
    Template pour générer une checklist des critères Prioritaire du RGESN.

    Args:
        themes: Thèmes à cibler, séparés par virgule (ex: "1,4"). Vide = tous.
    """
    themes_param = f", themes=[{themes}]" if themes else ""
    return f"""Tu es un expert en écoconception numérique RGESN 2024.

Génère une checklist des critères RGESN Prioritaire{f' pour les thèmes {themes}' if themes else ''}.

Étapes :
1. Utilise rgesn_checklist(priorites=["Prioritaire"]{themes_param}) pour obtenir la liste.
2. Présente la checklist sous forme de tableau opérationnel :
   - Pour chaque critère : **ID**, **Question**, **Thème**, **Difficulté**
   - Regroupe par thème
   - Ajoute une colonne Statut vide pour la saisie (C / NC / NA / NE)
3. Rappelle en fin de checklist que les critères Prioritaire ont un poids de 1.5 dans le calcul du score RGESN."""


@mcp.prompt()
def rapport_conformite(resultats: str) -> str:
    """
    Template pour générer un rapport de conformité RGESN structuré.

    Args:
        resultats: Résultats d'audit au format dict JSON (ex: '{"1.1": "C", "1.2": "NC"}')
    """
    return f"""Tu es un expert en écoconception numérique RGESN 2024.

Génère un rapport de conformité RGESN complet à partir des résultats suivants :

{resultats}

Étapes :
1. Utilise rgesn_taux_conformite avec les résultats fournis pour calculer le score pondéré officiel.
2. Pour chaque critère NC, utilise rgesn_obtenir_critere pour récupérer le détail (objectif, mise en œuvre).
3. Structure le rapport :
   - **Résumé exécutif** — score global, nombre C/NC/NA/NE, niveau de maturité
   - **Points de conformité** — critères C remarquables
   - **Axes d'amélioration** — critères NC classés par priorité et difficulté
   - **Plan d'action** — top 5 corrections à fort impact sur le score
   - **Prochaines étapes** — recommandations pour progresser vers le niveau supérieur

Le score RGESN est pondéré : Prioritaire×1.5, Recommandé×1.25, Modéré×1.0."""


@mcp.prompt()
def checklist_par_metier(metier: str = "") -> str:
    """
    Template pour générer une checklist RGESN filtrée par profil métier.

    Args:
        metier: Profil cible (ex: "développeur", "designer", "chef de projet"). Vide = tous.
    """
    filtre = f'pour le profil "{metier}"' if metier else "pour tous les métiers"
    return f"""Tu es un expert en écoconception numérique RGESN 2024.

Génère une checklist RGESN opérationnelle {filtre}.

Étapes :
1. Utilise rgesn_checklist() pour obtenir la liste complète des 78 critères.
2. Filtre les critères dont le champ "metiers" contient{f' "{metier}"' if metier else ' le profil visé'}.
3. Pour les critères retenus, utilise rgesn_obtenir_critere pour enrichir avec la mise en œuvre concrète.
4. Présente la checklist en deux sections :
   - **Critères Prioritaire** — à traiter en premier (poids 1.5)
   - **Critères Recommandé et Modéré** — à planifier ensuite
5. Pour chaque critère : **ID**, **Question**, **Difficulté**, **Action concrète** adaptée au profil{f' {metier}' if metier else ''}.

Format final : tableau Markdown prêt à copier dans un outil de suivi."""


@mcp.prompt()
def audit_rapide_rgesn(url: str) -> str:
    """
    Template pour un audit rapide RGESN sur les 30 critères Prioritaire.

    Args:
        url: URL ou description du service à auditer
    """
    return f"""Tu es un expert en écoconception numérique RGESN 2024.

Réalise un audit rapide du service {url} en te concentrant sur les 30 critères Prioritaire.

Étapes :
1. Utilise rgesn_checklist(priorites=["Prioritaire"]) pour obtenir les 30 critères à vérifier.
2. Pour chaque critère, évalue rapidement le statut du service {url} :
   - **C** (Conforme) : bonne pratique visible ou déclarée
   - **NC** (Non conforme) : problème identifiable
   - **NA** (Non applicable) : le critère ne s'applique pas au contexte
   - **NE** (Non évalué) : impossible à évaluer sans accès complet
3. Utilise rgesn_taux_conformite avec les statuts C/NC déterminés pour calculer le score préliminaire.
4. Identifie le top 5 des critères NC les plus impactants sur le score.
5. Génère un rapport synthétique :
   - Score RGESN préliminaire (critères Prioritaire uniquement)
   - Répartition C/NC/NA/NE
   - Top 5 actions immédiates pour progresser

Durée estimée : 30 minutes d'analyse."""


@mcp.prompt()
def plan_action(service: str) -> str:
    """
    Template pour construire un plan d'action d'écoconception RGESN.

    Args:
        service: Description du service numérique (ex: "Site e-commerce B2B en React")
    """
    return f"""Tu es un expert en écoconception numérique RGESN 2024.

Construis un plan d'action d'écoconception pour : {service}

Étapes :
1. Utilise rgesn_statistiques() pour avoir une vue d'ensemble du référentiel.
2. Utilise rgesn_lister_criteres(priorite="Prioritaire") pour identifier les 30 critères à fort poids.
3. Pour chaque thème pertinent, utilise rgesn_lister_criteres(theme=N) pour approfondir.
4. Structure le plan d'action en 3 horizons :
   - **Court terme (< 1 mois)** — quick wins, critères Prioritaire à difficulté Faible
   - **Moyen terme (1-3 mois)** — critères Prioritaire à difficulté Modéré
   - **Long terme (> 3 mois)** — critères à difficulté Fort, refonte architecture
5. Pour chaque action : **Critère RGESN**, **Impact sur le score**, **Effort estimé**, **Responsable métier**

Adapte les recommandations au contexte de : {service}"""


@mcp.prompt()
def evaluer_score(criteres_nc: str) -> str:
    """
    Template pour estimer l'impact sur le score RGESN de corriger des critères NC.

    Args:
        criteres_nc: Liste de critères NC au format JSON (ex: '{"1.1": "NC", "2.3": "NC"}')
    """
    return f"""Tu es un expert en écoconception numérique RGESN 2024.

Évalue l'impact sur le score RGESN de corriger ces critères non conformes :

{criteres_nc}

Étapes :
1. Utilise rgesn_taux_conformite avec les critères actuels (tous NC) pour calculer le score de départ.
2. Pour chaque critère NC, utilise rgesn_obtenir_critere pour connaître sa priorité et son poids.
3. Simule le score après correction en passant chaque critère de NC → C un par un.
4. Classe les corrections par gain de score décroissant :
   - Prioritaire (poids 1.5) → gain maximum
   - Recommandé (poids 1.25)
   - Modéré (poids 1.0)
5. Présente un tableau de ROI :

| Critère | Priorité | Gain score estimé | Difficulté |
|---------|----------|-------------------|------------|

Recommande l'ordre optimal de correction pour maximiser le score RGESN."""


# ============================================================================
# Entrypoint
# ============================================================================

if __name__ == "__main__":
    factory.run_main(mcp, VERSION, "RGESN MCP", charger_cache, "criteres", TOKENS_FILE)
