"""
Serveur MCP pour le référentiel GreenIT
Connecte Claude aux bonnes pratiques web écologiques

API GreenIT: https://rweb.greenit.fr/api
- GET /api/languages
- GET /api/versions
- GET /api/fiches?lang=fr&version=latest
- GET /api/fiches/{id}?lang=fr&version=latest

Variables d'environnement:
  MCP_TRANSPORT  stdio (défaut) | http
  MCP_HOST       0.0.0.0 (défaut, mode http)
  MCP_PORT       8000 (défaut, mode http)

Gestion des tokens (fichier tokens.json):
  --generate-token --name <nom> [--expires-days <N>]  Créer un token (défaut: 365 jours)
  --list-tokens                                        Lister les tokens actifs
  --revoke-token <token>                               Révoquer un token
"""

from fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations
import json
import logging
import os
import sys
from pathlib import Path
from typing import Optional, List, Any

# Modules extraits
from data import (
    charger_cache, sauvegarder_cache,
    CACHE_FILE, calculer_ecoindex as _calculer_ecoindex_impl,
    compter_fiches, compter_lifecycles, compter_ressources, calculer_taux_ecoindex_moyen
)
from mcp_ref_core._helpers import validate_themes, validate_score_range, validate_nonnegative
from mcp_ref_core import routes, factory

# Re-export helper functions from routes for backward compatibility with tests
_get_base_url = routes._get_base_url
_get_token_request_url = routes._get_token_request_url
_http_homepage = routes._http_homepage
_http_install_script = routes._http_install_script
_http_guide = routes._http_guide

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
    stream=sys.stderr,
)
logger = logging.getLogger("greenit-mcp")

VERSION = "2.1.3"

_BASE_DIR = Path(__file__).parent
TOKENS_FILE = str(_BASE_DIR.parent / "tokens" / "tokens.json")
GREENIT_API_URL = "https://rweb.greenit.fr/api"

routes._VERSION = VERSION
routes._REFERENTIEL_VERSION = charger_cache().get("meta", {}).get("version", "")
routes._MCP_NAME = "GreenIT MCP"
routes._MCP_ID = "greenit"
routes._ITEMS_KEY = "fiches"
routes._LOGO = "🌱"
routes._ACCENT = "#22c55e"
routes._ACCENT_DARK = "#14532d"
routes._ACCENT_LIGHT = "#4ade80"
routes._ACCENT_BTN_TEXT = "#000"
routes._TAGLINE = "Bonnes pratiques d'écoconception web"

def _greenit_tool_definitions() -> list[dict[str, Any]]:
    """Build tool definitions from tools descriptions and parameter schemas.

    Returns:
        list[dict[str, Any]]: Tool definitions with required fields (name, description, inputSchema)
    """
    tool_defs = [
        {
            "name": "greenit_lister_fiches",
            "description": "Liste toutes les fiches ou filtre par lifecycle, ressource, impact, priorité",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "lifecycle": {"type": ["string", "null"], "description": "Filtrer par phase du cycle de vie"},
                    "saved_resource": {"type": ["string", "null"], "description": "Filtrer par ressource économisée"},
                    "impact_min": {"type": ["integer", "null"], "description": "Impact environnemental minimum (1-5)"},
                    "priorite_min": {"type": ["integer", "null"], "description": "Priorité d'implémentation minimum (1-5)"}
                }
            }
        },
        {
            "name": "greenit_fiches_prioritaires",
            "description": "Retourne les fiches à fort impact et haute priorité",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "impact_min": {"type": ["integer", "null"], "description": "Seuil minimum d'impact (défaut: 4)"},
                    "priorite_min": {"type": ["integer", "null"], "description": "Seuil minimum de priorité (défaut: 4)"}
                }
            }
        },
        {
            "name": "greenit_chercher_fiche",
            "description": "Recherche des fiches par mot-clé avec scoring de pertinence",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "terme": {"type": "string", "description": "Mot-clé à rechercher"}
                },
                "required": ["terme"]
            }
        },
        {
            "name": "greenit_comparer_fiches",
            "description": "Compare plusieurs fiches côte à côte avec recommandation",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "fiche_ids": {"type": "array", "items": {"type": "string"}, "description": "Liste d'identifiants de fiches à comparer"}
                },
                "required": ["fiche_ids"]
            }
        },
        {
            "name": "greenit_obtenir_fiche_complete",
            "description": "Récupère le contenu complet d'une fiche",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "fiche_id": {"type": "string", "description": "Identifiant de la fiche"}
                },
                "required": ["fiche_id"]
            }
        },
        {
            "name": "greenit_obtenir_statistiques",
            "description": "Statistiques du référentiel (distributions, top fiches)",
            "inputSchema": {
                "type": "object",
                "properties": {}
            }
        },
        {
            "name": "greenit_lister_lifecycles",
            "description": "Liste les 7 phases du cycle de vie avec nombre de fiches",
            "inputSchema": {
                "type": "object",
                "properties": {}
            }
        },
        {
            "name": "greenit_lister_ressources",
            "description": "Liste les 8 types de ressources avec nombre de fiches",
            "inputSchema": {
                "type": "object",
                "properties": {}
            }
        },
        {
            "name": "greenit_calculer_ecoindex",
            "description": "Calcule l'EcoIndex (score + grade) à partir des 3 métriques brutes : nœuds DOM, requêtes HTTP, taille KB",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "dom_nodes": {"type": "integer", "description": "Nombre de nœuds DOM"},
                    "requests": {"type": "integer", "description": "Nombre de requêtes HTTP"},
                    "size_kb": {"type": "number", "description": "Taille totale en kilo-octets"},
                    "url": {"type": ["string", "null"], "description": "URL de la page mesurée (optionnel)"}
                },
                "required": ["dom_nodes", "requests", "size_kb"]
            }
        }
    ]

    for tool in tool_defs:
        assert "name" in tool, f"Tool missing 'name': {tool}"
        assert "description" in tool, f"Tool missing 'description': {tool}"
        assert "inputSchema" in tool, f"Tool missing 'inputSchema': {tool}"

    return tool_defs


