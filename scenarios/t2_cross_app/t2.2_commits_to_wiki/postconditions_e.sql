-- Postconditions for T2.2e: Issues grouped by label

-- PC1: Wiki page exists
SELECT COUNT(*) = 1 AS pc1_page_exists
FROM pages
WHERE path = 'reports/issues-by-label';

-- PC2: Content mentions at least one label from seed data
SELECT content ILIKE '%bug%' OR content ILIKE '%feature%' OR content ILIKE '%enhancement%' AS pc2_has_labels
FROM pages
WHERE path = 'reports/issues-by-label';
