"""
Serveur MCP RGAA 4.2.1
Expose les outils d'audit d'accessibilité à Claude.

Variables d'environnement :
  MCP_TRANSPORT   stdio (défaut) | http
  MCP_HOST        0.0.0.0 (défaut, mode http)
  MCP_PORT        8000 (défaut, mode http)

Gestion des tokens :
  python rgaa_mcp.py --generate-token --name <nom> [--expires-days <N>]
  python rgaa_mcp.py --list-tokens
  python rgaa_mcp.py --revoke-token <token>
"""

from fastmcp.exceptions import ToolError
from analyseur import fetcher_html, analyser_html
from data import charger_cache, charger_audit_types
from mcp_ref_core._helpers import validate_themes
from mcp_ref_core import routes as _routes_mod, factory
import httpx
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from difflib import get_close_matches
from typing import Literal, Optional, Any

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
    stream=sys.stderr,
)
logger = logging.getLogger("rgaa-mcp")

_BASE_DIR = Path(__file__).parent
TOKENS_FILE = str(_BASE_DIR.parent / "tokens" / "tokens.json")

VERSION = "2.1.0"
_routes_mod._VERSION = VERSION
_routes_mod._REFERENTIEL_VERSION = charger_cache().get("meta", {}).get("version", "")
_routes_mod._MCP_NAME = "RGAA MCP"
_routes_mod._MCP_ID = "rgaa"
_routes_mod._ITEMS_KEY = "criteres"
_routes_mod._LOGO = "♿"
_routes_mod._ACCENT = "#2563eb"
_routes_mod._ACCENT_DARK = "#1e3a8a"
_routes_mod._ACCENT_LIGHT = "#93c5fd"
_routes_mod._ACCENT_BTN_TEXT = "#fff"
_routes_mod._TAGLINE = "Référentiel d'accessibilité des services web"

_get_base_url = _routes_mod._get_base_url
_get_token_request_url = _routes_mod._get_token_request_url


def _rgaa_tool_definitions() -> list[dict[str, Any]]:
    """Build tool definitions for RGAA MCP.

    Returns:
        list[dict[str, Any]]: Tool definitions with required fields (name, description, inputSchema)
    """
    tool_defs = [
        {
            "name": "rgaa_lister_criteres",
            "description": "Liste les critères RGAA, filtrables par thème",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "theme": {"type": ["integer", "null"], "description": "Numéro de thème (1-13)"},
                    "niveau_wcag": {"type": ["string", "null"], "description": "Niveau WCAG à filtrer (A, AA, AAA)"}
                }
            }
        },
        {
            "name": "rgaa_obtenir_critere",
            "description": "Retourne le détail d'un critère (tests, WCAG, niveau)",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "id": {"type": "string", "description": "Identifiant du critère (ex: 1.1, 11.3)"}
                },
                "required": ["id"]
            }
        },
        {
            "name": "rgaa_chercher",
            "description": "Recherche dans les critères et le glossaire par mot-clé",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Terme à rechercher"},
                    "scope": {"type": ["string", "null"], "description": "Périmètre de recherche (criteres, glossaire)"}
                },
                "required": ["query"]
            }
        },
        {
            "name": "rgaa_glossaire",
            "description": "Retourne la définition d'un terme du glossaire RGAA",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "terme": {"type": "string", "description": "Terme à rechercher (insensible à la casse)"}
                },
                "required": ["terme"]
            }
        },
        {
            "name": "rgaa_statistiques",
            "description": "Statistiques du référentiel (niveaux, thèmes, tests)",
            "inputSchema": {
                "type": "object",
                "properties": {}
            }
        },
        {
            "name": "rgaa_analyser",
            "description": "Analyse statique d'une URL (thèmes 1,2,5,6,8,9,11,12)",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL de la page à analyser"},
                    "themes": {"type": ["array", "null"], "description": "Liste de thèmes à cibler (1-13)"}
                },
                "required": ["url"]
            }
        },
        {
            "name": "rgaa_checklist",
            "description": "Checklist de tests manuels par thème ou critère",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "themes": {"type": ["array", "null"], "description": "Liste de thèmes (1-13)"},
                    "criteres": {"type": ["array", "null"], "description": "Liste d'identifiants de critères"}
                }
            }
        },
        {
            "name": "rgaa_taux_conformite",
            "description": "Calcule le taux de conformité RGAA à partir des résultats",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "resultats": {"type": "object", "description": "Dict {id_critere: statut} avec statuts C, NC, NA"}
                },
                "required": ["resultats"]
            }
        },
        {
            "name": "rgaa_types_audit",
            "description": "Liste les 3 types d'audit RGAA et indique lequel répond à l'obligation légale",
            "inputSchema": {
                "type": "object",
                "properties": {}
            }
        },
        {
            "name": "rgaa_criteres_audit",
            "description": "Retourne la liste des critères pour un type d'audit (complet, rapide, complémentaire)",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "type": {"type": "string", "description": "Type d'audit (complet, rapide, complementaire)", "enum": ["complet", "rapide", "complementaire"]}
                },
                "required": ["type"]
            }
        }
    ]

    # Validate all tools have required fields
    for tool in tool_defs:
        assert "name" in tool, f"Tool missing 'name': {tool}"
        assert "description" in tool, f"Tool missing 'description': {tool}"
        assert "inputSchema" in tool, f"Tool missing 'inputSchema': {tool}"

    return tool_defs