def _greenit_guide_extra_sections() -> str:
    return """
    <h2>5. Prompts MCP</h2>
    <p>Ces prompts sont des workflows préconfigurés invocables directement depuis Claude&nbsp;Code avec <code>/mcp__greenit__&lt;nom&gt;</code>.</p>
    <table>
      <thead><tr><th>Prompt</th><th>Paramètres</th><th>Description</th></tr></thead>
      <tbody>
        <tr><td><code>audit_ecoindex</code></td><td><code>url</code>, <code>focus?</code></td><td>Analyse l'impact environnemental d'une page via EcoIndex</td></tr>
        <tr><td><code>rapport_impact</code></td><td><code>resultats</code></td><td>Rapport d'impact environnemental structuré à partir de résultats d'analyse</td></tr>
        <tr><td><code>expliquer_fiche</code></td><td><code>fiche_id</code></td><td>Explication pédagogique d'une fiche (objectif, mise en œuvre, exemples)</td></tr>
        <tr><td><code>fiches_par_lifecycle</code></td><td><code>phase</code>, <code>impact_min?</code></td><td>Bonnes pratiques pour une phase du cycle de vie (ex : développement)</td></tr>
        <tr><td><code>checklist_ecoindex</code></td><td><code>domaines?</code></td><td>Checklist d'optimisation manuelle par domaine</td></tr>
        <tr><td><code>ressources_comparaison</code></td><td><code>fiche_ids</code></td><td>Comparaison des économies de ressources entre plusieurs fiches</td></tr>
        <tr><td><code>audit_rapide_greenit</code></td><td><code>url</code></td><td>Audit express — bonnes pratiques prioritaires en 5 minutes</td></tr>
        <tr><td><code>audit_par_ressource</code></td><td><code>ressource</code>, <code>budget?</code></td><td>Optimisation par type de ressource (réseau, CPU, mémoire…)</td></tr>
      </tbody>
    </table>

    <h2>6. Ressources disponibles</h2>
    <p>Les ressources MCP exposent les données brutes du référentiel, accessibles directement dans Claude :</p>
    <table>
      <thead><tr><th>Ressource</th><th>Description</th></tr></thead>
      <tbody>
        <tr><td><code>greenit://version</code></td><td>Version du serveur et des données</td></tr>
        <tr><td><code>greenit://index</code></td><td>Index de toutes les fiches (id, titre, lifecycle, impact, priorité)</td></tr>
        <tr><td><code>greenit://fiche/{fiche_id}</code></td><td>Contenu complet d'une fiche spécifique (ex : <code>RWEB_0051</code>)</td></tr>
        <tr><td><code>greenit://metadata</code></td><td>Métadonnées du référentiel (source, nb fiches, nb lifecycles)</td></tr>
      </tbody>
    </table>

    <h2>7. Exemples de questions</h2>
    <div class="note">Quelles fiches GreenIT sont prioritaires pour un site React ?</div>
    <div class="note">Quelles bonnes pratiques pour réduire les requêtes réseau ?</div>
    <div class="note">Quelles bonnes pratiques GreenIT s'appliquent à la phase de développement ?</div>
    <div class="note">Compare les fiches RWEB_0049 et RWEB_0051</div>
    <div class="note">Compare les fiches RWEB_0042 et RWEB_0050 : laquelle prioriser pour un site e-commerce ?</div>
    <div class="note">Donne-moi les statistiques du référentiel GreenIT</div>
    <div class="note">Donne-moi les bonnes pratiques GreenIT à appliquer en priorité pour réduire l'impact écologique de mon site (ex : https://example.com) — utilise Playwright avec Chromium pour mesurer les métriques DOM, requêtes et poids de page</div>
    <div class="note">J'ai mesuré avec Playwright : 450 nœuds DOM, 38 requêtes, 280 Ko — quel est l'EcoIndex de ma page ?</div>
    <div class="note">Calcule l'EcoIndex de https://example.com en utilisant Playwright pour mesurer les métriques réelles de la page</div>

    <h2>8. Calculer l'EcoIndex</h2>
    <p>L'EcoIndex est calculé à partir de 3 métriques mesurées avec Playwright :</p>
    <div class="note">Le serveur MCP pilote automatiquement Playwright en appliquant le protocole de mesure officiel EcoIndex. Il vous suffit de fournir une URL — Claude se charge du reste.</div>
    <table>
      <thead><tr><th>Paramètre</th><th>Description</th></tr></thead>
      <tbody>
        <tr><td><code>dom_nodes</code></td><td>Nombre de nœuds dans le DOM</td></tr>
        <tr><td><code>requests</code></td><td>Nombre de requêtes HTTP</td></tr>
        <tr><td><code>size_kb</code></td><td>Taille totale transférée en Ko</td></tr>
      </tbody>
    </table>
    <p>Protocole de mesure recommandé avec Playwright :</p>
    <pre><code>1. Ouvrir un contexte Playwright avec viewport 1920×1080 (spec EcoIndex officielle)
2. Naviguer vers la page
3. Attendre 3 secondes
4. Faire défiler jusqu'en bas progressivement
5. Attendre 3 secondes
6. Mesurer DOM, requêtes, taille
7. Appeler greenit_calculer_ecoindex(dom_nodes, requests, size_kb)</code></pre>
    <table>
      <thead><tr><th>Grade</th><th>Score</th></tr></thead>
      <tbody>
        <tr><td><span style="display:inline-block;width:14px;height:14px;border-radius:3px;background:#349A47;vertical-align:middle;margin-right:6px"></span>A</td><td>&gt; 80</td></tr>
        <tr><td><span style="display:inline-block;width:14px;height:14px;border-radius:3px;background:#51B84B;vertical-align:middle;margin-right:6px"></span>B</td><td>70 – 80</td></tr>
        <tr><td><span style="display:inline-block;width:14px;height:14px;border-radius:3px;background:#CADB2A;vertical-align:middle;margin-right:6px"></span>C</td><td>55 – 70</td></tr>
        <tr><td><span style="display:inline-block;width:14px;height:14px;border-radius:3px;background:#F6EB15;vertical-align:middle;margin-right:6px"></span>D</td><td>40 – 55</td></tr>
        <tr><td><span style="display:inline-block;width:14px;height:14px;border-radius:3px;background:#FECD06;vertical-align:middle;margin-right:6px"></span>E</td><td>25 – 40</td></tr>
        <tr><td><span style="display:inline-block;width:14px;height:14px;border-radius:3px;background:#F99839;vertical-align:middle;margin-right:6px"></span>F</td><td>10 – 25</td></tr>
        <tr><td><span style="display:inline-block;width:14px;height:14px;border-radius:3px;background:#ED2124;vertical-align:middle;margin-right:6px"></span>G</td><td>0 – 10</td></tr>
      </tbody>
    </table>"""


