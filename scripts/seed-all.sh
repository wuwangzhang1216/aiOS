#!/usr/bin/env bash
# Seed all databases with sample data
# Usage: ./scripts/seed-all.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "═══════════════════════════════════════════"
echo "  Seeding databases with sample data       "
echo "═══════════════════════════════════════════"

seed_pg() {
    local name=$1 container=$2 db=$3 file=$4
    echo -n "  Seeding $name..."
    if docker exec -i "$container" psql -U postgres -d "$db" < "$PROJECT_DIR/seeds/$file" >/dev/null 2>&1; then
        echo " done"
    else
        echo " FAILED (schema may not be ready yet)"
    fi
}

seed_pg "Gitea"       pg-gitea      gitea      gitea_seed.sql
seed_pg "Miniflux"    pg-miniflux   miniflux   miniflux_seed.sql
seed_pg "Vikunja"     pg-vikunja    vikunja    vikunja_seed.sql
seed_pg "Mattermost"  pg-mattermost mattermost mattermost_seed.sql

# Grant permissions to agent users
echo ""
echo "  Granting agent user permissions..."
for db_info in "pg-gitea:gitea" "pg-miniflux:miniflux" "pg-vikunja:vikunja" "pg-mattermost:mattermost"; do
    IFS=':' read -r container dbname <<< "$db_info"
    docker exec "$container" psql -U postgres -d "$dbname" -c "
        DO \$\$ BEGIN
            CREATE ROLE agent_ro LOGIN PASSWORD 'agent_ro_pass';
        EXCEPTION WHEN duplicate_object THEN NULL; END \$\$;
        DO \$\$ BEGIN
            CREATE ROLE agent_rw LOGIN PASSWORD 'agent_rw_pass';
        EXCEPTION WHEN duplicate_object THEN NULL; END \$\$;
        GRANT SELECT ON ALL TABLES IN SCHEMA public TO agent_ro;
        GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO agent_rw;
        GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO agent_rw;
    " >/dev/null 2>&1 || echo "  Warning: Could not grant permissions on $dbname"
done

echo ""
echo "  Seeding complete."
