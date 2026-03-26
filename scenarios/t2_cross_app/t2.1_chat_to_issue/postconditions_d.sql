-- Postconditions for T2.1d: Issue with label

-- PC1: Issue about rate limiting exists
SELECT COUNT(*) >= 1 AS pc1_issue_exists
FROM issue i
JOIN repository r ON i.repo_id = r.id
WHERE r.lower_name = 'backend-api'
AND (i.name ILIKE '%rate limit%' OR i.content ILIKE '%rate limit%');

-- PC2: Issue has the "feature" label assigned
SELECT COUNT(*) >= 1 AS pc2_label_assigned
FROM issue_label il
JOIN issue i ON il.issue_id = i.id
JOIN label l ON il.label_id = l.id
JOIN repository r ON i.repo_id = r.id
WHERE r.lower_name = 'backend-api'
AND l.name = 'feature'
AND (i.name ILIKE '%rate limit%' OR i.content ILIKE '%rate limit%');
