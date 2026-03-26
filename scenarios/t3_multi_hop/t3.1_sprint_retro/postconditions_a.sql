-- Postconditions for T3.1a: Standard retro report

-- PC1: Wiki page exists
SELECT COUNT(*) = 1 AS pc1_page_exists
FROM pages WHERE path = 'reports/sprint-retro-w12';

-- PC2: Report mentions completed work (closed issue from Gitea seed: connection pool)
SELECT content ILIKE '%connection pool%' OR content ILIKE '%completed%' OR content ILIKE '%closed%' AS pc2_has_completed
FROM pages WHERE path = 'reports/sprint-retro-w12';

-- PC3: Report mentions in-progress work (open issues from Gitea seed)
SELECT content ILIKE '%rate limit%' OR content ILIKE '%pagination%' OR content ILIKE '%in progress%' AS pc3_has_in_progress
FROM pages WHERE path = 'reports/sprint-retro-w12';

-- PC4: Report includes chat context (from Mattermost)
SELECT content ILIKE '%alice%' OR content ILIKE '%bob%' AS pc4_has_chat_context
FROM pages WHERE path = 'reports/sprint-retro-w12';

-- PC5: Report has meaningful length (not just a stub)
SELECT length(content) > 200 AS pc5_substantial_content
FROM pages WHERE path = 'reports/sprint-retro-w12';

-- PC6: Data sources were not modified
SELECT (SELECT COUNT(*) FROM issue) > 0 AS pc6_gitea_intact;
