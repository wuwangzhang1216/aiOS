-- Postconditions for T1.3c: Message with code reference

-- PC1: Message exists in backend channel from bob
SELECT COUNT(*) >= 1 AS pc1_message_exists
FROM posts p
JOIN channels c ON p.channelid = c.id
JOIN users u ON p.userid = u.id
WHERE c.name = 'backend'
AND u.username = 'bob'
AND p.message LIKE '%auth_middleware%';

-- PC2: Message contains code reference
SELECT COUNT(*) >= 1 AS pc2_has_code_ref
FROM posts p
JOIN channels c ON p.channelid = c.id
WHERE c.name = 'backend'
AND (p.message LIKE '%`auth_middleware.py`%' OR p.message LIKE '%auth_middleware.py%');
