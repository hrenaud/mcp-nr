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

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations
import json
import logging
import os
import sys
from pathlib import Path
from typing import Optional, List

# Modules extraits
from data import (
    charger_cache, charger_metadata, sauvegarder_cache, sauvegarder_metadata,
    CACHE_FILE, METADATA_FILE, calculer_ecoindex as _calculer_ecoindex_impl,
    compter_fiches, compter_lifecycles, compter_ressources, calculer_taux_ecoindex_moyen
)
from mcp_ref_core.auth import construire_verifier, tokens_pour_auth, cmd_generate_token, cmd_list_tokens, cmd_revoke_token
from mcp_ref_core._helpers import validate_themes, validate_score_range, validate_nonnegative
from mcp_ref_core import routes

# Re-export helper functions from routes for backward compatibility with tests
_get_base_url = routes._get_base_url
_get_token_request_url = routes._get_token_request_url

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
    stream=sys.stderr,
)
logger = logging.getLogger("greenit-mcp")

VERSION = "1.1.1"

_BASE_DIR = Path(__file__).parent
TOKENS_FILE = str(_BASE_DIR / "tokens" / "tokens.json")
GREENIT_API_URL = "https://rweb.greenit.fr/api"

# Helper to inject VERSION and theme into routes module
def _setup_routes():
    routes._VERSION = VERSION
    routes._MCP_NAME = "GreenIT MCP"
    routes._MCP_ID = "greenit"
    routes._LOGO = "🌱"
    routes._ACCENT = "#22c55e"
    routes._ACCENT_DARK = "#14532d"
    routes._ACCENT_LIGHT = "#4ade80"
    routes._ACCENT_BTN_TEXT = "#000"
    routes._TAGLINE = "Bonnes pratiques d'écoconception web"


from mcp_ref_core.routes import _http_homepage, _http_guide  # noqa: E402


# ============================================================================
# HTTP ROUTES (public endpoints — no auth)
# ============================================================================

async def _http_install_script(request) -> "Response":
    from starlette.responses import PlainTextResponse
    base_url = _get_base_url()
    mcp_url = f"{base_url}/mcp"
    token_request_url = _get_token_request_url()
    script = (
        routes._INSTALL_SCRIPT_TEMPLATE
        .replace("__BASE_URL__", base_url)
        .replace("__MCP_URL__", mcp_url)
        .replace("__TOKEN_REQUEST_URL__", token_request_url)
        .replace("__MCP_NAME__", routes._MCP_NAME)
        .replace("__MCP_ID__", routes._MCP_ID)
    )
    return PlainTextResponse(script, media_type="text/plain; charset=utf-8")


# ============================================================================
# MCP INITIALIZATION
# ============================================================================

def _create_mcp() -> FastMCP:
    """Crée et configure l'instance FastMCP avec auth et routes HTTP."""
    from mcp_ref_core.auth import DynamicTokenVerifier
    from mcp_ref_core import routes as _routes_mod

    token_path = Path(TOKENS_FILE)
    verifier = DynamicTokenVerifier(token_path)
    _routes_mod._token_verifier = verifier
    _routes_mod._get_tool_definitions = _routes_mod._greenit_tool_definitions

    if verifier.tokens:
        mcp_instance = FastMCP("GreenIT-Referentiel", auth=verifier)
        mcp_instance._auth = verifier
    else:
        mcp_instance = FastMCP("GreenIT-Referentiel")
        mcp_instance._auth = None

    transport = os.environ.get("MCP_TRANSPORT", "stdio")
    if transport == "http":
        mcp_instance.custom_route("/", methods=["GET"])(_http_homepage)
        mcp_instance.custom_route("/install.sh", methods=["GET"])(_http_install_script)
        mcp_instance.custom_route("/guide", methods=["GET"])(_http_guide)
        mcp_instance.custom_route("/admin/tokens", methods=["GET"])(_routes_mod._http_admin_list_tokens)
        mcp_instance.custom_route("/admin/tokens", methods=["POST"])(_routes_mod._http_admin_create_token)
        mcp_instance.custom_route("/admin/tokens/{id}", methods=["GET"])(_routes_mod._http_admin_get_token)
        mcp_instance.custom_route("/admin/tokens/{id}", methods=["PATCH"])(_routes_mod._http_admin_update_token)
        mcp_instance.custom_route("/admin/tokens/{id}", methods=["DELETE"])(_routes_mod._http_admin_delete_token)
    return mcp_instance


# Create MCP instance
mcp = _create_mcp()
_setup_routes()


# ============================================================================
# RESSOURCES: Données statiques par URI
# ============================================================================