mcp = factory.create_mcp(
    "GreenIT-Referentiel",
    TOKENS_FILE,
    _greenit_tool_definitions,
    _greenit_guide_extra_sections,
)


# ============================================================================
# RESSOURCES: Données statiques par URI
# ============================================================================

@mcp.resource("greenit://fiche/{fiche_id}")
async def obtenir_fiche(fiche_id: str) -> str:
    """Récupère une fiche spécifique."""
    fiches = charger_cache().get("fiches", {})

    if fiche_id in fiches:
        return json.dumps(fiches[fiche_id], ensure_ascii=False, indent=2)

    return json.dumps({"erreur": f"Fiche '{fiche_id}' non trouvée"}, ensure_ascii=False)


@mcp.resource("greenit://index")
async def index_fiches() -> str:
    """Liste toutes les fiches disponibles."""
    fiches = charger_cache().get("fiches", {})

    categories = set()
    for fiche in fiches.values():
        for r in fiche.get("saved_resources", []):
            categories.add(r)
        if fiche.get("lifecycle"):
            categories.add(fiche["lifecycle"])
        for criterion in fiche.get("criteria", []):
            if "criterium" in criterion:
                categories.add(criterion["criterium"])

    index = {
        "total": len(fiches),
        "fiches": [
            {
                "id": fiche_id,
                "num": fiche.get("num"),
                "title": fiche.get("title"),
                "description": fiche.get("shortDescription", "")[:200]
            }
            for fiche_id, fiche in sorted(fiches.items())
        ],
        "categories": sorted(list(categories))
    }
    return json.dumps(index, ensure_ascii=False, indent=2)


@mcp.resource("greenit://metadata")
async def obtenir_metadata() -> str:
    """Récupère les métadonnées du référentiel avec statistiques calculées."""
    meta = charger_cache().get("meta", {})
    return json.dumps({
        "source": "https://github.com/greenit-apps/greenit-data",
        "updated_at": meta.get("updated_at", "inconnue"),
        "nb_fiches": compter_fiches(),
        "nb_lifecycles": compter_lifecycles(),
        "nb_ressources": compter_ressources(),
        "taux_ecoindex_moyen": calculer_taux_ecoindex_moyen(),
    }, ensure_ascii=False, indent=2)


routes.register_version_resource(mcp, charger_cache)


# ============================================================================
# OUTILS: Actions que Claude peut effectuer
# ============================================================================