def _rgaa_guide_extra_sections() -> str:
    return """
    <h2>5. Prompts MCP</h2>
    <p>Ces prompts sont des workflows préconfigurés invocables directement depuis Claude&nbsp;Code avec <code>/mcp__rgaa__&lt;nom&gt;</code>.</p>
    <table>
      <thead><tr><th>Prompt</th><th>Paramètres</th><th>Description</th></tr></thead>
      <tbody>
        <tr><td><code>audit_page</code></td><td><code>url</code>, <code>themes?</code></td><td>Audit complet d'une page — analyse automatique + tests manuels complémentaires</td></tr>
        <tr><td><code>rapport_audit</code></td><td><code>resultats</code></td><td>Rapport d'audit Markdown structuré (résumé, violations, recommandations)</td></tr>
        <tr><td><code>expliquer_critere</code></td><td><code>id_critere</code></td><td>Explication pédagogique d'un critère (objectif, impacts, tests, WCAG)</td></tr>
        <tr><td><code>criteres_par_sujet</code></td><td><code>sujet</code>, <code>niveau?</code></td><td>Critères RGAA liés à un sujet (images, formulaires, couleurs…)</td></tr>
        <tr><td><code>checklist_audit</code></td><td><code>themes</code></td><td>Checklist de tests manuels par thème, prête pour un audit terrain</td></tr>
        <tr><td><code>criteres_wcag</code></td><td><code>niveau_wcag?</code></td><td>Critères RGAA correspondant à un niveau WCAG (A / AA / AAA)</td></tr>
        <tr><td><code>audit_par_type</code></td><td><code>url</code>, <code>type?</code></td><td>Audit selon un type RGAA officiel (complet / rapide / complémentaire)</td></tr>
        <tr><td><code>audit_rapide</code></td><td><code>url</code></td><td>Audit express — 25 critères essentiels niveau A (diagnostic premier niveau)</td></tr>
        <tr><td><code>audit_complementaire</code></td><td><code>url</code></td><td>Audit complémentaire — 25 critères additionnels (médias, tableaux, consultation)</td></tr>
        <tr><td><code>plan_correction</code></td><td><code>violations</code></td><td>Plan de correction priorisé par impact utilisateur, avec exemples de code</td></tr>
        <tr><td><code>formuler_exigences</code></td><td><code>contexte</code></td><td>Exigences d'accessibilité pour un projet — légales, de base, de qualité</td></tr>
      </tbody>
    </table>

    <h2>6. Ressources disponibles</h2>
    <p>Les ressources MCP exposent les données brutes du référentiel :</p>
    <table>
      <thead><tr><th>Ressource</th><th>Description</th></tr></thead>
      <tbody>
        <tr><td><code>rgaa://version</code></td><td>Version du serveur et des données</td></tr>
        <tr><td><code>rgaa://metadata</code></td><td>Statistiques du référentiel (nb critères, thèmes, taux automatisable)</td></tr>
        <tr><td><code>rgaa://index</code></td><td>Index de tous les critères (id, titre, thème, niveau)</td></tr>
        <tr><td><code>rgaa://criteres/{critere_id}</code></td><td>Contenu complet d'un critère (ex : <code>1.1</code>)</td></tr>
      </tbody>
    </table>

    <h2>7. Exemples de questions</h2>
    <div class="note">Quels critères RGAA s'appliquent aux images décoratives ?</div>
    <div class="note">Explique le critère 1.1 du RGAA et ses tests associés</div>
    <div class="note">Génère une checklist d'audit pour un composant navigation</div>
    <div class="note">Quels critères WCAG AA concernent les formulaires ?</div>
    <div class="note">Compare les critères 9.1 et 9.2 du RGAA</div>
    <div class="note">Donne-moi les statistiques du référentiel RGAA</div>"""


