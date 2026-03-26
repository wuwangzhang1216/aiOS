-- Postconditions for T1.2c: Page with tags

-- PC1: Page exists
SELECT COUNT(*) = 1 AS pc1_page_exists
FROM pages
WHERE path = 'test/tagged-page';

-- PC2: The "architecture" tag exists
SELECT COUNT(*) >= 1 AS pc2_tag_exists
FROM tags
WHERE tag = 'architecture';

-- PC3: Page is associated with the architecture tag
-- Note: Wiki.js uses pageTags junction table
SELECT COUNT(*) >= 1 AS pc3_tag_linked
FROM "pageTags"
WHERE "pageId" = (SELECT id FROM pages WHERE path = 'test/tagged-page')
  AND "tagId" = (SELECT id FROM tags WHERE tag = 'architecture');
