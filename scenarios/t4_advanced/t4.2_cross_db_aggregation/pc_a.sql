-- PC1: Message exists in sprint-planning with correct OPEN_ISSUES
SELECT 1 FROM posts p JOIN channels c ON p.channelid = c.id
  WHERE c.name = 'sprint-planning'
  AND p.message LIKE '%OPEN_ISSUES: 5%';

-- PC2: Correct OPEN_TASKS count
SELECT 1 FROM posts p JOIN channels c ON p.channelid = c.id
  WHERE c.name = 'sprint-planning'
  AND p.message LIKE '%OPEN_TASKS: 3%';

-- PC3: Correct COMPLETED_TASKS count
SELECT 1 FROM posts p JOIN channels c ON p.channelid = c.id
  WHERE c.name = 'sprint-planning'
  AND p.message LIKE '%COMPLETED_TASKS: 1%';

-- PC4: Correct CHANNEL_COUNT
SELECT 1 FROM posts p JOIN channels c ON p.channelid = c.id
  WHERE c.name = 'sprint-planning'
  AND p.message LIKE '%CHANNEL_COUNT: 5%';
