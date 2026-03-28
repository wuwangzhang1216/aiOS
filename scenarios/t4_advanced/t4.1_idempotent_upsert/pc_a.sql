-- PC1: "Fix connection pool exhaustion" exists with priority 4
SELECT 1 FROM tasks WHERE title = 'Fix connection pool exhaustion'
  AND project_id = (SELECT id FROM projects WHERE title = 'Backend API')
  AND priority = 4;

-- PC2: "Implement caching layer" exists with priority 2
SELECT 1 FROM tasks WHERE title = 'Implement caching layer'
  AND project_id = (SELECT id FROM projects WHERE title = 'Backend API')
  AND priority = 2;

-- PC3: "Add GraphQL endpoint" exists with priority 3
SELECT 1 FROM tasks WHERE title = 'Add GraphQL endpoint'
  AND project_id = (SELECT id FROM projects WHERE title = 'Backend API')
  AND priority = 3;

-- PC4: No duplicate titles in the project
SELECT 1 WHERE NOT EXISTS (
  SELECT title FROM tasks
  WHERE project_id = (SELECT id FROM projects WHERE title = 'Backend API')
  GROUP BY title HAVING COUNT(*) > 1
);