mcp = factory.create_mcp("RGAA MCP", TOKENS_FILE, _rgaa_tool_definitions, _rgaa_guide_extra_sections)


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
                        "titre": {"type": "string"},
                        "automatisable": {"type": "boolean"},
                        "niveau": {"type": ["string", "null"]}
                    },
                    "required": ["id", "theme", "titre", "automatisable"]
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
def rgaa_lister_criteres(theme: Optional[int] = None, niveau_wcag: Optional[Literal["A", "AA", "AAA"]] = None) -> dict:
    """
    Liste les critères RGAA avec filtres optionnels par thème et/ou niveau WCAG.

    Args:
        theme: Numéro de thème (1-13). None = tous les thèmes.
        niveau_wcag: Niveau WCAG à filtrer. None = tous les niveaux.

    Returns:
        {"total": N, "criteres": [...]}
    """
    if theme is not None:
        validate_themes([theme])

    if niveau_wcag is not None:
        valid_levels = {"A", "AA", "AAA"}
        if niveau_wcag not in valid_levels:
            raise ToolError(
                f"Niveau WCAG '{niveau_wcag}' invalide. "
                f"Les niveaux acceptés sont : A, AA, AAA. "
                f"Utilise rgaa_lister_criteres() sans filtre pour voir tous les critères."
            )

    cache = charger_cache()
    criteres = list(cache["criteres"].values())
    if theme is not None:
        criteres = [c for c in criteres if c["theme"] == theme]
    if niveau_wcag is not None:
        token = f"({niveau_wcag.upper()})"
        criteres = [c for c in criteres if any(token in ref for ref in c.get("wcag", []))]
    return {
        "total": len(criteres),
        "criteres": [
            {
                "id": c["id"],
                "theme": c["theme"],
                "titre": c["titre"],
                "automatisable": c["automatisable"],
                "niveau": c.get("niveau"),
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
            "titre": {"type": "string"},
            "tests": {"type": "object"},
            "wcag": {"type": "array", "items": {"type": "string"}},
            "cas_particuliers": {"type": ["string", "null"]},
            "niveau": {"type": ["string", "null"]},
            "automatisable": {"type": "boolean"},
            "erreur": {"type": "string"}
        }
    },
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
def rgaa_obtenir_critere(id: str) -> dict:
    """
    Retourne le détail complet d'un critère RGAA.

    Args:
        id: Identifiant du critère (ex: "1.1", "11.3")

    Returns:
        Détail complet : titre, tests, références WCAG, cas particuliers, niveau
    """
    cache = charger_cache()
    critere = cache["criteres"].get(id)
    if critere is None:
        # Essayer de suggérer un critère proche
        valid_ids = list(cache["criteres"].keys())
        suggestions = get_close_matches(id, valid_ids, n=1, cutoff=0.4)
        suggest_msg = f" As-tu voulu dire '{suggestions[0]}'?" if suggestions else ""
        raise ToolError(
            f"Critère '{id}' n'existe pas.{suggest_msg} "
            f"Les ID valides vont de 1.1 à 13.13. "
            f"Utilise rgaa_lister_criteres() pour lister tous les critères."
        )
    return critere


@mcp.tool(
    output_schema={
        "type": "object",
        "properties": {
            "criteres": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "theme": {"type": "integer"},
                        "titre": {"type": "string"}
                    },
                    "required": ["id", "theme", "titre"]
                }
            },
            "termes_glossaire": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "terme": {"type": "string"},
                        "definition": {"type": "string"},
                        "examples": {"type": ["array", "null"]}
                    },
                    "required": ["terme", "definition"]
                }
            }
        },
        "required": ["criteres", "termes_glossaire"]
    },
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
def rgaa_chercher(query: str, scope: Optional[list[Literal["criteres", "glossaire"]]] = None) -> dict:
    """
    Recherche par mot-clé dans les critères et/ou le glossaire.

    Args:
        query: Terme à rechercher
        scope: Périmètre de recherche. None = critères et glossaire.

    Returns:
        {"criteres": [...], "termes_glossaire": [...]}
    """
    if not query or not query.strip():
        raise ToolError(
            "La requête de recherche ne peut pas être vide. "
            "Fournis un terme ou un mot-clé (ex: 'images', 'formulaires', 'couleurs')."
        )

    if scope is None:
        scope = ["criteres", "glossaire"]

    cache = charger_cache()
    q = query.lower()
    criteres_trouves = []
    termes_trouves = []

    if "criteres" in scope:
        for c in cache["criteres"].values():
            if q in c["titre"].lower() or q in str(c.get("tests", "")).lower():
                criteres_trouves.append({
                    "id": c["id"],
                    "theme": c["theme"],
                    "titre": c["titre"],
                })

    if "glossaire" in scope:
        for terme, entry in cache["glossaire"].items():
            if q in terme or q in entry["definition"].lower():
                termes_trouves.append(entry)

    return {"criteres": criteres_trouves, "termes_glossaire": termes_trouves}


