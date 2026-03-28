-- PC1: The Vikunja task has the urgent label
SELECT 1 FROM label_tasks lt JOIN tasks t ON lt.task_id = t.id
  JOIN labels l ON lt.label_id = l.id
  WHERE t.title = 'Fix connection pool exhaustion' AND l.title = 'urgent';

-- PC2: Mattermost post with exact escalation message
-- Gitea issue title is "Database connection pool exhaustion"
SELECT 1 FROM posts p JOIN channels c ON p.channelid = c.id
  WHERE c.name = 'devops'
  AND p.message = 'ESCALATED: Database connection pool exhaustion -> task labeled urgent';

-- PC3: The task still has its original bug label too
SELECT 1 FROM label_tasks lt JOIN tasks t ON lt.task_id = t.id
  JOIN labels l ON lt.label_id = l.id
  WHERE t.title = 'Fix connection pool exhaustion' AND l.title = 'bug';
