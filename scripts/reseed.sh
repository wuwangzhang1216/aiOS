#!/usr/bin/env bash
# Reseed: clean all experiment data and re-seed from scratch.
# Usage: ./scripts/reseed.sh [--arm sql|mcp|both]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
ARM="${1:---arm}"
ARM_VAL="${2:-both}"
if [ "$ARM" = "--arm" ]; then ARM_VAL="${ARM_VAL}"; else ARM_VAL="both"; fi

pg() { docker exec "$1" psql -U postgres -d "$2" -c "$3" >/dev/null 2>&1 || true; }

# ── Step 1: Clean ──
pg pg-gitea gitea "DELETE FROM issue_label; DELETE FROM repo_unit; DELETE FROM label; DELETE FROM issue; DELETE FROM repository; DELETE FROM \"user\" WHERE lower_name IN ('alice','bob');"
pg pg-miniflux miniflux "DELETE FROM entries; DELETE FROM feeds; DELETE FROM categories WHERE title != 'All';"
pg pg-vikunja vikunja "DELETE FROM label_tasks; DELETE FROM task_assignees; DELETE FROM project_views WHERE project_id IN (1,2); DELETE FROM labels WHERE id <= 100; DELETE FROM tasks; DELETE FROM projects; DELETE FROM users WHERE id IN (1,2);"
pg pg-mattermost mattermost "DELETE FROM posts; DELETE FROM channelmembers WHERE userid IN (SELECT id FROM users WHERE username IN ('alice','bob','agent-user')); DELETE FROM channels WHERE teamid=(SELECT id FROM teams WHERE name='engineering'); DELETE FROM teammembers WHERE teamid=(SELECT id FROM teams WHERE name='engineering') AND userid NOT IN (SELECT id FROM users WHERE username='mmadmin'); DELETE FROM teams WHERE name='engineering'; DELETE FROM users WHERE username IN ('alice','bob','agent-user');"

# ── Step 2: Seed ──
bash "$SCRIPT_DIR/seed-all.sh" >/dev/null 2>&1

# ── Step 3: MCP-specific fixes (only when running MCP arm) ──
if [ "$ARM_VAL" = "mcp" ] || [ "$ARM_VAL" = "both" ]; then
    # Add mmadmin to engineering team + all channels
    docker exec pg-mattermost psql -U postgres -d mattermost -c "
    INSERT INTO teammembers (teamid,userid,roles,deleteat,schemeuser,schemeadmin,schemeguest,createat)
    SELECT t.id, u.id, 'team_admin team_user', 0, true, true, false, extract(epoch from now())::bigint*1000
    FROM teams t CROSS JOIN users u WHERE t.name='engineering' AND u.username='mmadmin'
    ON CONFLICT DO NOTHING;
    INSERT INTO channelmembers (channelid, userid, roles, lastviewedat, msgcount, mentioncount, notifyprops, lastupdateat, schemeuser, schemeguest, schemeadmin)
    SELECT c.id, u.id, 'channel_admin channel_user', 0, 0, 0, '{}', extract(epoch from now())::bigint*1000, true, false, true
    FROM channels c CROSS JOIN users u WHERE u.username='mmadmin' AND c.teamid=(SELECT id FROM teams WHERE name='engineering')
    ON CONFLICT DO NOTHING;
    " >/dev/null 2>&1 || true

    # Set Vikunja project ownership for MCP user
    docker exec pg-vikunja psql -U postgres -d vikunja -c "
    UPDATE projects SET owner_id = (SELECT id FROM users WHERE username LIKE 'exp%' ORDER BY id DESC LIMIT 1) WHERE id IN (1,2);
    " >/dev/null 2>&1 || true
fi
