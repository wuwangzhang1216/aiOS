#!/usr/bin/env bash
# Seed all databases with sample data
# Usage: ./scripts/seed-all.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "═══════════════════════════════════════════"
echo "  Seeding databases with sample data       "
echo "═══════════════════════════════════════════"

# Load environment
if [ -f "$PROJECT_DIR/.env" ]; then
    set -a
    source "$PROJECT_DIR/.env"
    set +a
fi

GITEA_PASS="${GITEA_DB_PASS:-gitea_secret}"
WIKI_PASS="${WIKI_DB_PASS:-wiki_secret}"
MM_PASS="${MM_DB_PASS:-mm_secret}"

# Seed Gitea
echo -n "  Seeding Gitea..."
if PGPASSWORD="$GITEA_PASS" psql -h localhost -p 5501 -U postgres -d gitea \
    -f "$PROJECT_DIR/seeds/gitea_seed.sql" >/dev/null 2>&1; then
    echo " done"
else
    echo " FAILED (schema may not be ready yet)"
fi

# Seed Wiki.js
echo -n "  Seeding Wiki.js..."
if PGPASSWORD="$WIKI_PASS" psql -h localhost -p 5502 -U postgres -d wikijs \
    -f "$PROJECT_DIR/seeds/wikijs_seed.sql" >/dev/null 2>&1; then
    echo " done"
else
    echo " FAILED (schema may not be ready yet)"
fi

# Seed Mattermost
echo -n "  Seeding Mattermost..."
if PGPASSWORD="$MM_PASS" psql -h localhost -p 5504 -U postgres -d mattermost \
    -f "$PROJECT_DIR/seeds/mattermost_seed.sql" >/dev/null 2>&1; then
    echo " done"
else
    echo " FAILED (schema may not be ready yet)"
fi

# Grant permissions to agent users (in case init scripts didn't run)
echo ""
echo "  Granting agent user permissions..."
for db_info in "5501:gitea:$GITEA_PASS" "5502:wikijs:$WIKI_PASS" "5504:mattermost:$MM_PASS"; do
    IFS=':' read -r port dbname pass <<< "$db_info"
    PGPASSWORD="$pass" psql -h localhost -p "$port" -U postgres -d "$dbname" -c "
        GRANT SELECT ON ALL TABLES IN SCHEMA public TO agent_ro;
        GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO agent_rw;
        GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO agent_rw;
    " >/dev/null 2>&1 || echo "  Warning: Could not grant permissions on $dbname"
done

echo ""
echo "  Seeding complete."
