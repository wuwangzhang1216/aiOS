-- Gitea issues with "connection" in title (seed):
--   "Database connection pool exhaustion" (id=3)
-- Vikunja already has: "Fix connection pool exhaustion" (different title!)
-- So the agent must create a NEW task with the exact Gitea title.

-- PC1: Vikunja task with exact Gitea issue title exists
SELECT 1 FROM tasks WHERE title = 'Database connection pool exhaustion'
  AND project_id = (SELECT id FROM projects WHERE title = 'Backend API');

-- PC2: Triage summary posted to sprint-planning
SELECT 1 FROM posts p JOIN channels c ON p.channelid = c.id
  WHERE c.name = 'sprint-planning'
  AND p.message LIKE 'BUG_TRIAGE:%';

-- PC3: Triage summary mentions the issue
SELECT 1 FROM posts p JOIN channels c ON p.channelid = c.id
  WHERE c.name = 'sprint-planning'
  AND p.message LIKE '%Database connection pool exhaustion%'
  AND p.message LIKE '%SYNCED%';