@mcp.resource("greenit://fiche/{fiche_id}")
async def obtenir_fiche(fiche_id: str) -> str:
    """Récupère une fiche spécifique."""
    cache = charger_cache()

    if fiche_id in cache:
        fiche = cache[fiche_id]
        return json.dumps(fiche, ensure_ascii=False, indent=2)

    return json.dumps({"erreur": f"Fiche '{fiche_id}' non trouvée"}, ensure_ascii=False)


@mcp.resource("greenit://index")
async def index_fiches() -> str:
    """Liste toutes les fiches disponibles."""
    cache = charger_cache()

    categories = set()
    for fiche in cache.values():
        # Format GitHub: saved_resources + lifecycle
        for r in fiche.get("saved_resources", []):
            categories.add(r)
        if fiche.get("lifecycle"):
            categories.add(fiche["lifecycle"])
        # Format API: criteria (rétrocompatibilité)
        for criterion in fiche.get("criteria", []):
            if "criterium" in criterion:
                categories.add(criterion["criterium"])

    index = {
        "total": len(cache),
        "fiches": [
            {
                "id": fiche_id,
                "num": fiche.get("num"),
                "title": fiche.get("title"),
                "description": fiche.get("shortDescription", "")[:200]
            }
            for fiche_id, fiche in sorted(cache.items())
        ],
        "categories": sorted(list(categories))
    }
    return json.dumps(index, ensure_ascii=False, indent=2)


@mcp.resource("greenit://metadata")
async def obtenir_metadata() -> str:
    """Récupère les métadonnées du référentiel avec statistiques calculées."""
    metadata = charger_metadata()
    return json.dumps({
        "languages": metadata.get("languages", ["fr"]),
        "versions": metadata.get("versions", ["latest"]),
        "source": "https://github.com/greenit-apps/greenit-data",
        "updated_at": metadata.get("updated_at", "inconnue"),
        "nb_fiches": compter_fiches(),
        "nb_lifecycles": compter_lifecycles(),
        "nb_ressources": compter_ressources(),
        "taux_ecoindex_moyen": calculer_taux_ecoindex_moyen(),
    }, ensure_ascii=False, indent=2)


