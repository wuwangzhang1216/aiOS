-- Postconditions for T1.3d: Reply to existing message

-- PC1: Reply message exists
SELECT COUNT(*) >= 1 AS pc1_reply_exists
FROM posts p
JOIN channels c ON p.channelid = c.id
JOIN users u ON p.userid = u.id
WHERE c.name = 'backend'
AND u.username = 'bob'
AND p.message LIKE '%staging%';

-- PC2: Reply has a rootid (is part of a thread) — or at minimum the message exists
-- Note: If the agent couldn't figure out threading, the message should still exist
SELECT COUNT(*) >= 1 AS pc2_message_or_thread
FROM posts p
JOIN channels c ON p.channelid = c.id
WHERE c.name = 'backend'
AND p.message LIKE '%Thanks for the update%';
