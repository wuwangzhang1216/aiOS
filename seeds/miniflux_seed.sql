-- Miniflux seed data: sample feeds, categories, and entries
-- Run after Miniflux has initialized its schema (RUN_MIGRATIONS=1)
-- Miniflux creates an admin user on first boot. We add data for that user.

-- ── Categories ──
-- (Miniflux auto-creates "All" category; we add more)
INSERT INTO categories (user_id, title)
SELECT u.id, c.title
FROM users u
CROSS JOIN (VALUES ('Tech News'), ('Engineering Blogs'), ('DevOps')) AS c(title)
WHERE u.username = 'admin'
ON CONFLICT DO NOTHING;

-- ── Feeds ──
INSERT INTO feeds (user_id, category_id, feed_url, site_url, title, crawler, parsing_error_count)
SELECT u.id, cat.id, f.feed_url, f.site_url, f.title, false, 0
FROM users u
CROSS JOIN LATERAL (VALUES
    ('Tech News',         'https://hnrss.org/frontpage',       'https://news.ycombinator.com', 'Hacker News'),
    ('Engineering Blogs', 'https://blog.golang.org/feed.atom', 'https://blog.golang.org',      'Go Blog'),
    ('DevOps',            'https://kubernetes.io/feed.xml',    'https://kubernetes.io',        'Kubernetes Blog')
) AS f(category, feed_url, site_url, title)
JOIN categories cat ON cat.user_id = u.id AND cat.title = f.category
WHERE u.username = 'admin'
ON CONFLICT DO NOTHING;

-- ── Entries ──
INSERT INTO entries (user_id, feed_id, hash, title, url, content, author, status, published_at, created_at, changed_at)
SELECT u.id, fd.id, md5(e.title || e.url), e.title, e.url, e.content, e.author,
       'unread',
       NOW() - (e.age || ' hours')::interval,
       NOW() - (e.age || ' hours')::interval,
       NOW()
FROM users u
CROSS JOIN LATERAL (VALUES
    ('Hacker News',      'Show HN: A new approach to database migrations',
     'https://example.com/db-migrations', '<p>A new tool for zero-downtime schema changes</p>', 'alice_dev', 2),
    ('Hacker News',      'Why SQLite is the most deployed database',
     'https://example.com/sqlite-deployed', '<p>SQLite handles most use cases better than you think</p>', 'bob_eng', 5),
    ('Go Blog',          'Go 1.23 Release Notes',
     'https://blog.golang.org/go1.23', '<p>New features in Go 1.23 including range-over-func</p>', 'Go Team', 12),
    ('Kubernetes Blog',  'Kubernetes v1.31 release',
     'https://kubernetes.io/blog/k8s-131', '<p>New features in Kubernetes 1.31</p>', 'K8s Release Team', 24)
) AS e(feed_title, title, url, content, author, age)
JOIN feeds fd ON fd.user_id = u.id AND fd.title = e.feed_title
WHERE u.username = 'admin'
ON CONFLICT DO NOTHING;
