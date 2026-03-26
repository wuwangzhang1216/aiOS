-- Wiki.js seed data: realistic sample pages for experiment
-- Run via: psql -h localhost -p 5502 -U postgres -d wikijs -f seeds/wikijs_seed.sql
--
-- Wiki.js uses its own migration system. This script inserts sample data
-- after Wiki.js has initialized. Table names must match Wiki.js v2 schema.

-- ── Users ──
-- Wiki.js manages users through its auth system.
-- The admin user is created during initial setup.
-- We insert additional test users.

-- Note: Wiki.js v2 uses "users" table with specific columns.
-- After first boot, inspect with: \dt and \d users

-- ── Pages ──
-- Wiki.js stores pages in the "pages" table with content, path, etc.
INSERT INTO pages (
    path, hash, title, description,
    "isPrivate", "isPublished",
    content, render,
    "contentType", "createdAt", "updatedAt",
    "editorKey", "localeCode",
    "authorId"
) VALUES
    ('home', md5('home'), 'Home', 'Welcome page',
     false, true,
     '# Welcome to the Team Wiki\n\nThis is our internal knowledge base.\n\n## Quick Links\n- [Meeting Notes](/meetings)\n- [Architecture](/architecture)\n- [Onboarding](/onboarding)',
     '<h1>Welcome to the Team Wiki</h1>',
     'markdown', NOW(), NOW(),
     'markdown', 'en',
     1),
    ('meetings/sprint-review-2026-w10', md5('meetings/sprint-review-2026-w10'),
     'Sprint Review - Week 10 (2026)', 'Sprint review notes for week 10',
     false, true,
     '# Sprint Review - Week 10\n\n## Completed\n- Fixed login timeout issue\n- Added pagination to users API\n\n## In Progress\n- Rate limiting middleware\n- DB connection pool optimization\n\n## Blockers\n- None\n\n## Action Items\n- [ ] Alice: Deploy rate limiter to staging\n- [ ] Bob: Review pool settings PR',
     '',
     'markdown', NOW(), NOW(),
     'markdown', 'en',
     1),
    ('architecture/backend', md5('architecture/backend'),
     'Backend Architecture', 'Overview of backend system architecture',
     false, true,
     '# Backend Architecture\n\n## Stack\n- **Language**: Python 3.12\n- **Framework**: FastAPI\n- **Database**: PostgreSQL 16\n- **Cache**: Redis 7\n\n## Services\n1. API Gateway\n2. Auth Service\n3. User Service\n4. Notification Service\n\n## Database Schema\nSee [schema diagram](/architecture/db-schema)',
     '',
     'markdown', NOW(), NOW(),
     'markdown', 'en',
     1),
    ('onboarding/new-developer', md5('onboarding/new-developer'),
     'New Developer Onboarding', 'Step-by-step onboarding guide',
     false, true,
     '# New Developer Onboarding\n\n## Day 1\n1. Get access to Git repositories\n2. Set up local development environment\n3. Read architecture docs\n\n## Day 2\n1. Join team channels on Mattermost\n2. Review open issues\n3. Pick a starter task\n\n## Contacts\n- **Tech Lead**: Alice (alice@experiment.local)\n- **DevOps**: Bob (bob@experiment.local)',
     '',
     'markdown', NOW(), NOW(),
     'markdown', 'en',
     1),
    ('meetings/standup-2026-03-18', md5('meetings/standup-2026-03-18'),
     'Daily Standup - March 18, 2026', 'Daily standup notes',
     false, true,
     '# Standup - March 18, 2026\n\n## Alice\n- Yesterday: Finished pagination PR\n- Today: Starting rate limiting\n- Blockers: None\n\n## Bob\n- Yesterday: Investigated connection pool issue\n- Today: Testing pool config changes\n- Blockers: Need access to prod metrics dashboard',
     '',
     'markdown', NOW(), NOW(),
     'markdown', 'en',
     1)
ON CONFLICT DO NOTHING;

-- ── Tags ──
INSERT INTO tags (tag, title, "createdAt", "updatedAt")
VALUES
    ('meeting-notes', 'Meeting Notes', NOW(), NOW()),
    ('architecture', 'Architecture', NOW(), NOW()),
    ('onboarding', 'Onboarding', NOW(), NOW()),
    ('sprint', 'Sprint', NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Note: Wiki.js schema may vary between versions.
-- After first boot, inspect with: \dt and \d pages
-- Adjust column names as needed.
