-- Gitea seed data: users, repos, labels, issues
-- Run AFTER Gitea has initialized its schema via migrations.
-- Idempotent via ON CONFLICT DO NOTHING.

-- ── Users ──
INSERT INTO "user" (
    lower_name, name, full_name, email,
    passwd, passwd_hash_algo,
    type, is_admin, is_active,
    avatar, avatar_email,
    created_unix, updated_unix
) VALUES
    ('alice', 'alice', 'Alice Developer', 'alice@experiment.local',
     '$2a$10$YGWkMzVHGtsRrv9p8gESHePSuGn8w9RGm9JBjQhFqXUsm7DZ7BJHK', 'bcrypt',
     0, false, true, '', 'alice@experiment.local',
     EXTRACT(EPOCH FROM NOW())::bigint, EXTRACT(EPOCH FROM NOW())::bigint),
    ('bob', 'bob', 'Bob Engineer', 'bob@experiment.local',
     '$2a$10$YGWkMzVHGtsRrv9p8gESHePSuGn8w9RGm9JBjQhFqXUsm7DZ7BJHK', 'bcrypt',
     0, false, true, '', 'bob@experiment.local',
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
SELECT r.id, 0, l.name, l.description, l.color, 0, 0,
       EXTRACT(EPOCH FROM NOW())::bigint, EXTRACT(EPOCH FROM NOW())::bigint
FROM repository r
CROSS JOIN (VALUES
    ('bug',           'Something is broken',           '#d73a4a'),
    ('feature',       'New feature request',           '#0075ca'),
    ('enhancement',   'Improvement to existing feature','#a2eeef'),
    ('documentation', 'Documentation changes',          '#0075ca'),
    ('priority:high', 'High priority issue',            '#e11d48')
) AS l(name, description, color)
WHERE r.lower_name = 'backend-api'
ON CONFLICT DO NOTHING;

-- ── Issues ──
-- Note: Gitea uses "index" as the issue number within a repo.
-- Check actual column name after migration.
INSERT INTO issue (
    repo_id, poster_id,
    name, content,
    is_closed, is_pull, num_comments,
    created_unix, updated_unix
)
SELECT r.id,
       (SELECT id FROM "user" WHERE lower_name = i.poster),
       i.title, i.body, i.closed, false, 0,
       EXTRACT(EPOCH FROM NOW())::bigint, EXTRACT(EPOCH FROM NOW())::bigint
FROM repository r
CROSS JOIN (VALUES
    ('alice', 'Fix login timeout issue',
     'Users report session expires after 5 minutes instead of 30. Check JWT expiry config.', false),
    ('alice', 'Add pagination to /api/users',
     'Currently returns all users in one response. Need offset/limit params.', false),
    ('bob',   'Database connection pool exhaustion',
     'Under load, we run out of DB connections. Need to tune pool settings.', false),
    ('alice', 'Add rate limiting middleware',
     'Implement rate limiting for API endpoints to prevent abuse.', false),
    ('bob',   'Update README with setup instructions',
     'The setup section is outdated. Needs Docker Compose instructions.', false)
) AS i(poster, title, body, closed)
WHERE r.lower_name = 'backend-api'
ON CONFLICT DO NOTHING;
