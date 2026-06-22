#!/usr/bin/env bash
# release.sh — Release synchronisée de tous les MCPs du monorepo
# Usage: ./release.sh <version>  (ex: ./release.sh 1.0.0)

set -euo pipefail

VERSION="${1:-}"
if [[ -z "$VERSION" ]]; then
  echo "Usage: $0 <version>"
  echo "Exemple: $0 1.0.0"
  exit 1
fi

if ! [[ "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  echo "Erreur: version invalide '$VERSION' (format attendu: X.Y.Z)"
  exit 1
fi

if [[ -n "$(git status --porcelain)" ]]; then
  echo "Erreur: des fichiers non committés existent. Committez d'abord vos changements."
  git status --short
  exit 1
fi

MCPS=(greenit rgaa rgesn)

for MCP in "${MCPS[@]}"; do
  SCRIPT="${MCP}/files/${MCP}_mcp.py"
  PYPROJECT="${MCP}/pyproject.toml"

  sed -i.bak "s/^VERSION = \".*\"/VERSION = \"$VERSION\"/" "$SCRIPT" && rm -f "$SCRIPT.bak"
  sed -i.bak "s/^version = \".*\"/version = \"$VERSION\"/" "$PYPROJECT" && rm -f "$PYPROJECT.bak"

  echo "[$MCP] VERSION → $VERSION"
done

git add "${MCPS[@]/%//files/*_mcp.py}" "${MCPS[@]/%//pyproject.toml}" 2>/dev/null || \
  git add greenit/files/greenit_mcp.py greenit/pyproject.toml \
          rgaa/files/rgaa_mcp.py rgaa/pyproject.toml \
          rgesn/files/rgesn_mcp.py rgesn/pyproject.toml

git commit -m "chore(release): bump version to $VERSION"
git tag -a "v$VERSION" -m "Release v$VERSION"

echo ""
echo "Release v$VERSION prête. Pour pousser :"
echo "  git push && git push origin v$VERSION"
