-- Postconditions for T2.2b: All repos summary

-- PC1: Wiki page exists
SELECT COUNT(*) = 1 AS pc1_page_exists
FROM pages
WHERE path = 'reports/all-repositories';

-- PC2: Content mentions at least 2 repos from seed data
SELECT content ILIKE '%backend-api%' AND content ILIKE '%frontend-app%' AS pc2_contains_repos
FROM pages
WHERE path = 'reports/all-repositories';

-- PC3: Content includes owner information
SELECT content ILIKE '%alice%' OR content ILIKE '%bob%' AS pc3_has_owners
FROM pages
WHERE path = 'reports/all-repositories';
