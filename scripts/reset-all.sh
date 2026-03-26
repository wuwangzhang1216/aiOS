#!/usr/bin/env bash
# Reset all databases to clean state for experiment reproducibility
# Usage: ./scripts/reset-all.sh [--no-seed]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
COMPOSE_FILE="$PROJECT_DIR/docker-compose.mvp.yml"

NO_SEED=false
if [[ "${1:-}" == "--no-seed" ]]; then
    NO_SEED=true
fi

echo "═══════════════════════════════════════════"
echo "  Resetting all databases (clean state)    "
echo "═══════════════════════════════════════════"

# Step 1: Stop and remove volumes
echo "[1/4] Stopping containers and removing volumes..."
docker compose -f "$COMPOSE_FILE" down -v --remove-orphans 2>/dev/null || true

# Step 2: Start fresh
echo "[2/4] Starting fresh containers..."
docker compose -f "$COMPOSE_FILE" up -d

# Step 3: Wait for databases to be healthy
echo "[3/4] Waiting for databases to be healthy..."
for db in pg-gitea pg-wiki pg-mattermost; do
    echo -n "  Waiting for $db..."
    for i in $(seq 1 30); do
        if docker exec "$db" pg_isready -U postgres >/dev/null 2>&1; then
            echo " ready"
            break
        fi
        if [ "$i" -eq 30 ]; then
            echo " TIMEOUT"
            exit 1
        fi
        sleep 1
    done
done

# Step 4: Wait for apps to initialize their schemas
echo "[4/4] Waiting for apps to initialize schemas..."

# Gitea needs time to run migrations
echo -n "  Waiting for Gitea..."
for i in $(seq 1 60); do
    if docker exec pg-gitea psql -U postgres -d gitea -c "SELECT 1 FROM repository LIMIT 0" >/dev/null 2>&1; then
        echo " ready"
        break
    fi
    if [ "$i" -eq 60 ]; then
        echo " TIMEOUT (schema not ready)"
        echo "  Note: Gitea may need manual initial setup at http://localhost:3000"
    fi
    sleep 2
done

# Wiki.js
echo -n "  Waiting for Wiki.js..."
for i in $(seq 1 60); do
    if docker exec pg-wiki psql -U postgres -d wikijs -c "SELECT 1 FROM pages LIMIT 0" >/dev/null 2>&1; then
        echo " ready"
        break
    fi
    if [ "$i" -eq 60 ]; then
        echo " TIMEOUT (schema not ready)"
    fi
    sleep 2
done

# Mattermost
echo -n "  Waiting for Mattermost..."
for i in $(seq 1 60); do
    if docker exec pg-mattermost psql -U postgres -d mattermost -c 'SELECT 1 FROM "Posts" LIMIT 0' >/dev/null 2>&1; then
        echo " ready"
        break
    fi
    if [ "$i" -eq 60 ]; then
        echo " TIMEOUT (schema not ready)"
    fi
    sleep 2
done

# Step 5: Seed data
if [ "$NO_SEED" = false ]; then
    echo ""
    "$SCRIPT_DIR/seed-all.sh"
fi

echo ""
echo "═══════════════════════════════════════════"
echo "  Reset complete. All databases are clean. "
echo "═══════════════════════════════════════════"
