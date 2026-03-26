-- Postconditions for T1.2a: Simple text wiki page

-- PC1: Page exists with correct path
SELECT COUNT(*) = 1 AS pc1_page_exists
FROM pages
WHERE path = 'test/simple-page';

-- PC2: Page has correct title
SELECT title = 'Simple Test Page' AS pc2_title_correct
FROM pages
WHERE path = 'test/simple-page';

-- PC3: Page content contains expected text
SELECT content LIKE '%simple test page%' AS pc3_content_present
FROM pages
WHERE path = 'test/simple-page';

-- PC4: Page is published
SELECT "isPublished" = true AS pc4_is_published
FROM pages
WHERE path = 'test/simple-page';

-- PC5: Page is public (not private)
SELECT "isPrivate" = false AS pc5_is_public
FROM pages
WHERE path = 'test/simple-page';