@mcp.resource("greenit://version")
async def version_serveur() -> str:
    """Retourne la version du serveur MCP et des données."""
    metadata = charger_metadata()
    return json.dumps({
        "server_version": VERSION,
        "data_version": metadata.get("data_version", "inconnue"),
        "data_updated_at": metadata.get("updated_at", "inconnue"),
        "fiches": len(charger_cache()),
    }, ensure_ascii=False, indent=2)


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
def lister_fiches(
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

        cache = charger_cache()
        resultats = []

        for fiche_id, fiche in cache.items():
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
def fiches_prioritaires(
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

        cache = charger_cache()
        resultats = []

        for fiche_id, fiche in cache.items():
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
def chercher_fiche(terme: str) -> dict:
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

        cache = charger_cache()
        resultats = []
        terme_lower = terme.lower()

        for fiche_id, fiche in cache.items():
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
def comparer_fiches(fiche_ids: List[str]) -> dict:
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

        cache = charger_cache()
        fiches = []
        invalid_ids = []

        for fiche_id in fiche_ids:
            if fiche_id not in cache:
                invalid_ids.append(fiche_id)
            else:
                f = cache[fiche_id]
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
def obtenir_fiche_complete(fiche_id: str) -> dict:
    """
    Récupère le contenu complet d'une fiche.

    Args:
        fiche_id: Identifiant de la fiche (ex: RWEB_0051)

    Returns:
        Contenu complet de la fiche
    """
    try:
        cache = charger_cache()

        if fiche_id not in cache:
            raise ToolError(f"Erreur lors de la récupération de la fiche. La fiche `{fiche_id}` n'a pas été trouvée. Vérifiez l'identifiant fourni.")

        fiche = dict(cache[fiche_id])

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
def obtenir_statistiques() -> dict:
    """
    Retourne les statistiques avancées du référentiel.

    Returns:
        Total, distribution par lifecycle, par score, top fiches
    """
    try:
        cache = charger_cache()

        if not cache:
            return {"statut": "Cache vide", "fiches": 0}

        from collections import Counter

        lifecycles = Counter()
        resources = Counter()
        ei_dist = Counter()
        pi_dist = Counter()

        for fiche in cache.values():
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
             for k, v in cache.items()],
            key=lambda x: x["score"], reverse=True
        )[:5]

        metadata = charger_metadata()

        return {
            "total_fiches": len(cache),
            "data_version": metadata.get("data_version"),
            "updated_at": metadata.get("updated_at"),
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
def lister_lifecycles() -> dict:
    """
    Liste les 7 phases du cycle de vie du référentiel GreenIT.

    Les ids retournés sont directement utilisables comme valeur du filtre
    `lifecycle` dans `lister_fiches`.

    Returns:
        JSON : liste de 7 entrées {id, label, count}, ordonnées par préfixe numérique.
    """
    try:
        cache = charger_cache()
        counts: dict[str, int] = {lc: 0 for lc in _LIFECYCLE_LABELS}
        for fiche in cache.values():
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
def lister_ressources() -> dict:
    """
    Liste les 8 types de ressources sauvegardées du référentiel GreenIT.

    Les ids retournés sont directement utilisables comme valeur du filtre
    `saved_resource` dans `lister_fiches`.

    Returns:
        JSON : liste de 8 entrées {id, label, count}, triées par count décroissant.
    """
    try:
        cache = charger_cache()
        counts: dict[str, int] = {r: 0 for r in _RESSOURCE_LABELS}
        for fiche in cache.values():
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
def calculer_ecoindex(dom_nodes: int, requests: int, size_kb: float, url: str = "") -> str:
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
2. Utiliser calculer_ecoindex avec les métriques mesurées
3. Interpréter le score EcoIndex (0-100) et le grade (A-G)
4. Recommander des optimisations si score < 50

Outils disponibles:
- calculer_ecoindex(dom_nodes, requests, size_kb) → {{"score": float, "grade": str}}

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

Utilise obtenir_statistiques pour contexte secteur si pertinent."""


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
1. Récupérer la fiche complète avec obtenir_fiche_complete("{fiche_id}")
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
1. Lister toutes les fiches avec lister_fiches(lifecycle="{phase}")
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

Utilise obtenir_statistiques pour contexte de conformité secteur."""


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
1. Récupérer chaque fiche avec obtenir_fiche_complete
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
1. Récupérer fiches_prioritaires() pour les 10 recommandations à fort impact
2. Mesurer l'URL avec calculer_ecoindex (estimer DOM, requêtes, taille)
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
1. Lister fiches avec lister_fiches(saved_resource="{ressource}")
2. Filtrer par priorité d'implémentation (rapide < {budget}h)
3. Estimer gain global si toutes implémentées
4. Détailler chaîne d'implémentation

Résultat: Plan d'action spécifique pour économiser {ressource} dans le budget temps."""


# ============================================================================
# MAIN: CLI et démarrage du serveur
# ============================================================================

if __name__ == "__main__":
    args = sys.argv[1:]

    # --generate-token --name <nom> [--expires-days <N>]
    if "--generate-token" in args:
        name = None
        expires_days = 365
        if "--name" in args:
            idx = args.index("--name")
            if idx + 1 < len(args):
                name = args[idx + 1]
        if "--expires-days" in args:
            idx = args.index("--expires-days")
            if idx + 1 < len(args):
                expires_days = int(args[idx + 1])

        cmd_generate_token(Path(TOKENS_FILE), name, expires_days)
        sys.exit(0)

    # --list-tokens
    if "--list-tokens" in args:
        cmd_list_tokens(Path(TOKENS_FILE))
        sys.exit(0)

    # --revoke-token <token>
    if "--revoke-token" in args:
        idx = args.index("--revoke-token")
        if idx + 1 >= len(args):
            print("Usage: --revoke-token <token>", file=sys.stderr)
            sys.exit(1)
        target = args[idx + 1]
        try:
            cmd_revoke_token(Path(TOKENS_FILE), target)
            sys.exit(0)
        except ValueError as e:
            print(f"Erreur: {e}", file=sys.stderr)
            sys.exit(1)

    # --health
    if "--health" in args:
        cache = charger_cache()
        if cache:
            print(f"OK: {len(cache)} fiches chargées")
            sys.exit(0)
        else:
            print("ERREUR: Cache vide")
            sys.exit(1)

    # Démarrage serveur
    transport = os.environ.get("MCP_TRANSPORT", "stdio")
    host = os.environ.get("MCP_HOST", "0.0.0.0")
    port = int(os.environ.get("MCP_PORT", "8000"))

    cache = charger_cache()
    meta = charger_metadata()

    logger.info("Serveur MCP GreenIT v%s en démarrage...", VERSION)
    logger.info("Cache: %s (%d fiches)", CACHE_FILE, len(cache))
    logger.info("Langues: %s", ", ".join(meta.get("languages", [])))

    if not cache:
        logger.warning("Cache vide — exécutez: python preparer_donnees.py --telecharger")

    if transport == "http":
        tokens = tokens_pour_auth(Path(TOKENS_FILE))
        auth_info = f"activée ({len(tokens)} token(s))" if tokens else "désactivée"
        logger.info("Auth: %s", auth_info)
        logger.info("HTTP: %s:%d", host, port)

    logger.info("Serveur prêt")

    if transport == "http":
        mcp.run(transport="streamable-http", host=host, port=port)
    else:
        mcp.run()
