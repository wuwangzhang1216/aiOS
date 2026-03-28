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

# ── Post-seed fixes ──
echo ""
echo "  Applying post-seed fixes..."

# Gitea: enable issues/wiki/PR on repos (repo_unit: 1=issues, 2=wiki, 3=PR)
docker exec pg-gitea psql -U postgres -d gitea -c "
INSERT INTO repo_unit (repo_id, type, config, created_unix)
SELECT r.id, u.type, '{}', EXTRACT(EPOCH FROM NOW())::bigint
FROM repository r CROSS JOIN (VALUES (1),(2),(3)) AS u(type)
ON CONFLICT DO NOTHING;
" >/dev/null 2>&1 || true

# Vikunja: add default views to projects (required by Vikunja v2+ for task listing)
docker exec pg-vikunja psql -U postgres -d vikunja -c "
INSERT INTO project_views (id, title, project_id, view_kind, position, created, updated)
SELECT nextval('project_views_id_seq'), 'List', p.id, 0, 0, NOW(), NOW()
FROM projects p
WHERE NOT EXISTS (SELECT 1 FROM project_views WHERE project_id = p.id);
" >/dev/null 2>&1 || true

# Vikunja: fix sequences
docker exec pg-vikunja psql -U postgres -d vikunja -c "
SELECT setval('tasks_id_seq', (SELECT COALESCE(MAX(id),0) FROM tasks));
SELECT setval('projects_id_seq', (SELECT COALESCE(MAX(id),0) FROM projects));
SELECT setval('labels_id_seq', (SELECT COALESCE(MAX(id),0) FROM labels));
" >/dev/null 2>&1 || true

# Mattermost: fix NULL columns that cause Go scan errors
docker exec pg-mattermost psql -U postgres -d mattermost -c "
UPDATE teams SET email=COALESCE(email,''), companyname=COALESCE(companyname,''),
  alloweddomains=COALESCE(alloweddomains,''), inviteid=COALESCE(inviteid,''),
  schemeid=COALESCE(schemeid,''), groupconstrained=COALESCE(groupconstrained,false),
  lastteamiconupdate=COALESCE(lastteamiconupdate,0),
  cloudlimitsarchived=COALESCE(cloudlimitsarchived,false);
UPDATE users SET emailverified=COALESCE(emailverified,false);
UPDATE channels SET extraupdateat=COALESCE(extraupdateat,0),
  lastrootpostat=COALESCE(lastrootpostat,0), lastpostat=COALESCE(lastpostat,0),
  header=COALESCE(header,''), purpose=COALESCE(purpose,''),
  creatorid=COALESCE(creatorid,''), schemeid=COALESCE(schemeid,''),
  groupconstrained=COALESCE(groupconstrained,false),
  shared=COALESCE(shared,false);
" >/dev/null 2>&1 || true

# Grant permissions to agent users
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
