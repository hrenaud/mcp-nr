"""
Script pour télécharger les données GreenIT et les mettre en cache

Usage:
    python preparer_donnees.py --telecharger    # Télécharge depuis l'API rweb.greenit.fr
    python preparer_donnees.py --github          # Charge depuis github.com/cnumr/best-practices
    python preparer_donnees.py --example         # Charge les exemples
    python preparer_donnees.py --check          # Vérifie le cache
"""

import httpx
import json
import asyncio
import base64
import re
import subprocess
from pathlib import Path
from typing import Optional, Dict
import sys
from datetime import datetime, timezone

# Configuration
GREENIT_API_URL = "https://rweb.greenit.fr/api"
CACHE_FILE = "greenit_cache.json"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json',
    'Accept-Language': 'fr-FR,fr;q=0.9',
    'Referer': 'https://rweb.greenit.fr/',
}

async def telecharger_api(lang: str = "fr", version: str = "latest") -> Optional[Dict]:
    """
    Télécharge les fiches depuis l'API GreenIT.

    Args:
        lang: Langue (par défaut "fr")
        version: Version (par défaut "latest")

    Returns:
        Dictionnaire avec les fiches, ou None en cas d'erreur
    """
    print(f"📥 Téléchargement depuis l'API GreenIT...")
    print(f"   URL: {GREENIT_API_URL}/fiches?lang={lang}&version={version}")

    try:
        async with httpx.AsyncClient(headers=HEADERS, timeout=30.0) as client:
            url = f"{GREENIT_API_URL}/fiches?lang={lang}&version={version}"
            response = await client.get(url)

            if response.status_code != 200:
                print(f"   ❌ Erreur API: {response.status_code}")
                print(f"   Contenu: {response.text[:200]}")
                return None

            fiches_list = response.json()

            if not isinstance(fiches_list, list):
                print(f"   ❌ Format inattendu: {type(fiches_list)}")
                return None

            print(f"   ✅ {len(fiches_list)} fiches trouvées")

            fiches_dict = {}

            for i, fiche_data in enumerate(fiches_list):
                fiche_num = fiche_data.get("num")

                if not fiche_num:
                    print(f"   ⚠️  Fiche {i} sans numéro, ignorée")
                    continue

                print(f"   📄 Chargement fiche {i+1}/{len(fiches_list)}: {fiche_num}...", end=" ")

                try:
                    fiche_url = f"{GREENIT_API_URL}/fiches/{fiche_num}?lang={lang}&version={version}"
                    fiche_response = await client.get(fiche_url)

                    if fiche_response.status_code == 200:
                        fiche_content = fiche_response.json()
                        fiches_dict[str(fiche_num)] = fiche_content
                        print("✅")
                    else:
                        print(f"❌ (Status {fiche_response.status_code})")

                except Exception as e:
                    print(f"❌ ({str(e)[:30]})")

            return fiches_dict

    except Exception as e:
        print(f"   ❌ Erreur de connexion: {e}")
        return None

async def telecharger_metadata(source: str = "api") -> Dict:
    """Récupère la version courante depuis l'API rweb.greenit.fr/api/versions."""
    print(f"📥 Récupération de la version...")

    now = datetime.now(timezone.utc).isoformat()
    meta = {
        "source": source,
        "data_version": "latest",
        "updated_at": now,
        "version": "",
    }

    try:
        async with httpx.AsyncClient(headers=HEADERS, timeout=10.0) as client:
            print("   Versions...", end=" ")
            response = await client.get(f"{GREENIT_API_URL}/versions")
            if response.status_code == 200:
                data = response.json()
                versions = data["data"] if isinstance(data, dict) else data
                numeric = [v for v in versions if v.replace(".", "").isdigit()]
                meta["version"] = max(numeric, key=lambda v: [int(x) for x in v.split(".")]) if numeric else ""
                print(f"✅ → v{meta['version']}")
            else:
                print(f"⚠️  (Status {response.status_code})")
    except Exception as e:
        print(f"⚠️  ({str(e)[:40]})")

    return meta

