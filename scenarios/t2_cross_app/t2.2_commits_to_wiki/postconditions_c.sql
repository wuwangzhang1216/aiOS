-- Postconditions for T2.2c: Closed issues report

-- PC1: Wiki page exists
SELECT COUNT(*) = 1 AS pc1_page_exists
FROM pages
WHERE path = 'reports/resolved-issues';

-- PC2: Content mentions the closed issue from seed data
SELECT content ILIKE '%connection pool%' AS pc2_mentions_closed_issue
FROM pages
WHERE path = 'reports/resolved-issues';
