-- Postconditions for T3.1e: Action items extraction

-- PC1: Wiki page exists
SELECT COUNT(*) = 1 AS pc1_page_exists
FROM pages WHERE path = 'reports/action-items-w12';

-- PC2: Report contains action-like items
SELECT content ILIKE '%action%' OR content ILIKE '%todo%' OR content ILIKE '%task%' AS pc2_has_actions
FROM pages WHERE path = 'reports/action-items-w12';

-- PC3: Content is substantial
SELECT length(content) > 100 AS pc3_substantial
FROM pages WHERE path = 'reports/action-items-w12';

-- PC4: Mentions specific items from source data
SELECT content ILIKE '%rate limit%'
    OR content ILIKE '%pool%'
    OR content ILIKE '%staging%' AS pc4_has_specific_items
FROM pages WHERE path = 'reports/action-items-w12';
