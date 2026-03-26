#!/usr/bin/env bash
# Verify all database connections and basic schema accessibility
# Usage: ./scripts/verify-connections.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "═══════════════════════════════════════════"
echo "  Verifying database connections            "
echo "═══════════════════════════════════════════"

# Load environment
if [ -f "$PROJECT_DIR/.env" ]; then
    set -a
    source "$PROJECT_DIR/.env"
    set +a
fi

PASS=0
FAIL=0

check_db() {
    local name=$1 host=$2 port=$3 user=$4 pass=$5 db=$6 query=$7

    echo -n "  [$name] Connecting as $user..."
    if result=$(PGPASSWORD="$pass" psql -h "$host" -p "$port" -U "$user" -d "$db" -t -c "$query" 2>&1); then
        count=$(echo "$result" | tr -d ' ')
        echo " OK (result: $count)"
        PASS=$((PASS + 1))
    else
        echo " FAILED: $result"
        FAIL=$((FAIL + 1))
    fi
}

# ── Gitea ──
echo ""
echo "─── Gitea (port 5501) ───"
check_db "Gitea/postgres" localhost 5501 postgres "${GITEA_DB_PASS:-gitea_secret}" gitea "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public'"
check_db "Gitea/agent_ro" localhost 5501 agent_ro "${GITEA_AGENT_PASS:-agent_gitea_pass}" gitea "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public'"
check_db "Gitea/agent_rw" localhost 5501 agent_rw "${GITEA_AGENT_PASS:-agent_gitea_pass}" gitea "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public'"

# ── Wiki.js ──
echo ""
echo "─── Wiki.js (port 5502) ───"
check_db "Wiki/postgres" localhost 5502 postgres "${WIKI_DB_PASS:-wiki_secret}" wikijs "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public'"
check_db "Wiki/agent_ro" localhost 5502 agent_ro "${WIKI_AGENT_PASS:-agent_wiki_pass}" wikijs "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public'"
check_db "Wiki/agent_rw" localhost 5502 agent_rw "${WIKI_AGENT_PASS:-agent_wiki_pass}" wikijs "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public'"

# ── Mattermost ──
echo ""
echo "─── Mattermost (port 5504) ───"
check_db "MM/postgres" localhost 5504 postgres "${MM_DB_PASS:-mm_secret}" mattermost "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public'"
check_db "MM/agent_ro" localhost 5504 agent_ro "${MM_AGENT_PASS:-agent_mm_pass}" mattermost "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public'"
check_db "MM/agent_rw" localhost 5504 agent_rw "${MM_AGENT_PASS:-agent_mm_pass}" mattermost "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public'"

# ── Summary ──
echo ""
echo "═══════════════════════════════════════════"
echo "  Results: $PASS passed, $FAIL failed"
echo "═══════════════════════════════════════════"

if [ "$FAIL" -gt 0 ]; then
    exit 1
fi
