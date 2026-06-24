#!/usr/bin/env bash
# Build et lance greenit + rgaa en local (depuis la racine du monorepo).
# Usage : ./local-build.sh

docker buildx build -f greenit/Dockerfile -t greenit-mcp .
docker buildx build -f rgaa/Dockerfile    -t rgaa-mcp .
docker buildx build -f rgesn/Dockerfile   -t rgesn-mcp .

docker compose -f greenit/docker-compose.yml up -d
docker compose -f rgaa/docker-compose.yml    up -d
docker compose -f rgesn/docker-compose.yml   up -d