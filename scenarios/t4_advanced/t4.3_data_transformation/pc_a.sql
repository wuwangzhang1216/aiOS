-- PC1: Issue for "database migrations" with exact [HN] prefix
SELECT 1 FROM issue WHERE repo_id = (SELECT id FROM repository WHERE lower_name = 'backend-api')
  AND name = '[HN] Show HN: A new approach to database migrations';

-- PC2: Issue for "SQLite" with exact [HN] prefix
SELECT 1 FROM issue WHERE repo_id = (SELECT id FROM repository WHERE lower_name = 'backend-api')
  AND name = '[HN] Why SQLite is the most deployed database';

-- PC3: Body of migrations issue has Source line
SELECT 1 FROM issue WHERE name = '[HN] Show HN: A new approach to database migrations'
  AND content LIKE 'Source: https://example.com/db-migrations%';

-- PC4: Body of migrations issue has Author line
SELECT 1 FROM issue WHERE name = '[HN] Show HN: A new approach to database migrations'
  AND content LIKE '%Author: alice_dev%';
