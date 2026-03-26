-- Postconditions for T2.1b: Code message to issue

-- PC1: Issue exists with circuit breaker title
SELECT COUNT(*) >= 1 AS pc1_issue_exists
FROM issue i
JOIN repository r ON i.repo_id = r.id
WHERE r.lower_name = 'backend-api'
AND i.name ILIKE '%circuit breaker%';

-- PC2: Issue body mentions circuit breaker
SELECT COUNT(*) >= 1 AS pc2_content_relevant
FROM issue i
JOIN repository r ON i.repo_id = r.id
WHERE r.lower_name = 'backend-api'
AND i.content ILIKE '%circuit breaker%';
