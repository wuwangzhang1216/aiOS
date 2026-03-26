#!/usr/bin/env bash
# Reset all databases to clean state
# Usage: ./scripts/reset-all.sh [--no-seed]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

NO_SEED=false
[[ "${1:-}" == "--no-seed" ]] && NO_SEED=true

echo "═══════════════════════════════════════════"
echo "  Resetting all databases (clean state)    "
echo "═══════════════════════════════════════════"

echo "[1/4] Stopping containers and removing volumes..."
docker compose -f "$PROJECT_DIR/docker-compose.yml" down -v --remove-orphans 2>/dev/null || true

echo "[2/4] Starting fresh containers..."
docker compose -f "$PROJECT_DIR/docker-compose.yml" up -d

echo "[3/4] Waiting for databases..."
for db in pg-gitea pg-miniflux pg-vikunja pg-mattermost; do
    echo -n "  Waiting for $db..."
    for i in $(seq 1 30); do
        if docker exec "$db" pg_isready -U postgres >/dev/null 2>&1; then
            echo " ready"
            break
        fi
        [ "$i" -eq 30 ] && echo " TIMEOUT" && exit 1
        sleep 1
    done
done

echo "[4/4] Waiting for app schema migrations..."
sleep 15  # Give apps time to run migrations

if [ "$NO_SEED" = false ]; then
    echo ""
    "$SCRIPT_DIR/seed-all.sh"
fi

echo ""
echo "  Reset complete."
