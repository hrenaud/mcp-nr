#!/usr/bin/env bash
# Build et lance les 3 MCPs en local (depuis la racine du monorepo).
# Usage : ./local-build.sh

MCPS=(greenit rgaa rgesn)

echo "Exécution des tests avant release..."
for MCP in "${MCPS[@]}"; do
  echo "[$MCP] tests..."
  (cd "${MCP}/files" && pytest ../tests/ -q) || {
    echo "Erreur: les tests $MCP ont échoué. Release annulée."
    exit 1
  }
done
echo "Tous les tests passent. Build..."

docker buildx build -f greenit/Dockerfile -t greenit-mcp .
docker buildx build -f rgaa/Dockerfile    -t rgaa-mcp .
docker buildx build -f rgesn/Dockerfile   -t rgesn-mcp .

docker compose -f greenit/docker-compose.yml up -d
docker compose -f rgaa/docker-compose.yml    up -d
docker compose -f rgesn/docker-compose.yml   up -d