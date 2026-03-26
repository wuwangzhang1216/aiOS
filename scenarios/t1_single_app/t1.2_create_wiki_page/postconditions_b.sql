-- Postconditions for T1.2b: Markdown formatted page

-- PC1: Page exists
SELECT COUNT(*) = 1 AS pc1_page_exists
FROM pages
WHERE path = 'test/markdown-page';

-- PC2: Content contains a markdown heading
SELECT content LIKE '%#%' AS pc2_has_heading
FROM pages
WHERE path = 'test/markdown-page';

-- PC3: Content contains bullet list items (at least one - or *)
SELECT content LIKE '%- %' OR content LIKE '%* %' AS pc3_has_list
FROM pages
WHERE path = 'test/markdown-page';

-- PC4: Content contains a code block
SELECT content LIKE '%```%' AS pc4_has_code_block
FROM pages
WHERE path = 'test/markdown-page';

-- PC5: Page is published
SELECT "isPublished" = true AS pc5_is_published
FROM pages
WHERE path = 'test/markdown-page';