@mcp.tool(
    description="Liste les fiches du référentiel GreenIT avec filtres optionnels",
    annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True),
    output_schema={
        "type": "object",
        "properties": {
            "fiches": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string", "description": "Identifiant unique de la fiche"},
                        "num": {"type": "string", "description": "Numéro de la fiche"},
                        "titre": {"type": "string", "description": "Titre de la fiche"},
                        "environmental_impact": {"type": "integer", "description": "Score d'impact environnemental (1-5)"},
                        "priority_implementation": {"type": "integer", "description": "Priorité d'implémentation (1-5)"},
                        "lifecycle": {"type": "string", "description": "Phase du cycle de vie"},
                        "saved_resources": {"type": "array", "items": {"type": "string"}, "description": "Ressources économisées"}
                    }
                }
            }
        }
    }
)
def greenit_lister_fiches(
    lifecycle: Optional[str] = None,
    saved_resource: Optional[str] = None,
    impact_min: Optional[int] = None,
    priorite_min: Optional[int] = None,
) -> dict:
    """
    Liste les fiches du référentiel GreenIT avec filtres optionnels.

    Args:
        lifecycle: Filtrer par phase (ex: "3-developement", "2-conception")
        saved_resource: Filtrer par ressource économisée (ex: "network", "cpu", "requests")
        impact_min: Impact environnemental minimum (1-5)
        priorite_min: Priorité d'implémentation minimum (1-5)

    Returns:
        Liste allégée des fiches (id, titre, impact, priorité, lifecycle, ressources) — utiliser obtenir_fiche_complete pour le détail
    """
    try:
        # Validate impact_min parameter
        if impact_min is not None:
            validate_score_range(impact_min, 1, 5, "impact_min")

        # Validate priorite_min parameter
        if priorite_min is not None:
            validate_score_range(priorite_min, 1, 5, "priorite_min")

        fiches = charger_cache().get("fiches", {})
        resultats = []

        for fiche_id, fiche in fiches.items():
            if lifecycle and fiche.get("lifecycle") != lifecycle:
                continue
            if saved_resource and saved_resource not in fiche.get("saved_resources", []):
                continue
            if impact_min and fiche.get("environmental_impact", 0) < impact_min:
                continue
            if priorite_min and fiche.get("priority_implementation", 0) < priorite_min:
                continue

            resultats.append({
                "id": fiche_id,
                "num": fiche.get("num"),
                "titre": fiche.get("title"),
                "environmental_impact": fiche.get("environmental_impact"),
                "priority_implementation": fiche.get("priority_implementation"),
                "lifecycle": fiche.get("lifecycle"),
                "saved_resources": fiche.get("saved_resources", []),
            })

        return {"fiches": resultats}
    except ToolError:
        raise  # Re-raise ToolError as-is
    except Exception as e:
        raise ToolError(f"Erreur lors du listage des fiches. Détail: {str(e)}")


@mcp.tool(
    description="Retourne les fiches à fort impact et haute priorité d'implémentation",
    annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True),
    output_schema={
        "type": "object",
        "properties": {
            "fiches": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "num": {"type": "string"},
                        "titre": {"type": "string"},
                        "description": {"type": "string"},
                        "environmental_impact": {"type": "integer"},
                        "priority_implementation": {"type": "integer"},
                        "score": {"type": "integer"},
                        "lifecycle": {"type": "string"},
                        "saved_resources": {"type": "array", "items": {"type": "string"}},
                        "url": {"type": "string"}
                    }
                }
            }
        }
    }
)
def greenit_fiches_prioritaires(
    impact_min: int = 4,
    priorite_min: int = 4,
) -> dict:
    """
    Retourne les fiches à fort impact et haute priorité d'implémentation.

    Args:
        impact_min: Seuil minimum d'impact environnemental (défaut: 4/5)
        priorite_min: Seuil minimum de priorité d'implémentation (défaut: 4/5)

    Returns:
        Fiches triées par score combiné (impact + priorité) décroissant
    """
    try:
        # Validate impact_min parameter
        validate_score_range(impact_min, 1, 5, "impact_min")

        # Validate priorite_min parameter
        validate_score_range(priorite_min, 1, 5, "priorite_min")

        fiches = charger_cache().get("fiches", {})
        resultats = []

        for fiche_id, fiche in fiches.items():
            ei = fiche.get("environmental_impact", 0)
            pi = fiche.get("priority_implementation", 0)
            if ei >= impact_min and pi >= priorite_min:
                resultats.append({
                    "id": fiche_id,
                    "num": fiche.get("num"),
                    "titre": fiche.get("title"),
                    "description": fiche.get("shortDescription", "")[:300],
                    "environmental_impact": ei,
                    "priority_implementation": pi,
                    "score": ei + pi,
                    "lifecycle": fiche.get("lifecycle"),
                    "saved_resources": fiche.get("saved_resources", []),
                    "url": fiche.get("url", ""),
                })

        resultats.sort(key=lambda x: x["score"], reverse=True)
        return {"fiches": resultats}
    except ToolError:
        raise  # Re-raise ToolError as-is
    except Exception as e:
        raise ToolError(f"Erreur lors de la récupération des fiches prioritaires. Détail: {str(e)}")


@mcp.tool(
    description="Recherche des fiches par mot-clé avec scoring par pertinence",
    annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=True),
    output_schema={
        "type": "object",
        "properties": {
            "fiches": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "num": {"type": "string"},
                        "titre": {"type": "string"},
                        "apercu": {"type": "string"},
                        "environmental_impact": {"type": "integer"},
                        "priority_implementation": {"type": "integer"},
                        "pertinence": {"type": "integer"}
                    }
                }
            }
        }
    }
)
def greenit_chercher_fiche(terme: str) -> dict:
    """
    Recherche des fiches par mot-clé avec scoring par pertinence.

    Args:
        terme: Mot-clé à rechercher dans les titres, descriptions et tags

    Returns:
        Fiches correspondantes triées par pertinence décroissante (max 15)
    """
    try:
        # Validate terme parameter
        if not terme or not terme.strip():
            raise ToolError("Les paramètres fournis sont invalides. `terme` ne peut pas être vide. Fournissez un terme de recherche valide.")

        fiches = charger_cache().get("fiches", {})
        resultats = []
        terme_lower = terme.lower()

        for fiche_id, fiche in fiches.items():
            titre = fiche.get("title", "").lower()
            short_desc = fiche.get("shortDescription", "").lower()
            long_desc = fiche.get("description", "").lower()
            resources = " ".join(fiche.get("saved_resources", [])).lower()
            lifecycle = fiche.get("lifecycle", "").lower()

            score = 0
            if terme_lower in titre:
                score += 10
            if terme_lower in short_desc:
                score += 5
            if terme_lower in long_desc:
                score += 3
            if terme_lower in resources:
                score += 2
            if terme_lower in lifecycle:
                score += 1

            if score > 0:
                resultats.append({
                    "id": fiche_id,
                    "num": fiche.get("num"),
                    "titre": fiche.get("title"),
                    "apercu": fiche.get("shortDescription", "")[:200],
                    "environmental_impact": fiche.get("environmental_impact"),
                    "priority_implementation": fiche.get("priority_implementation"),
                    "pertinence": score,
                })

        resultats.sort(key=lambda x: x["pertinence"], reverse=True)
        return {"fiches": resultats[:15]}
    except ToolError:
        raise  # Re-raise ToolError as-is
    except Exception as e:
        raise ToolError(f"Erreur lors de la recherche. Détail: {str(e)}")


