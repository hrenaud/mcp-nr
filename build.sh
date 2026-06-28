#!/usr/bin/env bash
# Build et lance les 3 MCPs en local (depuis la racine du monorepo).
# Usage : ./build.sh
set -euo pipefail

MCPS=(greenit rgaa rgesn)
echo "Exécution des tests (hors Docker) avant build..."
for MCP in "${MCPS[@]}"; do
  (cd "${MCP}/files" && pytest ../tests/ -q --ignore=../tests/test_docker_integration.py) || {
    echo "Erreur: tests $MCP échoués. Build annulé."; exit 1; }
done

docker buildx build -f greenit/Dockerfile -t greenit-mcp .
docker buildx build -f rgaa/Dockerfile    -t rgaa-mcp .
docker buildx build -f rgesn/Dockerfile   -t rgesn-mcp .

docker compose -f greenit/docker-compose.yml up -d
docker compose -f rgaa/docker-compose.yml    up -d
docker compose -f rgesn/docker-compose.yml   up -d