def parser_mdx(contenu: str) -> Dict:
    """Parse un fichier MDX et retourne les données structurées."""
    match = re.match(r'^---\n(.*?)\n---\n(.*)$', contenu, re.DOTALL)
    if not match:
        return {}

    frontmatter_raw = match.group(1)
    body = match.group(2).strip()

    frontmatter = {}
    current_key = None
    current_list = None
    current_dict = None

    for line in frontmatter_raw.splitlines():
        kv = re.match(r'^(\w+):\s*(.+)$', line)
        if kv:
            current_list = None
            current_dict = None
            key, val = kv.group(1), kv.group(2).strip().strip("'\"")
            try:
                val = int(val)
            except ValueError:
                pass
            frontmatter[key] = val
            current_key = key
            continue

        key_only = re.match(r'^(\w+):\s*$', line)
        if key_only:
            current_key = key_only.group(1)
            frontmatter[current_key] = []
            current_list = frontmatter[current_key]
            current_dict = None
            continue

        list_item = re.match(r'^  - (.+)$', line)
        if list_item and current_list is not None:
            content = list_item.group(1).strip()
            nested_kv = re.match(r'^(\w+):\s*(.*)$', content)
            if nested_kv:
                k, v = nested_kv.group(1), nested_kv.group(2).strip().strip("'\"")
                current_dict = {k: v}
                current_list.append(current_dict)
            else:
                current_dict = None
                current_list.append(content.strip("'\""))
            continue

        nested_item = re.match(r'^    (\w+):\s*(.*)$', line)
        if nested_item and current_dict is not None:
            k, v = nested_item.group(1), nested_item.group(2).strip().strip("'\"")
            current_dict[k] = v
            continue

    description_match = re.search(r'## Description\s*\n\n(.+?)(?:\n\n|\Z)', body, re.DOTALL)
    short_desc = ""
    if description_match:
        first_para = description_match.group(1).strip().split('\n')[0]
        sentence_end = re.search(r'\.\s', first_para)
        short_desc = first_para[:sentence_end.end()-1] if sentence_end else first_para[:200]

    ref_id = str(frontmatter.get("refID", "")).zfill(4)
    ref_type = frontmatter.get("refType", "RWEB")

    return {
        "num": f"{ref_type}_{ref_id}",
        "refID": ref_id,
        "title": frontmatter.get("title", ""),
        "shortDescription": short_desc,
        "description": body,
        "lifecycle": frontmatter.get("lifecycle", ""),
        "environmental_impact": frontmatter.get("environmental_impact", ""),
        "priority_implementation": frontmatter.get("priority_implementation", ""),
        "saved_resources": frontmatter.get("saved_resources", []),
        "validations": frontmatter.get("validations", []),
        "url": f"https://rweb.greenit.fr/fr/fiches/{ref_id}",
        "source": "github"
    }


def telecharger_github() -> Optional[Dict]:
    """
    Charge les fiches depuis le dépôt GitHub cnumr/best-practices.
    Nécessite que `gh` soit installé et authentifié.
    """
    GITHUB_REPO = "cnumr/best-practices"
    GITHUB_PATH = "src/content/fiches/fr"

    print(f"📥 Chargement depuis GitHub ({GITHUB_REPO})...")

    try:
        result = subprocess.run(
            ["gh", "api", f"repos/{GITHUB_REPO}/contents/{GITHUB_PATH}", "--jq", ".[].name"],
            capture_output=True, text=True, check=True
        )
    except subprocess.CalledProcessError as e:
        print(f"   ❌ Erreur gh api: {e.stderr.strip()}")
        print("   Vérifiez que `gh` est installé et authentifié (gh auth login)")
        return None

    fichiers = [f.strip() for f in result.stdout.strip().splitlines() if f.strip().endswith(".mdx")]
    print(f"   ✅ {len(fichiers)} fichiers trouvés")

    fiches_dict = {}
    erreurs = 0

    for i, nom_fichier in enumerate(fichiers):
        print(f"   📄 {i+1}/{len(fichiers)}: {nom_fichier}...", end=" ", flush=True)

        try:
            result = subprocess.run(
                ["gh", "api", f"repos/{GITHUB_REPO}/contents/{GITHUB_PATH}/{nom_fichier}", "--jq", ".content"],
                capture_output=True, text=True, check=True
            )
            contenu_b64 = result.stdout.strip().replace("\\n", "").replace('"', '')
            contenu = base64.b64decode(contenu_b64).decode("utf-8")

            fiche = parser_mdx(contenu)
            if fiche and fiche.get("refID"):
                fiches_dict[fiche["num"]] = fiche
                print("✅")
            else:
                print("⚠️  (parse raté)")
                erreurs += 1

        except Exception as e:
            print(f"❌ ({str(e)[:40]})")
            erreurs += 1

    print(f"\n   📊 {len(fiches_dict)} fiches chargées, {erreurs} erreurs")
    return fiches_dict if fiches_dict else None