@mcp.tool(
    description="Compare plusieurs fiches côte à côte avec recommandation",
    annotations=ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True
    ),
    output_schema={
        "type": "object",
        "properties": {
            "comparaison": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "num": {"type": "string"},
                        "titre": {"type": "string"},
                        "description": {"type": "string"},
                        "environmental_impact": {"type": "integer"},
                        "priority_implementation": {"type": "integer"},
                        "score_combined": {"type": "integer"},
                        "lifecycle": {"type": "string"},
                        "saved_resources": {"type": "array", "items": {"type": "string"}},
                        "url": {"type": "string"}
                    }
                }
            },
            "recommandation": {
                "type": "object",
                "properties": {
                    "priorite_1": {"type": "string"},
                    "classement": {"type": "array", "items": {"type": "string"}},
                    "note": {"type": "string"}
                }
            }
        }
    }
)
def greenit_comparer_fiches(fiche_ids: List[str]) -> dict:
    """
    Compare plusieurs fiches côte à côte.

    Args:
        fiche_ids: Liste d'identifiants de fiches à comparer (ex: ["RWEB_0049", "RWEB_0051"])

    Returns:
        Matrice comparative avec scores, lifecycle, ressources économisées et recommandation
    """
    try:
        # Validate fiche_ids parameter
        if not fiche_ids or len(fiche_ids) == 0:
            raise ToolError("Les paramètres fournis sont invalides. `fiche_ids` ne peut pas être vide. Fournissez au moins une fiche à comparer.")

        all_fiches = charger_cache().get("fiches", {})
        fiches = []
        invalid_ids = []

        for fiche_id in fiche_ids:
            if fiche_id not in all_fiches:
                invalid_ids.append(fiche_id)
            else:
                f = all_fiches[fiche_id]
                fiches.append({
                    "id": fiche_id,
                    "num": f.get("num"),
                    "titre": f.get("title"),
                    "description": f.get("shortDescription", "")[:200],
                    "environmental_impact": f.get("environmental_impact"),
                    "priority_implementation": f.get("priority_implementation"),
                    "score_combined": (f.get("environmental_impact") or 0) + (f.get("priority_implementation") or 0),
                    "lifecycle": f.get("lifecycle"),
                    "saved_resources": f.get("saved_resources", []),
                    "url": f.get("url", ""),
                })

        # If any IDs are invalid, raise an error
        if invalid_ids:
            raise ToolError(f"Erreur lors de la comparaison. Les fiches suivantes n'ont pas été trouvées: {', '.join(invalid_ids)}. Vérifiez les identifiants des fiches.")

        fiches_triees = sorted(fiches, key=lambda x: x["score_combined"], reverse=True)

        return {
            "comparaison": fiches,
            "recommandation": {
                "priorite_1": fiches_triees[0]["id"] if fiches_triees else None,
                "classement": [f["id"] for f in fiches_triees],
                "note": "Classement basé sur le score combiné impact environnemental + priorité d'implémentation",
            },
        }
    except ToolError:
        raise  # Re-raise ToolError as-is
    except Exception as e:
        raise ToolError(f"Erreur lors de la comparaison des fiches. Détail: {str(e)}")


@mcp.tool(
    description="Récupère le contenu complet d'une fiche",
    annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True),
    output_schema={
        "type": "object",
        "properties": {
            "id": {"type": "string"},
            "num": {"type": "string"},
            "title": {"type": "string"},
            "shortDescription": {"type": "string"},
            "description": {"type": "string"},
            "environmental_impact": {"type": "integer"},
            "priority_implementation": {"type": "integer"},
            "lifecycle": {"type": "string"},
            "saved_resources": {"type": "array", "items": {"type": "string"}},
            "url": {"type": "string"},
            "principes_de_validation": {"type": "array", "items": {"type": "string"}}
        }
    }
)
def greenit_obtenir_fiche_complete(fiche_id: str) -> dict:
    """
    Récupère le contenu complet d'une fiche.

    Args:
        fiche_id: Identifiant de la fiche (ex: RWEB_0051)

    Returns:
        Contenu complet de la fiche
    """
    try:
        fiches = charger_cache().get("fiches", {})

        if fiche_id not in fiches:
            raise ToolError(f"Erreur lors de la récupération de la fiche. La fiche `{fiche_id}` n'a pas été trouvée. Vérifiez l'identifiant fourni.")

        fiche = dict(fiches[fiche_id])

        validations = fiche.get("validations") or []
        fiche["principes_de_validation"] = [
            f"Le nombre {v['rule']} est inférieur à {v['maxValue']}"
            for v in validations
            if v.get("rule") and v.get("maxValue")
        ]

        return fiche
    except ToolError:
        raise  # Re-raise ToolError as-is
    except Exception as e:
        raise ToolError(f"Erreur lors de la récupération de la fiche. Détail: {str(e)}")


