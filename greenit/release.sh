#!/usr/bin/env bash
# release.sh — Crée une release avec tag git
# Usage: ./release.sh <version>  (ex: ./release.sh 1.1.0)

set -euo pipefail

VERSION="${1:-}"
if [[ -z "$VERSION" ]]; then
  echo "Usage: $0 <version>"
  echo "Exemple: $0 1.1.0"
  exit 1
fi

if ! [[ "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  echo "Erreur: version invalide '$VERSION' (format attendu: X.Y.Z)"
  exit 1
fi

SCRIPT="files/greenit_mcp.py"
PYPROJECT="pyproject.toml"

# Vérifier que le dépôt est propre
if [[ -n "$(git status --porcelain)" ]]; then
  echo "Erreur: des fichiers non committés existent. Committez d'abord vos changements."
  git status --short
  exit 1
fi

# Mettre à jour la constante VERSION dans le script Python
sed -i.bak "s/^VERSION = \".*\"/VERSION = \"$VERSION\"/" "$SCRIPT" && rm -f "$SCRIPT.bak"
echo "VERSION mis à jour dans $SCRIPT"

# Mettre à jour la version dans pyproject.toml
sed -i.bak "s/^version = \".*\"/version = \"$VERSION\"/" "$PYPROJECT" && rm -f "$PYPROJECT.bak"
echo "version mis à jour dans $PYPROJECT"

# Vérifier les mises à jour
grep "VERSION = " "$SCRIPT"
grep "^version = " "$PYPROJECT"

# Committer
git add "$SCRIPT" "$PYPROJECT"
git commit -m "chore(release): bump version to $VERSION"

# Créer le tag
git tag -a "v$VERSION" -m "Release v$VERSION"
echo "Tag v$VERSION créé"

echo ""
echo "Release v$VERSION prête. Pour pousser:"
echo "  git push && git push origin v$VERSION"
