#!/usr/bin/env bash
# Verify all database connections
# Usage: ./scripts/verify-connections.sh
set -euo pipefail

echo "═══════════════════════════════════════════"
echo "  Verifying database connections            "
echo "═══════════════════════════════════════════"

PASS=0
FAIL=0

check_db() {
    local name=$1 container=$2 user=$3 db=$4

    echo -n "  [$name] Connecting as $user..."
    if result=$(docker exec "$container" psql -U "$user" -d "$db" -t -c \
        "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public'" 2>&1); then
        count=$(echo "$result" | tr -d ' ')
        echo " OK ($count tables)"
        PASS=$((PASS + 1))
    else
        echo " FAILED"
        FAIL=$((FAIL + 1))
    fi
}

for app in "Gitea:pg-gitea:gitea" "Miniflux:pg-miniflux:miniflux" "Vikunja:pg-vikunja:vikunja" "Mattermost:pg-mattermost:mattermost"; do
    IFS=':' read -r name container db <<< "$app"
    echo ""
    echo "─── $name ───"
    check_db "$name/postgres" "$container" postgres "$db"
    check_db "$name/agent_rw" "$container" agent_rw "$db"
done

echo ""
echo "═══════════════════════════════════════════"
echo "  Results: $PASS passed, $FAIL failed"
echo "═══════════════════════════════════════════"

[ "$FAIL" -eq 0 ] || exit 1