@mcp.tool(
    description="Retourne les statistiques avancées du référentiel GreenIT",
    annotations=ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
    ),
    output_schema={
        "type": "object",
        "properties": {
            "referentiel_version": {"type": "string"},
            "total_fiches": {"type": "integer"},
            "data_version": {"type": "string"},
            "updated_at": {"type": "string"},
            "distribution_lifecycle": {"type": "object"},
            "distribution_ressources": {"type": "object"},
            "distribution_impact_environnemental": {"type": "object"},
            "distribution_priorite_implementation": {"type": "object"},
            "top_5_score_combine": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "titre": {"type": "string"},
                        "score": {"type": "integer"}
                    }
                }
            }
        }
    }
)
def greenit_obtenir_statistiques() -> dict:
    """
    Retourne les statistiques avancées du référentiel.

    Returns:
        Version du référentiel, total, distribution par lifecycle, par score, top fiches
    """
    try:
        cache = charger_cache()
        fiches = cache.get("fiches", {})

        if not fiches:
            return {"statut": "Cache vide", "fiches": 0}

        from collections import Counter

        lifecycles = Counter()
        resources = Counter()
        ei_dist = Counter()
        pi_dist = Counter()

        for fiche in fiches.values():
            lc = fiche.get("lifecycle")
            if lc:
                lifecycles[lc] += 1
            for r in fiche.get("saved_resources", []):
                resources[r] += 1
            ei = fiche.get("environmental_impact")
            pi = fiche.get("priority_implementation")
            if ei:
                ei_dist[str(ei)] += 1
            if pi:
                pi_dist[str(pi)] += 1

        top_impact = sorted(
            [{"id": k, "titre": v.get("title"), "score": (v.get("environmental_impact") or 0) + (v.get("priority_implementation") or 0)}
             for k, v in fiches.items()],
            key=lambda x: x["score"], reverse=True
        )[:5]

        meta = cache.get("meta", {})

        return {
            "referentiel_version": meta.get("version", ""),
            "total_fiches": len(fiches),
            "data_version": meta.get("data_version"),
            "updated_at": meta.get("updated_at"),
            "distribution_lifecycle": dict(lifecycles.most_common()),
            "distribution_ressources": dict(resources.most_common()),
            "distribution_impact_environnemental": dict(sorted(ei_dist.items())),
            "distribution_priorite_implementation": dict(sorted(pi_dist.items())),
            "top_5_score_combine": top_impact,
        }
    except ToolError:
        raise  # Re-raise ToolError as-is
    except Exception as e:
        raise ToolError(f"Erreur lors du calcul des statistiques. Détail: {str(e)}")


_LIFECYCLE_LABELS = {
    "1-specification": "Spécification",
    "2-concept": "Conception",
    "3-developement": "Développement",
    "4-production": "Production",
    "5-utilization": "Utilisation",
    "6-support": "Support",
    "7-retirement": "Fin de vie",
}


@mcp.tool(
    description="Liste les 7 phases du cycle de vie du référentiel GreenIT",
    annotations=ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
    ),
    output_schema={
        "type": "object",
        "properties": {
            "lifecycles": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string", "description": "Identifiant de la phase (ex: 1-specification)"},
                        "label": {"type": "string", "description": "Libellé français de la phase"},
                        "count": {"type": "integer", "description": "Nombre de fiches pour cette phase"}
                    }
                }
            }
        }
    }
)
def greenit_lister_lifecycles() -> dict:
    """
    Liste les 7 phases du cycle de vie du référentiel GreenIT.

    Les ids retournés sont directement utilisables comme valeur du filtre
    `lifecycle` dans `greenit_lister_fiches`.

    Returns:
        JSON : liste de 7 entrées {id, label, count}, ordonnées par préfixe numérique.
    """
    try:
        fiches = charger_cache().get("fiches", {})
        counts: dict[str, int] = {lc: 0 for lc in _LIFECYCLE_LABELS}
        for fiche in fiches.values():
            lc = fiche.get("lifecycle")
            if lc in counts:
                counts[lc] += 1
        result = [
            {"id": lc, "label": label, "count": counts[lc]}
            for lc, label in _LIFECYCLE_LABELS.items()
        ]
        result.sort(key=lambda e: int(e["id"].split("-")[0]))
        return {"lifecycles": result}
    except ToolError:
        raise  # Re-raise ToolError as-is
    except Exception as e:
        raise ToolError(f"Erreur lors de la récupération des phases du cycle de vie. Détail: {str(e)}")


_RESSOURCE_LABELS = {
    "network":     "Réseau",
    "cpu":         "Processeur",
    "ram":         "Mémoire vive",
    "storage":     "Stockage",
    "requests":    "Requêtes",
    "electricity": "Consommation électrique",
    "ghg":         "Émissions de gaz à effet de serre",
    "e-waste":     "Déchets électroniques",
}


