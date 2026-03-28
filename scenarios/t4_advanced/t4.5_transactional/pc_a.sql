-- PC1: Gitea issue exists with exact title and body
SELECT 1 FROM issue WHERE name = 'Implement WebSocket support'
  AND content = 'Add real-time WebSocket endpoints for live updates'
  AND repo_id = (SELECT id FROM repository WHERE lower_name = 'backend-api');

-- PC2: Vikunja task exists with exact fields
SELECT 1 FROM tasks WHERE title = 'Implement WebSocket support'
  AND description = 'Tracking task for Gitea issue'
  AND priority = 3
  AND project_id = (SELECT id FROM projects WHERE title = 'Backend API');

-- PC3: Vikunja task has the "feature" label
SELECT 1 FROM label_tasks lt
  JOIN tasks t ON lt.task_id = t.id
  JOIN labels l ON lt.label_id = l.id
  WHERE t.title = 'Implement WebSocket support' AND l.title = 'feature';

-- PC4: Mattermost post with exact message
SELECT 1 FROM posts p JOIN channels c ON p.channelid = c.id
  WHERE c.name = 'backend'
  AND p.message = 'NEW FEATURE: Implement WebSocket support | Gitea issue created | Vikunja task tracked';
