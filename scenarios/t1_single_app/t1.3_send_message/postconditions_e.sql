-- Postconditions for T1.3e: Message in devops channel

-- PC1: Message exists in devops channel
SELECT COUNT(*) >= 1 AS pc1_message_exists
FROM posts p
JOIN channels c ON p.channelid = c.id
WHERE c.name = 'devops'
AND p.message LIKE '%Deployment%staging%';

-- PC2: Posted by bob
SELECT COUNT(*) >= 1 AS pc2_posted_by_bob
FROM posts p
JOIN channels c ON p.channelid = c.id
JOIN users u ON p.userid = u.id
WHERE c.name = 'devops'
AND u.username = 'bob'
AND p.message LIKE '%health checks%';
