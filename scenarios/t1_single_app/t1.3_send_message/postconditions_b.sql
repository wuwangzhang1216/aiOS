-- Postconditions for T1.3b: Message mentioning a user

-- PC1: Message exists in backend channel
SELECT COUNT(*) >= 1 AS pc1_message_exists
FROM posts p
JOIN channels c ON p.channelid = c.id
WHERE c.name = 'backend'
AND p.message LIKE '%bob%'
AND p.message LIKE '%review%';

-- PC2: Message mentions bob (contains @bob or bob's user reference)
SELECT COUNT(*) >= 1 AS pc2_mentions_bob
FROM posts p
JOIN channels c ON p.channelid = c.id
WHERE c.name = 'backend'
AND (p.message LIKE '%@bob%' OR p.message LIKE '%bob%')
AND p.message LIKE '%PR%' OR p.message LIKE '%connection pool%';
