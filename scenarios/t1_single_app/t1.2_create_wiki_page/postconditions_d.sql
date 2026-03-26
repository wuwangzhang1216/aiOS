-- Postconditions for T1.2d: Nested path page

-- PC1: Page exists with deeply nested path
SELECT COUNT(*) = 1 AS pc1_page_exists
FROM pages
WHERE path = 'projects/backend/api/authentication';

-- PC2: Page has correct title
SELECT title = 'Authentication API Docs' AS pc2_title_correct
FROM pages
WHERE path = 'projects/backend/api/authentication';

-- PC3: Content is non-empty and mentions auth
SELECT length(content) > 50 AND content ILIKE '%auth%' AS pc3_content_relevant
FROM pages
WHERE path = 'projects/backend/api/authentication';
