#!/usr/bin/env bash
# Build et lance greenit + rgaa en local (depuis la racine du monorepo).
# Usage : ./local-build.sh
# Décommenter les lignes rgesn quand le scaffold sera complet.

docker build -f greenit/Dockerfile -t greenit-mcp .
docker build -f rgaa/Dockerfile    -t rgaa-mcp .
# docker build -f rgesn/Dockerfile   -t rgesn-mcp .

docker compose -f greenit/docker-compose.yml up -d
docker compose -f rgaa/docker-compose.yml    up -d
# docker compose -f rgesn/docker-compose.yml   up -d