@mcp.tool(
    output_schema={
        "type": "object",
        "properties": {
            "terme": {"type": "string"},
            "definition": {"type": "string"},
            "exemples": {"type": ["array", "null"], "items": {"type": "string"}},
            "suggestion": {"type": ["string", "null"]},
            "erreur": {"type": ["string", "null"]}
        },
        "required": ["terme", "definition"]
    },
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
def rgaa_glossaire(terme: str) -> dict:
    """
    Retourne la définition d'un terme du glossaire RGAA.

    Args:
        terme: Terme à rechercher (insensible à la casse)

    Returns:
        {"terme": "...", "definition": "...", "exemples": [...]}
    """
    if not terme or not terme.strip():
        raise ToolError(
            "Le terme de recherche ne peut pas être vide. "
            "Fournis un terme du glossaire RGAA (ex: 'alternatives textuelles', 'contraste')."
        )

    cache = charger_cache()
    entry = cache["glossaire"].get(terme.lower())
    if entry is None:
        keys = list(cache["glossaire"].keys())
        t = terme.lower()
        # Sous-chaîne directe
        for key in keys:
            if t in key or key in t:
                val = cache["glossaire"][key]
                return {**val, "suggestion": f"Terme exact '{terme}' introuvable — je pense que tu voulais parler de \"{val['terme']}\""}
        # Correspondance floue (difflib)
        matches = get_close_matches(t, keys, n=1, cutoff=0.4)
        if matches:
            val = cache["glossaire"][matches[0]]
            return {**val, "suggestion": f"Terme exact '{terme}' introuvable — je pense que tu voulais parler de \"{val['terme']}\""}
        raise ToolError(
            f"Terme '{terme}' introuvable dans le glossaire RGAA. "
            f"Utilise rgaa_chercher('{terme}', scope=['glossaire']) pour chercher des termes similaires."
        )
    return entry


@mcp.tool(
    output_schema={
        "type": "object",
        "properties": {
            "referentiel_version": {"type": "string"},
            "total_criteres": {"type": "integer"},
            "automatisables": {"type": "integer"},
            "manuels": {"type": "integer"},
            "par_theme": {
                "type": "object",
                "additionalProperties": {
                    "type": "object",
                    "properties": {
                        "titre": {"type": "string"},
                        "nb_criteres": {"type": "integer"},
                        "automatisables": {"type": "integer"}
                    },
                    "required": ["titre", "nb_criteres", "automatisables"]
                }
            }
        },
        "required": ["referentiel_version", "total_criteres", "automatisables", "manuels", "par_theme"]
    },
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
def rgaa_statistiques() -> dict:
    """
    Retourne les statistiques du référentiel RGAA.

    Returns:
        Version du référentiel, nombre de critères par thème, automatisables vs manuels, total
    """
    cache = charger_cache()
    criteres = list(cache["criteres"].values())

    par_theme = {}
    for num, titre in cache["themes"].items():
        num_int = int(num)
        subset = [c for c in criteres if c["theme"] == num_int]
        par_theme[num] = {
            "titre": titre,
            "nb_criteres": len(subset),
            "automatisables": sum(1 for c in subset if c["automatisable"]),
        }

    auto = sum(1 for c in criteres if c["automatisable"])
    return {
        "referentiel_version": charger_cache().get("meta", {}).get("version", ""),
        "total_criteres": len(criteres),
        "automatisables": auto,
        "manuels": len(criteres) - auto,
        "par_theme": par_theme,
    }


@mcp.tool(
    output_schema={
        "type": "object",
        "properties": {
            "types": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "type": {"type": "string"},
                        "nom": {"type": "string"},
                        "description": {"type": "string"},
                        "conforme_obligation": {"type": "boolean"},
                        "nb_criteres": {"type": "integer"}
                    },
                    "required": ["type", "nom", "description", "conforme_obligation", "nb_criteres"]
                }
            }
        },
        "required": ["types"]
    },
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
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


@mcp.tool(
    output_schema={
        "type": "object",
        "properties": {
            "type": {"type": "string"},
            "nom": {"type": "string"},
            "conforme_obligation": {"type": "boolean"},
            "nb_criteres": {"type": "integer"},
            "criteres": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "theme": {"type": "integer"},
                        "titre": {"type": "string"}
                    },
                    "required": ["id", "theme", "titre"]
                }
            },
            "erreur": {"type": ["string", "null"]}
        },
        "required": ["type", "nom", "conforme_obligation", "nb_criteres", "criteres"]
    },
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
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
        valid_types = ", ".join(audit_types.keys())
        raise ToolError(
            f"Type d'audit '{type}' invalide. Valeurs acceptées : {valid_types}. "
            f"Utilise rgaa_types_audit() pour voir tous les types disponibles."
        )

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


# ============================================================================
# OUTILS : Analyse automatisée
# ============================================================================