@mcp.tool(
    description="Liste les 8 types de ressources sauvegardées du référentiel GreenIT",
    annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True),
    output_schema={
        "type": "object",
        "properties": {
            "ressources": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string", "description": "Identifiant de la ressource (ex: network)"},
                        "label": {"type": "string", "description": "Libellé français de la ressource"},
                        "count": {"type": "integer", "description": "Nombre de fiches économisant cette ressource"}
                    }
                }
            }
        }
    }
)
def greenit_lister_ressources() -> dict:
    """
    Liste les 8 types de ressources sauvegardées du référentiel GreenIT.

    Les ids retournés sont directement utilisables comme valeur du filtre
    `saved_resource` dans `greenit_lister_fiches`.

    Returns:
        JSON : liste de 8 entrées {id, label, count}, triées par count décroissant.
    """
    try:
        fiches = charger_cache().get("fiches", {})
        counts: dict[str, int] = {r: 0 for r in _RESSOURCE_LABELS}
        for fiche in fiches.values():
            for r in fiche.get("saved_resources", []):
                if r in counts:
                    counts[r] += 1
        result = [
            {"id": r, "label": label, "count": counts[r]}
            for r, label in _RESSOURCE_LABELS.items()
        ]
        result.sort(key=lambda e: e["count"], reverse=True)
        return {"ressources": result}
    except ToolError:
        raise  # Re-raise ToolError as-is
    except Exception as e:
        raise ToolError(f"Erreur lors de la récupération des ressources. Détail: {str(e)}")


@mcp.tool(
    description="Calcule l'EcoIndex (score + grade) à partir des 3 métriques brutes : nœuds DOM, requêtes HTTP, taille KB",
    annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True),
    output_schema={
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "URL de la page mesurée"},
            "dom_nodes": {"type": "integer", "description": "Nombre de nœuds DOM mesurés"},
            "requests": {"type": "integer", "description": "Nombre de requêtes HTTP mesurées"},
            "size_kb": {"type": "number", "description": "Taille totale en kilo-octets"},
            "score": {"type": "integer", "description": "Score EcoIndex (0-100)"},
            "grade": {"type": "string", "description": "Grade EcoIndex (A-G)"}
        }
    }
)
def greenit_calculer_ecoindex(dom_nodes: int, requests: int, size_kb: float, url: str = "") -> str:
    """
    Calcule l'EcoIndex à partir des 3 métriques brutes mesurées par Playwright.

    Protocole de mesure recommandé avec Playwright :
    1. Ouvrir un contexte avec viewport 1920x1080 (spec EcoIndex officielle)
    2. Naviguer vers la page
    3. Attendre 3 secondes
    4. Faire défiler jusqu'en bas progressivement
    5. Attendre 3 secondes
    6. Mesurer nœuds DOM, requêtes HTTP, taille totale en Ko
    7. Appeler cet outil avec les 3 métriques

    Args:
        dom_nodes: Nombre de nœuds dans le DOM
        requests:  Nombre de requêtes HTTP
        size_kb:   Taille totale transférée en kilo-octets
        url:       URL de la page mesurée (optionnel, pour contexte)

    Returns:
        JSON avec url, métriques, score (0-100) et grade (A-G)
    """
    try:
        # Valider que dom_nodes est non-négatif
        validate_nonnegative(dom_nodes, "dom_nodes")

        # Valider que requests est non-négatif
        validate_nonnegative(requests, "requests")

        # Valider que size_kb est non-négatif
        validate_nonnegative(size_kb, "size_kb")

        result = _calculer_ecoindex_impl(dom_nodes, requests, size_kb)
        return json.dumps({
            "url": url,
            "dom_nodes": dom_nodes,
            "requests": requests,
            "size_kb": size_kb,
            "score": result["score"],
            "grade": result["grade"],
        }, ensure_ascii=False, indent=2)

    except ToolError:
        raise
    except Exception as e:
        raise ToolError(
            f"Erreur lors du calcul de l'EcoIndex. Détail: {str(e)}. "
            "Vérifiez que les métriques `dom_nodes`, `requests` et `size_kb` sont valides."
        )


# ============================================================================
# MCP PROMPTS — GreenIT Environmental Impact Analysis Workflows
# ============================================================================


@mcp.prompt()
def audit_ecoindex(url: str, focus: str = "all") -> str:
    """
    Guide user through analyzing a page's environmental impact via EcoIndex.

    Args:
        url: URL to analyze
        focus: Which metrics to focus on (all/dom/requests/size)
    """
    return f"""Analyser l'impact environnemental d'une page web.

URL: {url}
Focus: {focus} (all/dom/requests/size)

Étapes:
1. Charger la page et mesurer ses métriques (DOM nodes, requêtes HTTP, taille KB)
2. Utiliser greenit_calculer_ecoindex avec les métriques mesurées
3. Interpréter le score EcoIndex (0-100) et le grade (A-G)
4. Recommander des optimisations si score < 50

Outils disponibles:
- greenit_calculer_ecoindex(dom_nodes, requests, size_kb) → {{"score": float, "grade": str}}

Génère un rapport structuré avec score, grade, et 3-5 recommandations d'amélioration."""


@mcp.prompt()
def rapport_impact(resultats: str) -> str:
    """
    Guide user through generating a structured environmental impact report.

    Args:
        resultats: Audit results to analyze
    """
    return f"""Générer un rapport d'impact environnemental structuré.

Résultats à analyser: {resultats}

Format du rapport:
- Titre: "Rapport d'Impact Environnemental"
- Résumé: Score EcoIndex global et interprétation
- Détails par métrique: DOM, requêtes HTTP, taille
- Recommandations: 5-10 actions classées par impact potentiel
- Ressources économisées: Estimation énergie/CO2 sauvegardés par optimisation

Utilise greenit_obtenir_statistiques pour contexte secteur si pertinent."""


