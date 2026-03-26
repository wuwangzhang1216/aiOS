-- Postconditions for T3.1c: Team member report

-- PC1: Wiki page exists
SELECT COUNT(*) = 1 AS pc1_page_exists
FROM pages WHERE path = 'reports/team-activity-w12';

-- PC2: Report has sections for both team members
SELECT content ILIKE '%alice%' AND content ILIKE '%bob%' AS pc2_both_members
FROM pages WHERE path = 'reports/team-activity-w12';

-- PC3: Report contains issue-related content
SELECT content ILIKE '%issue%' OR content ILIKE '%login%' OR content ILIKE '%api%' AS pc3_has_issues
FROM pages WHERE path = 'reports/team-activity-w12';
