-- Mattermost seed data: channels, users, and messages
-- Run after Mattermost has initialized its schema.
-- Mattermost uses 26-char alphanumeric IDs and Unix millisecond timestamps.

-- Helper function for Mattermost-style IDs
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
-- Mattermost may create a default team; we ensure "engineering" exists
INSERT INTO teams (id, createat, updateat, deleteat, displayname, name, description, type, allowopeninvite)
VALUES (mm_id(), (EXTRACT(EPOCH FROM NOW()) * 1000)::bigint, (EXTRACT(EPOCH FROM NOW()) * 1000)::bigint,
        0, 'Engineering', 'engineering', 'Engineering team', 'O', true)
ON CONFLICT DO NOTHING;

-- ── Users ──
INSERT INTO users (id, createat, updateat, deleteat, username, email, nickname, position, roles)
VALUES
    (mm_id(), (EXTRACT(EPOCH FROM NOW()) * 1000)::bigint, (EXTRACT(EPOCH FROM NOW()) * 1000)::bigint,
     0, 'agent-user', 'agent@experiment.local', 'Agent', 'AI Agent', 'system_user'),
    (mm_id(), (EXTRACT(EPOCH FROM NOW()) * 1000)::bigint, (EXTRACT(EPOCH FROM NOW()) * 1000)::bigint,
     0, 'alice', 'alice@experiment.local', 'Alice', 'Backend Developer', 'system_user'),
    (mm_id(), (EXTRACT(EPOCH FROM NOW()) * 1000)::bigint, (EXTRACT(EPOCH FROM NOW()) * 1000)::bigint,
     0, 'bob', 'bob@experiment.local', 'Bob', 'DevOps Engineer', 'system_user')
ON CONFLICT DO NOTHING;

-- ── Channels ──
INSERT INTO channels (id, createat, updateat, deleteat, teamid, type, displayname, name, header, purpose, totalmsgcount, lastpostat, totalmsgcountroot, lastrootpostat)
SELECT mm_id(),
       (EXTRACT(EPOCH FROM NOW()) * 1000)::bigint,
       (EXTRACT(EPOCH FROM NOW()) * 1000)::bigint,
       0, t.id, 'O'::channel_type, c.displayname, c.name, c.header, c.purpose, 0, 0, 0, 0
FROM teams t
CROSS JOIN (VALUES
    ('General',         'general',         'General engineering discussions',    'Team-wide announcements'),
    ('Backend',         'backend',         'Backend development',               'Backend API and database discussions'),
    ('Frontend',        'frontend',        'Frontend development',              'React and UI discussions'),
    ('DevOps',          'devops',          'DevOps & Infrastructure',           'CI/CD, deployments, infrastructure'),
    ('Sprint Planning', 'sprint-planning', 'Sprint planning and tracking',      'Sprint ceremonies and task management')
) AS c(displayname, name, header, purpose)
WHERE t.name = 'engineering'
ON CONFLICT DO NOTHING;

-- ── Posts (Messages) ──
INSERT INTO posts (id, createat, updateat, deleteat, userid, channelid, message, type, hashtags, props)
SELECT mm_id(),
       ((EXTRACT(EPOCH FROM NOW()) - p.offset_secs) * 1000)::bigint,
       ((EXTRACT(EPOCH FROM NOW()) - p.offset_secs) * 1000)::bigint,
       0, u.id, ch.id, p.message, '', '', '{}'
FROM (VALUES
    ('alice', 'backend',          3600, 'The login timeout bug is fixed. It was a JWT config issue - expiry was set to 300s instead of 1800s.'),
    ('bob',   'backend',          3000, 'Nice catch! I''ll update the helm chart defaults too.'),
    ('alice', 'backend',          2400, 'I''m starting on the rate limiting middleware today. Going to use a sliding window approach.'),
    ('bob',   'devops',           1800, 'Heads up: I''m seeing connection pool exhaustion in staging. Current max is 20, we might need 50.'),
    ('alice', 'backend',          1200, 'Can we also add a circuit breaker? The downstream service was flapping yesterday.'),
    ('bob',   'general',           600, 'Sprint retro tomorrow at 2pm. Please add your items to the wiki page.'),
    ('alice', 'sprint-planning',   300, 'Completed: login timeout fix (#3), pagination (#2). Starting: rate limiting (#4)')
) AS p(username, channel, offset_secs, message)
JOIN users u ON u.username = p.username
JOIN channels ch ON ch.name = p.channel
ON CONFLICT DO NOTHING;

-- Update channel message counts
UPDATE channels SET totalmsgcount = (
    SELECT COUNT(*) FROM posts WHERE posts.channelid = channels.id AND posts.deleteat = 0
);

DROP FUNCTION IF EXISTS mm_id();
