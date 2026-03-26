-- Postconditions for T2.2a: Single repo issues to wiki

-- PC1: Wiki page exists
SELECT COUNT(*) = 1 AS pc1_page_exists
FROM pages
WHERE path = 'reports/backend-api-issues';

-- PC2: Page title is correct
SELECT title ILIKE '%backend%api%issue%' AS pc2_title_correct
FROM pages
WHERE path = 'reports/backend-api-issues';

-- PC3: Page content mentions at least one actual issue title from Gitea seed data
SELECT content ILIKE '%login timeout%'
    OR content ILIKE '%pagination%'
    OR content ILIKE '%rate limit%' AS pc3_contains_issue_data
FROM pages
WHERE path = 'reports/backend-api-issues';
