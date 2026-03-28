-- Seed: open tasks in Backend API with labels:
--   Task 1 "Fix connection pool exhaustion" label=bug (id=1) priority=3
--   Task 2 "Add rate limiting middleware" label=feature (id=2) priority=2
--   Task 4 "Write API documentation" label=docs (id=4) priority=1

-- PC1: Post for connection pool task with exact format
SELECT 1 FROM posts p JOIN channels c ON p.channelid = c.id
  WHERE c.name = 'backend'
  AND p.message = 'TASK: Fix connection pool exhaustion | LABEL: bug | PRIORITY: 3';

-- PC2: Post for rate limiting task
SELECT 1 FROM posts p JOIN channels c ON p.channelid = c.id
  WHERE c.name = 'backend'
  AND p.message = 'TASK: Add rate limiting middleware | LABEL: feature | PRIORITY: 2';

-- PC3: Post for documentation task
SELECT 1 FROM posts p JOIN channels c ON p.channelid = c.id
  WHERE c.name = 'backend'
  AND p.message = 'TASK: Write API documentation | LABEL: docs | PRIORITY: 1';
