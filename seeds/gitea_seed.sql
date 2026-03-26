-- Gitea seed data: realistic sample data for experiment
-- NOTE: This runs AFTER Gitea has initialized its own schema.
-- Run via: psql -h localhost -p 5501 -U postgres -d gitea -f seeds/gitea_seed.sql
--
-- Gitea creates its schema on first boot. This script inserts sample data
-- into the existing tables. Table/column names must match Gitea's actual schema.
-- We use ON CONFLICT DO NOTHING to be idempotent.

-- Wait for schema to exist (Gitea must have run migrations first)
-- The seed-all.sh script handles this by waiting for the app to be ready.

-- ── Users ──
-- Note: Gitea manages users via its own system. We insert an "agent-user"
-- that the experiment agent will operate as.
-- Password hash for 'agent123' using bcrypt (Gitea default)
INSERT INTO "user" (
    lower_name, name, full_name, email,
    passwd, passwd_hash_algo,
    type, is_admin, is_active,
    created_unix, updated_unix
) VALUES
    ('agent-user', 'agent-user', 'Experiment Agent', 'agent@experiment.local',
     '$2a$10$YGWkMzVHGtsRrv9p8gESHePSuGn8w9RGm9JBjQhFqXUsm7DZ7BJHK', 'bcrypt',
     0, false, true,
     EXTRACT(EPOCH FROM NOW())::bigint, EXTRACT(EPOCH FROM NOW())::bigint),
    ('alice', 'alice', 'Alice Developer', 'alice@experiment.local',
     '$2a$10$YGWkMzVHGtsRrv9p8gESHePSuGn8w9RGm9JBjQhFqXUsm7DZ7BJHK', 'bcrypt',
     0, false, true,
     EXTRACT(EPOCH FROM NOW())::bigint, EXTRACT(EPOCH FROM NOW())::bigint),
    ('bob', 'bob', 'Bob Engineer', 'bob@experiment.local',
     '$2a$10$YGWkMzVHGtsRrv9p8gESHePSuGn8w9RGm9JBjQhFqXUsm7DZ7BJHK', 'bcrypt',
     0, false, true,
     EXTRACT(EPOCH FROM NOW())::bigint, EXTRACT(EPOCH FROM NOW())::bigint)
ON CONFLICT (lower_name) DO NOTHING;

-- ── Repositories ──
INSERT INTO repository (
    owner_id, owner_name, lower_name, name,
    description, is_private, is_fork, is_empty,
    default_branch, num_stars, num_forks, num_issues,
    created_unix, updated_unix
) VALUES
    ((SELECT id FROM "user" WHERE lower_name = 'alice'),
     'alice', 'backend-api', 'backend-api',
     'Main backend API service', false, false, false,
     'main', 3, 1, 5,
     EXTRACT(EPOCH FROM NOW())::bigint, EXTRACT(EPOCH FROM NOW())::bigint),
    ((SELECT id FROM "user" WHERE lower_name = 'alice'),
     'alice', 'frontend-app', 'frontend-app',
     'React frontend application', false, false, false,
     'main', 2, 0, 3,
     EXTRACT(EPOCH FROM NOW())::bigint, EXTRACT(EPOCH FROM NOW())::bigint),
    ((SELECT id FROM "user" WHERE lower_name = 'bob'),
     'bob', 'infra-scripts', 'infra-scripts',
     'Infrastructure automation scripts', true, false, false,
     'main', 0, 0, 1,
     EXTRACT(EPOCH FROM NOW())::bigint, EXTRACT(EPOCH FROM NOW())::bigint)
ON CONFLICT DO NOTHING;

-- ── Labels ──
INSERT INTO label (
    repo_id, org_id, name, description, color,
    num_issues, num_closed_issues,
    created_unix, updated_unix
)
SELECT
    r.id, 0, l.name, l.description, l.color,
    0, 0,
    EXTRACT(EPOCH FROM NOW())::bigint, EXTRACT(EPOCH FROM NOW())::bigint
FROM repository r
CROSS JOIN (VALUES
    ('bug', 'Something is broken', '#d73a4a'),
    ('feature', 'New feature request', '#0075ca'),
    ('enhancement', 'Improvement to existing feature', '#a2eeef'),
    ('documentation', 'Documentation changes', '#0075ca'),
    ('priority:high', 'High priority issue', '#e11d48')
) AS l(name, description, color)
WHERE r.lower_name = 'backend-api'
ON CONFLICT DO NOTHING;

-- ── Issues ──
INSERT INTO issue (
    repo_id, poster_id, index_col,
    name, content,
    is_closed, is_pull, num_comments,
    created_unix, updated_unix
)
SELECT
    r.id,
    (SELECT id FROM "user" WHERE lower_name = 'alice'),
    i.idx,
    i.title, i.body,
    i.closed, false, 0,
    EXTRACT(EPOCH FROM NOW())::bigint, EXTRACT(EPOCH FROM NOW())::bigint
FROM repository r
CROSS JOIN (VALUES
    (1, 'Fix login timeout issue', 'Users report session expires after 5 minutes instead of 30. Check JWT expiry config.', false),
    (2, 'Add pagination to /api/users', 'Currently returns all users in one response. Need offset/limit params.', false),
    (3, 'Database connection pool exhaustion', 'Under load, we run out of DB connections. Need to tune pool settings.', true),
    (4, 'Add rate limiting middleware', 'Implement rate limiting for API endpoints to prevent abuse.', false),
    (5, 'Update README with setup instructions', 'The setup section is outdated. Needs Docker Compose instructions.', false)
) AS i(idx, title, body, closed)
WHERE r.lower_name = 'backend-api'
ON CONFLICT DO NOTHING;

-- Note: Some column names may differ from Gitea's actual schema.
-- After first boot, inspect with: \d issue
-- and adjust this seed script accordingly.
-- The verify-connections.sh script will validate seed data loaded correctly.
