-- Postconditions for T2.1a: Single message to issue

-- PC1: A new issue exists in backend-api mentioning connection pool
SELECT COUNT(*) >= 1 AS pc1_issue_created
FROM issue i
JOIN repository r ON i.repo_id = r.id
WHERE r.lower_name = 'backend-api'
AND (i.name ILIKE '%connection pool%' OR i.content ILIKE '%connection pool%');

-- PC2: Issue body contains content from the Mattermost message
SELECT COUNT(*) >= 1 AS pc2_content_from_chat
FROM issue i
JOIN repository r ON i.repo_id = r.id
WHERE r.lower_name = 'backend-api'
AND i.content ILIKE '%connection pool%';

-- PC3: Original Mattermost message still exists (not modified)
SELECT COUNT(*) >= 1 AS pc3_source_preserved
FROM posts p
JOIN channels c ON p.channelid = c.id
WHERE c.name = 'devops'
AND p.message LIKE '%connection pool%';
