-- Postconditions for T3.1d: Compare with previous

-- PC1: Wiki page exists
SELECT COUNT(*) = 1 AS pc1_page_exists
FROM pages WHERE path = 'reports/sprint-comparison-w12';

-- PC2: Report references week 10 content
SELECT content ILIKE '%week 10%' OR content ILIKE '%w10%' OR content ILIKE '%previous%' AS pc2_references_previous
FROM pages WHERE path = 'reports/sprint-comparison-w12';

-- PC3: Original sprint review page still exists
SELECT COUNT(*) = 1 AS pc3_original_preserved
FROM pages WHERE path = 'meetings/sprint-review-2026-w10';