@mcp.prompt()
def expliquer_fiche(fiche_id: str) -> str:
    """
    Guide user through understanding a sustainability recommendation in detail.

    Args:
        fiche_id: ID of the GreenIT fiche to explain (ex: "RWEB_0001")
    """
    return f"""Expliquer une fiche de recommandation GreenIT en détail.

ID fiche: {fiche_id}

Étapes:
1. Récupérer la fiche complète avec greenit_obtenir_fiche_complete("{fiche_id}")
2. Expliquer l'objectif et le bénéfice environnemental
3. Décrire les ressources économisées (CPU, réseau, stockage, énergie)
4. Donner les étapes d'implémentation (conception/développement/test)
5. Fournir 2-3 exemples concrets de code/patterns
6. Lister les impacts mesurables (avant/après)

Langage: Pédagogique et accessible, cible développeurs."""


@mcp.prompt()
def fiches_par_lifecycle(phase: str, impact_min: int = 3) -> str:
    """
    Guide user through finding recommendations for a specific lifecycle phase.

    Args:
        phase: Lifecycle phase (conception/spécification/développement/test/déploiement/maintenance)
        impact_min: Minimum environmental impact score (1-5)
    """
    return f"""Lister les fiches GreenIT recommandées pour une phase du cycle de vie.

Phase: {phase} (conception/spécification/développement/test/déploiement/maintenance)
Impact minimum: {impact_min}/5

Étapes:
1. Lister toutes les fiches avec greenit_lister_fiches(lifecycle="{phase}")
2. Filtrer par impact >= {impact_min}
3. Organiser par domaine (architecture, frontend, backend, infra, data)
4. Pour chaque fiche, résumer en 1 ligne l'objectif
5. Recommander l'ordre d'implémentation optimal

Génère une checklist priorisée pour la phase donnée."""


@mcp.prompt()
def checklist_ecoindex(domaines: str = "all") -> str:
    """
    Guide user through creating a manual optimization checklist.

    Args:
        domaines: Domains to focus on (all/dom/requests/size/js/images/css)
    """
    return f"""Générer une checklist manuelle pour optimiser l'EcoIndex.

Domaines: {domaines} (all/dom/requests/size/js/images/css)

Format checklist:
- [ ] Catégorie 1: Réduction DOM
  - [ ] Élément spécifique 1
  - [ ] Élément spécifique 2
- [ ] Catégorie 2: Réduction requêtes HTTP
  - [ ] Compression des assets
  - [ ] Cache HTTP
- [ ] Catégorie 3: Réduction taille de transfert
  - [ ] Images optimisées
  - [ ] CSS/JS minifiés

Chaque élément doit être:
- Vérifiable manuellement
- Estimable en temps d'implémentation
- Classé par impact potentiel (High/Medium/Low)

Utilise greenit_obtenir_statistiques pour contexte de conformité secteur."""


@mcp.prompt()
def ressources_comparaison(fiche_ids: str) -> str:
    """
    Guide user through comparing resource savings across multiple fiches.

    Args:
        fiche_ids: Comma-separated fiche IDs (ex: "RWEB_0001,RWEB_0002")
    """
    return f"""Comparer l'impact de plusieurs fiches de recommandation.

Fiches: {fiche_ids} (format: RWEB_0001,RWEB_0002)

Étapes:
1. Récupérer chaque fiche avec greenit_obtenir_fiche_complete
2. Extraire ressources économisées (network/cpu/storage/energy)
3. Créer tableau comparatif
4. Calculer impact cumulatif
5. Recommander ordre d'implémentation par ROI

Tableau à générer:
| Fiche | Réseau | CPU | Stockage | Énergie | Temps impl | ROI |
|-------|--------|-----|----------|---------|------------|-----|

Inclure: difficultés relatives et dépendances entre fiches."""


@mcp.prompt()
def audit_rapide_greenit(url: str) -> str:
    """
    Guide user through a quick 5-minute audit of top-priority recommendations.

    Args:
        url: URL to audit
    """
    return f"""Audit rapide GreenIT d'une page web - 10 fiches prioritaires.

URL: {url}

Étapes:
1. Récupérer greenit_fiches_prioritaires() pour les 10 recommandations à fort impact
2. Mesurer l'URL avec greenit_calculer_ecoindex (estimer DOM, requêtes, taille)
3. Pour chaque fiche du top 10: vérifier si implémentée
4. Générer rapport rapide (5 min de review)

Format rapport:
- EcoIndex score/grade de la page
- Top 5 recommandations manquantes
- Estimation impact si implémentées
- 1 action immédiate recommandée

Cible: quick feedback pour décision d'audit complet."""


@mcp.prompt()
def audit_par_ressource(ressource: str, budget: int = 2) -> str:
    """
    Guide user through optimizing by a specific resource type.

    Args:
        ressource: Resource type to optimize (network/cpu/storage/energy/requests)
        budget: Time budget in hours for implementation
    """
    return f"""Audit ciblé par type de ressource à économiser.

Ressource: {ressource} (network/cpu/storage/energy/requests)
Budget temps: {budget} heures d'implémentation

Étapes:
1. Lister fiches avec greenit_lister_fiches(saved_resource="{ressource}")
2. Filtrer par priorité d'implémentation (rapide < {budget}h)
3. Estimer gain global si toutes implémentées
4. Détailler chaîne d'implémentation

Résultat: Plan d'action spécifique pour économiser {ressource} dans le budget temps."""


# ============================================================================
# MAIN: CLI et démarrage du serveur
# ============================================================================

if __name__ == "__main__":
    factory.run_main(mcp, VERSION, "GreenIT MCP", charger_cache, "fiches", TOKENS_FILE)