def charger_exemples() -> Dict:
    """Retourne un jeu de données d'exemple pour les tests."""
    print("📋 Chargement des données d'exemple...")

    return {
        "1.01": {
            "num": "1.01",
            "title": "Minifier CSS et JavaScript",
            "shortDescription": "Réduire la taille des fichiers CSS et JavaScript en supprimant les espaces inutiles.",
            "description": "La minification réduit la taille des fichiers CSS et JavaScript en supprimant les espaces, commentaires et caractères inutiles. Cela réduit le temps de téléchargement et la consommation d'énergie.",
            "criteria": [
                {"criterium": "Performance", "impact": "20-30%"}
            ],
            "url": "https://rweb.greenit.fr/fr/fiches/1.01"
        },
        "1.02": {
            "num": "1.02",
            "title": "Compresser les données en Gzip",
            "shortDescription": "Utiliser la compression Gzip pour compresser les réponses serveur.",
            "description": "La compression Gzip permet de réduire de 60-80% la taille des fichiers texte transmis.",
            "criteria": [
                {"criterium": "Performance", "impact": "60-80%"}
            ],
            "url": "https://rweb.greenit.fr/fr/fiches/1.02"
        },
        "3.01": {
            "num": "3.01",
            "title": "Implémenter le lazy-loading des images",
            "shortDescription": "Charger les images uniquement quand elles deviennent visibles.",
            "description": "Le lazy-loading réduit le temps de chargement initial de la page de 30-50%.",
            "criteria": [
                {"criterium": "Performance", "impact": "30-50%"},
                {"criterium": "Écologie", "impact": "Économie d'énergie"}
            ],
            "url": "https://rweb.greenit.fr/fr/fiches/3.01"
        },
        "4.01": {
            "num": "4.01",
            "title": "Implémenter un mode sombre",
            "shortDescription": "Proposer un thème sombre pour les écrans OLED.",
            "description": "Sur les écrans OLED, le mode sombre réduit de 10-15% la consommation d'énergie.",
            "criteria": [
                {"criterium": "Écologie", "impact": "10-15%"}
            ],
            "url": "https://rweb.greenit.fr/fr/fiches/4.01"
        }
    }

def verifier_cache() -> None:
    """Vérifie et affiche les informations du cache."""
    print("🔍 Vérification du cache...")

    if not Path(CACHE_FILE).exists():
        print(f"   ❌ {CACHE_FILE} n'existe pas")
        return

    try:
        with open(CACHE_FILE, 'r', encoding='utf-8') as f:
            cache = json.load(f)

        meta = cache.get("meta", {})
        fiches = cache.get("fiches", {})

        print(f"   ✅ Cache valide")
        print(f"   📊 Fiches: {len(fiches)}")
        print(f"   🏷️  Version: {meta.get('version', 'inconnue')}")
        print(f"   📅 Mis à jour: {meta.get('updated_at', 'inconnu')}")

    except Exception as e:
        print(f"   ❌ Erreur: {e}")

def sauvegarder_cache(data: Dict) -> bool:
    """Sauvegarde les données dans le cache."""
    try:
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"\n✅ Cache sauvegardé: {Path(CACHE_FILE).absolute()}")
        return True
    except Exception as e:
        print(f"\n❌ Erreur de sauvegarde: {e}")
        return False

async def main():
    """Fonction principale."""
    print("\n" + "=" * 70)
    print("🌱 PRÉPARATION DES DONNÉES GREENIT")
    print("=" * 70 + "\n")

    if len(sys.argv) > 1:
        action = sys.argv[1]
    else:
        action = "--example"

    fiches = None
    meta = None

    if action == "--telecharger":
        print("📡 Mode: Téléchargement depuis l'API\n")
        fiches = await telecharger_api()
        meta = await telecharger_metadata(source="api")

    elif action == "--github":
        print("📡 Mode: Chargement depuis GitHub (cnumr/best-practices)\n")
        fiches = telecharger_github()
        meta = await telecharger_metadata(source="github")

    elif action == "--example":
        print("📖 Mode: Données d'exemple\n")
        fiches = charger_exemples()
        now = datetime.now(timezone.utc).isoformat()
        meta = {
            "source": "example",
            "data_version": "latest",
            "updated_at": now,
            "version": "",
        }

    elif action == "--check":
        print("🔍 Mode: Vérification\n")
        verifier_cache()
        return
    else:
        print(f"❌ Action inconnue: {action}")
        print("\nUsage:")
        print("  python preparer_donnees.py --telecharger  # Depuis l'API rweb.greenit.fr")
        print("  python preparer_donnees.py --github        # Depuis GitHub cnumr/best-practices")
        print("  python preparer_donnees.py --example       # Données exemple")
        print("  python preparer_donnees.py --check         # Vérifier cache")
        return

    if fiches and meta:
        sauvegarder_cache({"meta": meta, "fiches": fiches})
        print(f"   📊 {len(fiches)} fiches sauvegardées (v{meta.get('version', '?')})")

    print("\n" + "=" * 70)
    print("✅ PRÉPARATION TERMINÉE")
    print("=" * 70)
    print("\n📌 Prochaines étapes:")
    print(f"   1. Vérifiez {CACHE_FILE}")
    print(f"   2. Lancez: python greenit_mcp.py")
    print(f"   3. Configurez Claude Desktop avec le serveur MCP")
    print()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrompu par l'utilisateur")
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
