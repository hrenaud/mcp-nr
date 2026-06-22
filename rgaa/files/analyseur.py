"""
Analyse statique HTML pour critères RGAA automatisables.
Thèmes couverts : 1, 2, 5, 6, 8, 9, 11, 12
"""

import httpx
from bs4 import BeautifulSoup
from typing import Optional


THEMES_ANALYSES = [1, 2, 5, 6, 8, 9, 11, 12]
NOTE = "Analyse statique uniquement. Utiliser Playwright MCP pour l'analyse DOM rendu (contrastes, ARIA dynamique, focus visible)."


def fetcher_html(url: str) -> str:
    with httpx.Client(timeout=30, follow_redirects=True) as client:
        r = client.get(url, headers={"User-Agent": "Mozilla/5.0 RGAA-MCP/1.0"})
        r.raise_for_status()
        return r.text


def analyser_html(html: str, themes: Optional[list[int]] = None) -> dict:
    """Analyse le HTML et retourne les violations par critère."""
    soup = BeautifulSoup(html, "lxml")
    themes_cibles = set(themes) & set(THEMES_ANALYSES) if themes else set(THEMES_ANALYSES)

    resultats = []

    if 1 in themes_cibles:
        resultats.extend(_theme1(soup))
    if 2 in themes_cibles:
        resultats.extend(_theme2(soup))
    if 5 in themes_cibles:
        resultats.extend(_theme5(soup))
    if 6 in themes_cibles:
        resultats.extend(_theme6(soup))
    if 8 in themes_cibles:
        resultats.extend(_theme8(soup))
    if 9 in themes_cibles:
        resultats.extend(_theme9(soup))
    if 11 in themes_cibles:
        resultats.extend(_theme11(soup))
    if 12 in themes_cibles:
        resultats.extend(_theme12(soup))

    nb_violations = sum(1 for r in resultats if r["statut"] == "NC")
    return {
        "themes_analyses": sorted(themes_cibles),
        "nb_violations": nb_violations,
        "criteres": resultats,
        "note": NOTE,
    }


# ============================================================================
# Thème 1 — Images
# ============================================================================

def _theme1(soup: BeautifulSoup) -> list[dict]:
    violations_1_1 = []
    for img in soup.find_all("img"):
        alt = img.get("alt")
        role = img.get("role", "")
        aria_hidden = img.get("aria-hidden", "false")
        if aria_hidden == "true" or role in ("presentation", "none"):
            continue
        if alt is None:
            violations_1_1.append({
                "selecteur": _selecteur(img),
                "html": str(img)[:200],
                "probleme": "Attribut alt manquant",
            })
    return [_critere("1.1", violations_1_1)]


# ============================================================================
# Thème 2 — Cadres
# ============================================================================

def _theme2(soup: BeautifulSoup) -> list[dict]:
    violations = []
    for iframe in soup.find_all("iframe"):
        title = iframe.get("title", "").strip()
        if not title:
            violations.append({
                "selecteur": _selecteur(iframe),
                "html": str(iframe)[:200],
                "probleme": "Attribut title manquant ou vide sur iframe",
            })
    return [_critere("2.1", violations)]


# ============================================================================
# Thème 5 — Tableaux
# ============================================================================

def _theme5(soup: BeautifulSoup) -> list[dict]:
    violations_5_1 = []
    violations_5_7 = []
    for table in soup.find_all("table"):
        caption = table.find("caption")
        summary = table.get("summary", "").strip()
        aria_label = table.get("aria-label", "").strip()
        aria_desc = table.get("aria-describedby", "").strip()
        if not any([caption, summary, aria_label, aria_desc]):
            violations_5_1.append({
                "selecteur": _selecteur(table),
                "html": str(table)[:200],
                "probleme": "Tableau sans caption ni summary ni aria-label",
            })
        for th in table.find_all("th"):
            if not th.get("scope"):
                violations_5_7.append({
                    "selecteur": _selecteur(th),
                    "html": str(th)[:200],
                    "probleme": "Cellule d'en-tête sans attribut scope",
                })
    return [_critere("5.1", violations_5_1), _critere("5.7", violations_5_7)]


# ============================================================================
# Thème 6 — Liens
# ============================================================================

