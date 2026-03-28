-- PC1: alice_issues correct (seed: 3)
SELECT 1 FROM posts p JOIN channels c ON p.channelid = c.id
  WHERE c.name = 'general' AND p.message LIKE '%alice_issues: 3%';

-- PC2: alice_tasks correct (seed: 2 - tasks 2 and 4)
SELECT 1 FROM posts p JOIN channels c ON p.channelid = c.id
  WHERE c.name = 'general' AND p.message LIKE '%alice_tasks: 2%';

-- PC3: bob_issues correct (seed: 2)
SELECT 1 FROM posts p JOIN channels c ON p.channelid = c.id
  WHERE c.name = 'general' AND p.message LIKE '%bob_issues: 2%';

-- PC4: bob_tasks correct (seed: 3 - tasks 1, 3, 5)
SELECT 1 FROM posts p JOIN channels c ON p.channelid = c.id
  WHERE c.name = 'general' AND p.message LIKE '%bob_tasks: 3%';
