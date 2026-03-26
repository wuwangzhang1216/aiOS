-- Postconditions for T2.1c: Multiple messages summarized

-- PC1: Summary issue exists
SELECT COUNT(*) >= 1 AS pc1_issue_exists
FROM issue i
JOIN repository r ON i.repo_id = r.id
WHERE r.lower_name = 'backend-api'
AND i.name ILIKE '%summary%' OR i.name ILIKE '%discussion%';

-- PC2: Issue body contains multiple messages (has at least 2 different author references)
SELECT COUNT(*) >= 1 AS pc2_multi_author
FROM issue i
JOIN repository r ON i.repo_id = r.id
WHERE r.lower_name = 'backend-api'
AND (i.content ILIKE '%alice%' AND i.content ILIKE '%bob%');