@mcp.tool(
    output_schema={
        "type": "object",
        "properties": {
            "url": {"type": "string"},
            "date": {"type": "string"},
            "themes_analyses": {"type": "array", "items": {"type": "integer"}},
            "nb_violations": {"type": "integer"},
            "criteres": {"type": "array", "items": {"type": "object"}},
            "note": {"type": "string"}
        },
        "required": ["url", "date", "themes_analyses", "nb_violations", "criteres"]
    },
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True
    }
)
def rgaa_analyser(url: str, themes: list[int] = None) -> dict:
    """
    Analyse une page web pour détecter les violations RGAA automatisables.

    Args:
        url: URL de la page à analyser
        themes: Liste de thèmes à cibler (1-13). None = tous les automatisables [1,2,5,6,8,9,11,12]

    Returns:
        {"url": "...", "date": "...", "themes_analyses": [...], "nb_violations": N, "criteres": [...], "note": "..."}
    """
    if not url or not url.strip():
        raise ToolError(
            "L'URL ne peut pas être vide. "
            "Fournis une URL valide (ex: https://example.com)."
        )

    if not url.startswith(("http://", "https://")):
        raise ToolError(
            f"L'URL '{url}' est invalide. "
            "Les URLs doivent commencer par http:// ou https://."
        )

    if themes is not None:
        validate_themes(themes)

    try:
        html = fetcher_html(url)
    except (httpx.RequestError, httpx.TimeoutException) as e:
        raise ToolError(f"Impossible de récupérer la page: {e}. Vérifie que l'URL est accessible et que le serveur répond.")
    except httpx.HTTPStatusError as e:
        raise ToolError(f"Erreur HTTP {e.response.status_code}: {e}. La page n'existe pas ou le serveur refuse l'accès.")

    result = analyser_html(html, themes)
    return {
        "url": url,
        "date": datetime.now(timezone.utc).isoformat(),
        **result,
    }


# ============================================================================
# OUTILS : Guidage (IGT)
# ============================================================================

OUTILS_CHECKLIST = {
    1: ["DevTools (onglet Éléments)", "Web Developer Toolbar", "NVDA + Firefox"],
    2: ["DevTools (onglet Éléments)"],
    3: ["Color Contrast Analyser", "DevTools", "WCAG Contrast Checker"],
    4: ["VLC", "Sous-titres natifs du navigateur"],
    5: ["DevTools (onglet Éléments)", "NVDA"],
    6: ["DevTools", "WAVE", "NVDA"],
    7: ["DevTools (onglet Console)", "NVDA", "JAWS"],
    8: ["DevTools (vue Source)", "W3C Validator"],
    9: ["HeadingsMap (extension)", "WAVE", "DevTools"],
    10: ["DevTools (onglet Styles)", "zoom navigateur 200%"],
    11: ["DevTools", "NVDA", "WAVE"],
    12: ["Navigation clavier (Tab)", "NVDA", "DevTools"],
    13: ["DevTools", "NVDA", "tests de défilement"],
}


@mcp.tool(
    output_schema={
        "type": "object",
        "properties": {
            "criteres": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "titre": {"type": "string"},
                        "tests": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "description": {"type": "string"},
                                    "methode": {"type": "string"},
                                    "outils": {"type": "array", "items": {"type": "string"}}
                                },
                                "required": ["description", "methode", "outils"]
                            }
                        }
                    },
                    "required": ["id", "titre", "tests"]
                }
            },
            "erreur": {"type": ["string", "null"]}
        },
        "required": ["criteres"]
    },
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
def rgaa_checklist(themes: list[int] = None, criteres: list[str] = None) -> dict:
    """
    Génère une checklist de test manuel RGAA.

    Args:
        themes: Liste de thèmes (ex: [1, 6, 11])
        criteres: Liste d'identifiants de critères (ex: ["1.1", "6.1"])
        Au moins un des deux paramètres est requis.

    Returns:
        {"criteres": [{"id": "...", "titre": "...", "tests": [...]}]}
    """
    if not themes and not criteres:
        raise ToolError(
            "Au moins un paramètre est requis : themes ou criteres. "
            "Exemples : themes=[1, 6, 11] ou criteres=['1.1', '6.1']."
        )

    cache = charger_cache()

    # Valider les thèmes
    if themes:
        validate_themes(themes)

    # Valider les critères
    if criteres:
        invalid_criteres = [c for c in criteres if c not in cache["criteres"]]
        if invalid_criteres:
            raise ToolError(
                f"Critères invalides : {invalid_criteres}. "
                f"Utilise rgaa_lister_criteres() pour voir les IDs valides."
            )

    ids_cibles = set()

    if themes:
        for c in cache["criteres"].values():
            if c["theme"] in themes:
                ids_cibles.add(c["id"])

    if criteres:
        ids_cibles.update(criteres)

    result = []
    for cid in sorted(ids_cibles, key=lambda x: [int(p) for p in x.split(".")]):
        c = cache["criteres"].get(cid)
        if not c:
            continue
        outils = OUTILS_CHECKLIST.get(c["theme"], ["DevTools"])
        tests_raw = c.get("tests", {})
        if isinstance(tests_raw, dict):
            tests_list = [v[0] if isinstance(v, list) and v else str(v) for v in tests_raw.values()]
        elif isinstance(tests_raw, list):
            tests_list = [str(t) for t in tests_raw]
        else:
            tests_list = [str(tests_raw)]

        tests = [
            {
                "description": t,
                "methode": "Inspecter manuellement avec les outils ci-dessous",
                "outils": outils,
            }
            for t in tests_list if t
        ] or [{"description": "Vérifier la conformité selon le critère", "methode": "Inspection manuelle", "outils": outils}]

        result.append({"id": cid, "titre": c["titre"], "tests": tests})

    return {"criteres": result}


