-- Postconditions for T2.2d: Repo with stats

-- PC1: Wiki page exists
SELECT COUNT(*) = 1 AS pc1_page_exists
FROM pages
WHERE path = 'reports/backend-api-stats';

-- PC2: Content includes numeric stats
SELECT content ~ '\d+' AS pc2_has_numbers
FROM pages
WHERE path = 'reports/backend-api-stats';

-- PC3: Content mentions relevant stat categories
SELECT content ILIKE '%issue%' AND (content ILIKE '%star%' OR content ILIKE '%fork%') AS pc3_has_stat_categories
FROM pages
WHERE path = 'reports/backend-api-stats';
