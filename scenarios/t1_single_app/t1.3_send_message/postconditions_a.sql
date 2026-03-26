-- Postconditions for T1.3a: Simple text message

-- PC1: A new message exists in the general channel containing the expected text
SELECT COUNT(*) >= 1 AS pc1_message_exists
FROM posts p
JOIN channels c ON p.channelid = c.id
WHERE c.name = 'general'
AND p.message LIKE '%Hello from the AI agent%';

-- PC2: Message was posted by alice
SELECT COUNT(*) >= 1 AS pc2_posted_by_alice
FROM posts p
JOIN channels c ON p.channelid = c.id
JOIN users u ON p.userid = u.id
WHERE c.name = 'general'
AND p.message LIKE '%Hello from the AI agent%'
AND u.username = 'alice';

-- PC3: Message has valid timestamps (non-zero)
SELECT p.createat > 0 AS pc3_valid_timestamp
FROM posts p
JOIN channels c ON p.channelid = c.id
WHERE c.name = 'general'
AND p.message LIKE '%Hello from the AI agent%'
LIMIT 1;
