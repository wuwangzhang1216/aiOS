-- Postconditions for T3.1b: With statistics

-- PC1: Wiki page exists
SELECT COUNT(*) = 1 AS pc1_page_exists
FROM pages WHERE path = 'reports/sprint-metrics-w12';

-- PC2: Report contains numbers
SELECT content ~ '\d+' AS pc2_has_numbers
FROM pages WHERE path = 'reports/sprint-metrics-w12';

-- PC3: Report mentions both open and closed categories
SELECT (content ILIKE '%open%' OR content ILIKE '%progress%')
   AND (content ILIKE '%closed%' OR content ILIKE '%completed%' OR content ILIKE '%resolved%') AS pc3_has_status_categories
FROM pages WHERE path = 'reports/sprint-metrics-w12';
