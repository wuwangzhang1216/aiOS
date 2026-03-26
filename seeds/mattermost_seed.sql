-- Mattermost seed data: realistic channels, users, and messages
-- Run via: psql -h localhost -p 5504 -U postgres -d mattermost -f seeds/mattermost_seed.sql
--
-- Mattermost creates its schema on first boot via migrations.
-- This script inserts sample data. Mattermost uses specific ID formats
-- (26-char alphanumeric) and Unix millisecond timestamps.

-- Helper function to generate Mattermost-style IDs
CREATE OR REPLACE FUNCTION mm_id() RETURNS varchar(26) AS $$
DECLARE
    chars text := 'abcdefghijklmnopqrstuvwxyz0123456789';
    result text := '';
    i int;
BEGIN
    FOR i IN 1..26 LOOP
        result := result || substr(chars, floor(random() * length(chars) + 1)::int, 1);
    END LOOP;
    RETURN result;
END;
$$ LANGUAGE plpgsql;

-- ── Teams ──
-- Mattermost requires at least one team
INSERT INTO teams (id, createat, updateat, displayname, name, description, type, allowopeninvite)
VALUES
    (mm_id(), (EXTRACT(EPOCH FROM NOW()) * 1000)::bigint, (EXTRACT(EPOCH FROM NOW()) * 1000)::bigint,
     'Engineering', 'engineering', 'Engineering team', 'O', true)
ON CONFLICT DO NOTHING;

-- ── Channels ──
-- Insert channels for the engineering team
INSERT INTO channels (id, createat, updateat, teamid, type, displayname, name, header, purpose, totalmsgcount)
SELECT
    mm_id(),
    (EXTRACT(EPOCH FROM NOW()) * 1000)::bigint,
    (EXTRACT(EPOCH FROM NOW()) * 1000)::bigint,
    t.id, c.type, c.displayname, c.name, c.header, c.purpose, 0
FROM teams t
CROSS JOIN (VALUES
    ('O', 'General', 'general', 'General engineering discussions', 'Team-wide announcements and discussions'),
    ('O', 'Backend', 'backend', 'Backend development', 'Backend API and database discussions'),
    ('O', 'Frontend', 'frontend', 'Frontend development', 'React and UI discussions'),
    ('O', 'DevOps', 'devops', 'DevOps & Infrastructure', 'CI/CD, deployments, infrastructure'),
    ('O', 'Sprint Planning', 'sprint-planning', 'Sprint planning and tracking', 'Sprint ceremonies and task management')
) AS c(type, displayname, name, header, purpose)
WHERE t.name = 'engineering'
ON CONFLICT DO NOTHING;

-- ── Users ──
-- Mattermost users (password hash for 'agent123')
INSERT INTO users (id, createat, updateat, username, email, nickname, position, roles)
VALUES
    (mm_id(), (EXTRACT(EPOCH FROM NOW()) * 1000)::bigint, (EXTRACT(EPOCH FROM NOW()) * 1000)::bigint,
     'agent-user', 'agent@experiment.local', 'Agent', 'AI Agent', 'system_user'),
    (mm_id(), (EXTRACT(EPOCH FROM NOW()) * 1000)::bigint, (EXTRACT(EPOCH FROM NOW()) * 1000)::bigint,
     'alice', 'alice@experiment.local', 'Alice', 'Backend Developer', 'system_user'),
    (mm_id(), (EXTRACT(EPOCH FROM NOW()) * 1000)::bigint, (EXTRACT(EPOCH FROM NOW()) * 1000)::bigint,
     'bob', 'bob@experiment.local', 'Bob', 'DevOps Engineer', 'system_user')
ON CONFLICT DO NOTHING;

-- ── Posts (Messages) ──
-- Sample messages in the backend channel
INSERT INTO posts (id, createat, updateat, userid, channelid, message, type)
SELECT
    mm_id(),
    ((EXTRACT(EPOCH FROM NOW()) - p.offset_secs) * 1000)::bigint,
    ((EXTRACT(EPOCH FROM NOW()) - p.offset_secs) * 1000)::bigint,
    u.id,
    ch.id,
    p.message,
    ''
FROM users u
JOIN channels ch ON ch.name = p.channel
CROSS JOIN LATERAL (VALUES
    ('alice', 'backend', 3600, 'The login timeout bug is fixed. It was a JWT config issue - expiry was set to 300s instead of 1800s.'),
    ('bob', 'backend', 3000, 'Nice catch! I''ll update the helm chart defaults too.'),
    ('alice', 'backend', 2400, 'I''m starting on the rate limiting middleware today. Going to use a sliding window approach.'),
    ('bob', 'devops', 1800, 'Heads up: I''m seeing connection pool exhaustion in staging. Current max is 20, we might need 50.'),
    ('alice', 'backend', 1200, 'Can we also add a circuit breaker? The downstream service was flapping yesterday.'),
    ('bob', 'general', 600, 'Sprint retro tomorrow at 2pm. Please add your items to the wiki page.'),
    ('alice', 'sprint-planning', 300, 'Completed: login timeout fix (#3), pagination (#2). Starting: rate limiting (#4)')
) AS p(username, channel, offset_secs, message)
WHERE u.username = p.username
ON CONFLICT DO NOTHING;

-- Update channel message counts
UPDATE channels SET totalmsgcount = (
    SELECT COUNT(*) FROM posts WHERE posts.channelid = channels.id
);

-- Clean up helper function
DROP FUNCTION IF EXISTS mm_id();

-- Note: Mattermost schema is complex with many columns.
-- After first boot, inspect with: \dt and \d posts
-- Some columns may have NOT NULL constraints requiring defaults.
-- Adjust this seed script based on actual schema inspection.