# ============================================================================
# OUTILS : Reporting
# ============================================================================

@mcp.tool(
    output_schema={
        "type": "object",
        "properties": {
            "taux": {"type": "number"},
            "nb_conformes": {"type": "integer"},
            "nb_non_conformes": {"type": "integer"},
            "nb_non_applicables": {"type": "integer"},
            "criteres_evalues": {"type": "integer"},
            "erreur": {"type": ["string", "null"]}
        },
        "required": ["taux", "nb_conformes", "nb_non_conformes", "nb_non_applicables", "criteres_evalues"]
    },
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
def rgaa_taux_conformite(resultats: dict) -> dict:
    """
    Calcule le taux de conformité RGAA selon la formule officielle.

    Formule : C / (C + NC) × 100  (les NA sont exclus du calcul)

    Args:
        resultats: Dict {id_critere: statut} avec statuts "C", "NC", ou "NA"
                   Exemple: {"1.1": "C", "1.2": "NC", "1.3": "NA"}

    Returns:
        {"taux": float, "nb_conformes": int, "nb_non_conformes": int, "nb_non_applicables": int, "criteres_evalues": int}
    """
    if not resultats:
        raise ToolError(
            "Les résultats d'audit ne peuvent pas être vides. "
            "Fournis un dictionnaire avec au moins un critère et son statut (C, NC ou NA). "
            "Exemple : {'1.1': 'C', '1.2': 'NC', '1.3': 'NA'}."
        )

    valides = {"C", "NC", "NA"}
    invalid_statuts = []
    for cid, statut in resultats.items():
        if statut not in valides:
            invalid_statuts.append((cid, statut))

    if invalid_statuts:
        all_details = ", ".join([f"'{cid}': '{statut}'" for cid, statut in invalid_statuts])
        raise ToolError(
            f"Statuts invalides : {all_details}. "
            f"Les statuts acceptés sont uniquement : C (conforme), NC (non-conforme), NA (non-applicable)."
        )

    nb_c = sum(1 for s in resultats.values() if s == "C")
    nb_nc = sum(1 for s in resultats.values() if s == "NC")
    nb_na = sum(1 for s in resultats.values() if s == "NA")
    evalues = nb_c + nb_nc
    taux = round(nb_c / evalues * 100, 2) if evalues > 0 else 0.0

    return {
        "taux": taux,
        "nb_conformes": nb_c,
        "nb_non_conformes": nb_nc,
        "nb_non_applicables": nb_na,
        "criteres_evalues": evalues,
    }


# ============================================================================
# PROMPTS MCP
# ============================================================================

@mcp.prompt()
def audit_page(url: str, themes: str = "") -> str:
    """
    Template pour auditer une page web avec le MCP RGAA.

    Args:
        url: URL de la page à auditer
        themes: Thèmes à cibler, séparés par virgule (ex: "1,6,11"). Vide = tous.
    """
    themes_str = f"en ciblant les thèmes {themes}" if themes else "sur tous les thèmes automatisables"
    themes_param = f", themes=[{themes}]" if themes else ""
    return f"""Tu es un expert en accessibilité numérique RGAA 4.2.1.

Effectue un audit de la page {url} {themes_str}.

Étapes :
1. Utilise `rgaa_analyser` avec l'URL {url}{themes_param} pour obtenir les violations automatiques détectées.
2. Pour chaque thème avec des violations, utilise `rgaa_checklist` pour obtenir les tests manuels complémentaires.
3. Pour les critères NC, utilise `rgaa_obtenir_critere` si tu as besoin du détail (tests précis, références WCAG).
4. Si Playwright MCP est disponible dans la session, utilise-le pour analyser le DOM rendu (focus visible, contrastes, comportements dynamiques).
5. Synthétise les résultats dans un rapport structuré avec : résumé exécutif, violations par thème, recommandations prioritaires.

Commence par lancer l'analyse automatique."""


@mcp.prompt()
def rapport_audit(resultats: str) -> str:
    """
    Template pour générer un rapport d'audit RGAA structuré.

    Args:
        resultats: Résultats d'audit au format JSON ou description textuelle
    """
    return f"""Tu es un expert en accessibilité numérique RGAA 4.2.1.

Génère un rapport d'audit complet au format Markdown à partir des résultats suivants :

{resultats}

Structure du rapport :
1. **Résumé exécutif** — taux de conformité, nombre de critères C/NC/NA, point clé
2. **Violations par thème** — pour chaque thème NC : critère, impact utilisateur, élément(s) concerné(s)
3. **Recommandations prioritaires** — top 5 corrections à fort impact, avec exemple de code corrigé si pertinent
4. **Méthode** — préciser que l'analyse automatique couvre ~57% des critères et qu'un audit manuel complet est recommandé

Utilise `rgaa_taux_conformite` si tu as le détail C/NC/NA par critère pour calculer le taux officiel.
Utilise `rgaa_obtenir_critere` pour enrichir les descriptions avec les références WCAG officielles."""


@mcp.prompt()
def expliquer_critere(id_critere: str) -> str:
    """
    Template pour expliquer un critère RGAA et comment le tester.

    Args:
        id_critere: Identifiant du critère (ex: "1.1", "11.3")
    """
    return f"""Tu es un expert en accessibilité numérique RGAA 4.2.1.

Explique le critère RGAA {id_critere} de façon pédagogique.

Étapes :
1. Utilise `rgaa_obtenir_critere` avec l'id "{id_critere}" pour obtenir le détail complet.
2. Si des termes techniques apparaissent dans les tests ou cas particuliers, utilise `rgaa_glossaire` pour les définir.
3. Présente une explication structurée :
   - **Objectif** — pourquoi ce critère existe et quel problème d'accessibilité il adresse
   - **Qui est impacté** — profils d'utilisateurs concernés (non-voyants, moteur, cognitif…)
   - **Comment tester** — étapes concrètes avec les outils recommandés
   - **Exemple conforme / non conforme** — code HTML si pertinent
   - **Références WCAG** — critères WCAG correspondants et leur niveau"""


@mcp.prompt()
def criteres_par_sujet(sujet: str, niveau: str = "A") -> str:
    """
    Template pour lister les critères RGAA liés à un sujet, filtrés par niveau WCAG.

    Args:
        sujet: Mot-clé du sujet (ex: "images", "formulaires", "couleurs")
        niveau: Niveau WCAG à cibler : "A", "AA" ou "AAA" (défaut : "A")
    """
    return f"""Tu es un expert en accessibilité numérique RGAA 4.2.1.

Liste les critères RGAA de niveau {niveau} liés à "{sujet}".

Étapes :
1. Utilise `rgaa_chercher` avec la query "{sujet}" pour trouver les critères correspondants.
2. Utilise `rgaa_lister_criteres` avec niveau_wcag="{niveau}" pour obtenir tous les critères de ce niveau.
3. Croise les deux résultats pour ne garder que les critères de niveau {niveau} en rapport avec "{sujet}".
4. Pour chaque critère retenu, utilise `rgaa_obtenir_critere` si tu as besoin du détail.
5. Présente les résultats sous forme de tableau : **ID**, **Titre**, **Thème**, avec une brève explication de pourquoi ce critère concerne "{sujet}"."""


@mcp.prompt()
def checklist_audit(themes: str) -> str:
    """
    Template pour générer une checklist de tests manuels par thèmes.

    Args:
        themes: Noms ou numéros de thèmes séparés par virgule (ex: "formulaires, navigation" ou "11,12")
    """
    return f"""Tu es un expert en accessibilité numérique RGAA 4.2.1.

Génère une checklist d'audit manuel pour les thèmes : {themes}.

Étapes :
1. Identifie les numéros de thèmes RGAA correspondant à "{themes}" :
   - Si des noms sont fournis, utilise `rgaa_statistiques` pour obtenir la liste des thèmes et leur numéro.
   - Si des numéros sont fournis, utilise-les directement.
2. Utilise `rgaa_checklist` avec la liste de ces numéros pour obtenir les tests détaillés.
3. Présente la checklist sous forme exploitable pour un audit terrain :
   - Pour chaque critère : **ID**, **Titre**, procédure de test, outils recommandés
   - Regroupe par thème
   - Indique en fin de checklist les outils globaux nécessaires pour l'ensemble de l'audit."""


@mcp.prompt()
def criteres_wcag(niveau_wcag: str = "AA") -> str:
    """
    Template pour lister les critères RGAA correspondant à un niveau WCAG.

    Args:
        niveau_wcag: Niveau WCAG cible : "A", "AA" ou "AAA" (défaut : "AA")
    """
    return f"""Tu es un expert en accessibilité numérique RGAA 4.2.1.

Liste tous les critères RGAA qui correspondent au niveau WCAG {niveau_wcag}.

Étapes :
1. Utilise `rgaa_lister_criteres` avec niveau_wcag="{niveau_wcag}" pour obtenir la liste complète.
2. Regroupe les critères par thème pour une lecture claire.
3. Présente un tableau synthétique : **Thème**, **ID**, **Titre**, avec le ou les critères WCAG {niveau_wcag} associés.
4. Conclus avec le total de critères {niveau_wcag} et la proportion automatisable vs manuelle."""


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


@mcp.prompt()
def plan_correction(violations: str) -> str:
    """
    Template pour générer un plan de correction priorisé à partir de violations RGAA.

    Args:
        violations: Liste de critères NC au format JSON ou description textuelle
    """
    return f"""Tu es un expert en accessibilité numérique RGAA 4.2.1.

Génère un plan de correction priorisé pour les violations RGAA suivantes :

{violations}

Étapes :
1. Pour chaque critère NC listé, utilise `rgaa_obtenir_critere` pour récupérer le titre, les tests et les références WCAG.
2. Classe les violations par niveau d'impact utilisateur :
   - **Bloquant** — empêche complètement l'accès pour certains profils (non-voyants, moteur…)
   - **Majeur** — gêne significative et contournement difficile
   - **Mineur** — gêne mais contournement possible
3. Pour chaque violation, fournis :
   - **Critère RGAA** — ID et titre
   - **Impact** — profils d'utilisateurs affectés
   - **Correction** — étapes concrètes avec exemple de code HTML/CSS si pertinent
   - **Effort estimé** — Faible / Modéré / Fort
4. Présente le plan sous forme de backlog priorisé, du plus impactant au moins impactant.
5. Conclus avec l'estimation du taux de conformité RGAA une fois toutes les corrections appliquées (utilise `rgaa_taux_conformite` si tu as les données C/NC/NA)."""


@mcp.prompt()
def formuler_exigences(contexte: str) -> str:
    """
    Template pour formuler des exigences d'accessibilité pour un projet.

    Args:
        contexte: Description du projet (ex: "Application mobile bancaire", "Site intranet RH")
    """
    return f"""Tu es un expert en accessibilité numérique RGAA 4.2.1.

Formule les exigences d'accessibilité pour le projet suivant : {contexte}

Étapes :
1. Utilise `rgaa_statistiques()` pour avoir une vue d'ensemble des 106 critères RGAA et leur répartition par thème.
2. Utilise `rgaa_types_audit()` pour identifier le type d'audit adapté au contexte et l'obligation légale applicable.
3. Identifie les thèmes RGAA particulièrement critiques pour ce type de projet :
   - Pour un contexte web : thèmes 1 (Images), 3 (Couleurs), 8 (Obligatoires), 11 (Formulaires), 12 (Navigation)
   - Adapte selon {contexte}
4. Pour les thèmes critiques, utilise `rgaa_lister_criteres` pour lister les critères niveau A et AA.
5. Structure les exigences en 3 catégories :
   - **Exigences légales** — critères RGAA obligatoires selon le statut de l'organisation
   - **Exigences de base** — critères niveau A incontournables pour l'accès
   - **Exigences de qualité** — critères niveau AA recommandés pour une bonne expérience

Format de sortie : document d'exigences Markdown prêt à intégrer dans un cahier des charges."""




# ============================================================================
# Ressources MCP
# ============================================================================

_routes_mod.register_version_resource(mcp, charger_cache)


@mcp.resource("rgaa://criteres/{critere_id}")
async def resource_critere(critere_id: str) -> str:
    """Détail complet d'un critère RGAA (même données que rgaa_obtenir_critere)."""
    cache = charger_cache()
    critere = cache["criteres"].get(critere_id)
    if critere is None:
        return json.dumps({"erreur": f"Critère '{critere_id}' introuvable"}, ensure_ascii=False)
    return json.dumps(critere, ensure_ascii=False, indent=2)


@mcp.resource("rgaa://index")
async def resource_index() -> str:
    """Index léger de tous les critères RGAA (id, thème, titre, niveau)."""
    cache = charger_cache()
    index = [
        {
            "id": c["id"],
            "theme": c["theme"],
            "titre": c["titre"],
            "niveau": c.get("niveau"),
            "automatisable": c["automatisable"],
        }
        for c in cache["criteres"].values()
    ]
    return json.dumps(index, ensure_ascii=False, indent=2)


@mcp.resource("rgaa://metadata")
async def resource_metadata() -> str:
    """Métadonnées du référentiel RGAA (langues, source, statistiques)."""
    cache = charger_cache()
    criteres = cache.get("criteres", {})
    meta = cache.get("meta", {})
    themes = cache.get("themes", {})
    nb_auto = sum(1 for c in criteres.values() if c.get("automatisable"))
    taux = round(nb_auto / len(criteres) * 100, 1) if criteres else 0.0
    return json.dumps({
        "languages": ["fr"],
        "versions": [meta.get("version", "inconnue")],
        "source": "https://github.com/DISIC/RGAA",
        "updated_at": meta.get("updated_at", "inconnue"),
        "nb_criteres": len(criteres),
        "nb_themes": len(themes),
        "taux_automatisable": taux,
    }, ensure_ascii=False, indent=2)



# ============================================================================
# Entrypoint
# ============================================================================

if __name__ == "__main__":
    _cache = charger_cache()
    logger.info("Serveur MCP RGAA v%s", VERSION)
    logger.info("Cache: %d critères", len(_cache.get("criteres", {})))
    factory.run_main(mcp, VERSION, "RGAA MCP", charger_cache, "criteres", TOKENS_FILE)
