-- Postconditions for T1.2e: Update existing page

-- PC1: Home page still exists
SELECT COUNT(*) = 1 AS pc1_page_exists
FROM pages
WHERE path = 'home';

-- PC2: Original content is preserved (contains "Welcome")
SELECT content LIKE '%Welcome%' AS pc2_original_preserved
FROM pages
WHERE path = 'home';

-- PC3: New section was appended
SELECT content LIKE '%Recent Updates%' AS pc3_new_section_added
FROM pages
WHERE path = 'home';

-- PC4: New content includes the specific text
SELECT content LIKE '%Agent test%' OR content LIKE '%March 2026%' AS pc4_specific_text
FROM pages
WHERE path = 'home';
