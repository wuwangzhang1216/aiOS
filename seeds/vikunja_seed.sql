-- Vikunja seed data: sample projects, tasks, and labels
-- Run after Vikunja has initialized its schema

-- Note: Vikunja's schema may vary by version. Inspect with \dt after boot.
-- This seed targets the Vikunja v0.22+ schema.

-- ── Users ──
-- Vikunja creates users via its API, but we can insert directly for the experiment
INSERT INTO users (id, username, email, password, status, created, updated)
VALUES
    (1, 'alice', 'alice@experiment.local', '$2a$14$dummy_hash_for_experiment', 0, NOW(), NOW()),
    (2, 'bob', 'bob@experiment.local', '$2a$14$dummy_hash_for_experiment', 0, NOW(), NOW())
ON CONFLICT DO NOTHING;

-- ── Projects ──
INSERT INTO projects (id, title, description, owner_id, created, updated)
VALUES
    (1, 'Backend API', 'Main backend service development', 1, NOW(), NOW()),
    (2, 'Infrastructure', 'DevOps and infrastructure tasks', 2, NOW(), NOW())
ON CONFLICT DO NOTHING;

-- ── Labels ──
INSERT INTO labels (id, title, hex_color, created_by_id, created, updated)
VALUES
    (1, 'bug',      'e11d48', 1, NOW(), NOW()),
    (2, 'feature',  '0075ca', 1, NOW(), NOW()),
    (3, 'urgent',   'd73a4a', 1, NOW(), NOW()),
    (4, 'docs',     'a2eeef', 1, NOW(), NOW())
ON CONFLICT DO NOTHING;

-- ── Tasks ──
INSERT INTO tasks (id, title, description, done, project_id, created_by_id, priority, created, updated)
VALUES
    (1, 'Fix connection pool exhaustion', 'Under load we run out of DB connections. Need to tune pool size from 20 to 50.', false, 1, 2, 3, NOW() - interval '3 days', NOW()),
    (2, 'Add rate limiting middleware', 'Implement sliding window rate limiting for API endpoints.', false, 1, 1, 2, NOW() - interval '2 days', NOW()),
    (3, 'Update Kubernetes manifests', 'Bump resource limits after last incident.', true, 2, 2, 2, NOW() - interval '5 days', NOW()),
    (4, 'Write API documentation', 'Document all REST endpoints for the backend service.', false, 1, 1, 1, NOW() - interval '1 day', NOW()),
    (5, 'Set up CI/CD pipeline', 'Configure GitHub Actions for automated testing and deployment.', false, 2, 2, 3, NOW(), NOW())
ON CONFLICT DO NOTHING;

-- ── Label-Task associations ──
INSERT INTO label_tasks (label_id, task_id, created)
VALUES
    (1, 1, NOW()),  -- bug -> connection pool
    (2, 2, NOW()),  -- feature -> rate limiting
    (4, 4, NOW()),  -- docs -> API documentation
    (3, 5, NOW())   -- urgent -> CI/CD
ON CONFLICT DO NOTHING;