def _theme6(soup: BeautifulSoup) -> list[dict]:
    violations = []
    for a in soup.find_all("a", href=True):
        texte = a.get_text(strip=True)
        aria_label = a.get("aria-label", "").strip()
        aria_labelledby = a.get("aria-labelledby", "").strip()
        title = a.get("title", "").strip()
        img = a.find("img")
        img_alt = img.get("alt", "").strip() if img else ""
        if not any([texte, aria_label, aria_labelledby, title, img_alt]):
            violations.append({
                "selecteur": _selecteur(a),
                "html": str(a)[:200],
                "probleme": "Lien sans intitulé accessible",
            })
    return [_critere("6.1", violations)]


# ============================================================================
# Thème 8 — Éléments obligatoires
# ============================================================================

def _theme8(soup: BeautifulSoup) -> list[dict]:
    resultats = []

    html_tag = soup.find("html")
    lang_valide = html_tag and html_tag.get("lang", "").strip()
    resultats.append(_critere("8.3", [] if lang_valide else [{
        "selecteur": "html",
        "html": str(html_tag)[:100] if html_tag else "<html>",
        "probleme": "Attribut lang manquant ou vide sur <html>",
    }]))

    title = soup.find("title")
    title_valide = title and title.get_text(strip=True)
    resultats.append(_critere("8.5", [] if title_valide else [{
        "selecteur": "title",
        "html": "<title></title>",
        "probleme": "Élément <title> manquant ou vide",
    }]))

    charset_ok = bool(
        soup.find("meta", charset=True)
        or soup.find("meta", attrs={"http-equiv": lambda v: v and "content-type" in v.lower()})
    )
    resultats.append(_critere("8.6", [] if charset_ok else [{
        "selecteur": "head",
        "html": "",
        "probleme": "Déclaration d'encodage (meta charset) manquante",
    }]))

    return resultats


# ============================================================================
# Thème 9 — Structuration
# ============================================================================

def _theme9(soup: BeautifulSoup) -> list[dict]:
    resultats = []

    h1_list = soup.find_all("h1")
    resultats.append(_critere("9.1", [] if h1_list else [{
        "selecteur": "body",
        "html": "",
        "probleme": "Aucun élément <h1> trouvé",
    }]))

    violations_9_2 = []
    niveaux = [int(h.name[1]) for h in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"])]
    for i in range(1, len(niveaux)):
        if niveaux[i] > niveaux[i - 1] + 1:
            violations_9_2.append({
                "selecteur": f"h{niveaux[i]}",
                "html": "",
                "probleme": f"Saut de niveau de titre : h{niveaux[i-1]} → h{niveaux[i]}",
            })
    resultats.append(_critere("9.2", violations_9_2))

    return resultats


# ============================================================================
# Thème 11 — Formulaires
# ============================================================================

def _theme11(soup: BeautifulSoup) -> list[dict]:
    violations = []
    TYPES_EXCLUS = {"hidden", "submit", "reset", "button", "image"}
    for inp in soup.find_all(["input", "select", "textarea"]):
        input_type = (inp.get("type") or "text").lower()
        if input_type in TYPES_EXCLUS:
            continue
        inp_id = inp.get("id", "")
        aria_label = inp.get("aria-label", "").strip()
        aria_labelledby = inp.get("aria-labelledby", "").strip()
        title = inp.get("title", "").strip()
        label_associe = bool(inp_id and soup.find("label", attrs={"for": inp_id}))
        if not any([label_associe, aria_label, aria_labelledby, title]):
            violations.append({
                "selecteur": _selecteur(inp),
                "html": str(inp)[:200],
                "probleme": "Champ de formulaire sans étiquette accessible",
            })
    return [_critere("11.1", violations)]


# ============================================================================
# Thème 12 — Navigation
# ============================================================================

def _theme12(soup: BeautifulSoup) -> list[dict]:
    liens_evitement = soup.find_all("a", href=lambda h: h and h.startswith("#"))
    skip_link = any(
        any(kw in a.get_text(strip=True).lower() for kw in ["contenu", "navigation", "passer", "aller", "skip"])
        for a in liens_evitement
    )
    violations = [] if skip_link else [{
        "selecteur": "body",
        "html": "",
        "probleme": "Aucun lien d'évitement détecté (lien ancre vers #contenu, #nav, etc.)",
    }]
    return [_critere("12.11", violations)]


# ============================================================================
# Helpers
# ============================================================================

def _critere(id: str, elements: list[dict]) -> dict:
    return {
        "id": id,
        "statut": "NC" if elements else "C",
        "nb_elements": len(elements),
        "elements": elements,
    }


def _selecteur(tag) -> str:
    sel = tag.name
    if tag.get("id"):
        sel += f"#{tag['id']}"
    elif tag.get("class"):
        sel += "." + ".".join(tag["class"][:2])
    return sel
