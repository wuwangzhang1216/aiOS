-- Postconditions for T2.1e: Issue assigned to author

-- PC1: Issue exists about what alice was starting
SELECT COUNT(*) >= 1 AS pc1_issue_exists
FROM issue i
JOIN repository r ON i.repo_id = r.id
WHERE r.lower_name = 'backend-api'
AND (i.name ILIKE '%rate limit%' OR i.content ILIKE '%rate limit%');

-- PC2: Issue poster is alice
SELECT COUNT(*) >= 1 AS pc2_assigned_to_alice
FROM issue i
JOIN repository r ON i.repo_id = r.id
JOIN "user" u ON i.poster_id = u.id
WHERE r.lower_name = 'backend-api'
AND u.lower_name = 'alice'
AND (i.name ILIKE '%rate limit%' OR i.content ILIKE '%rate limit%');
