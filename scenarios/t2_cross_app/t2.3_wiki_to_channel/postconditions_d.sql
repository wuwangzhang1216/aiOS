-- Postconditions for T2.3d: Architecture info to channel

-- PC1: Message posted to backend channel about architecture
SELECT COUNT(*) >= 1 AS pc1_message_posted
FROM posts p
JOIN channels c ON p.channelid = c.id
WHERE c.name = 'backend'
AND (p.message ILIKE '%fastapi%' OR p.message ILIKE '%python%' OR p.message ILIKE '%architecture%');

-- PC2: Message mentions services or stack from the wiki page
SELECT COUNT(*) >= 1 AS pc2_has_stack_info
FROM posts p
JOIN channels c ON p.channelid = c.id
WHERE c.name = 'backend'
AND (p.message ILIKE '%api gateway%' OR p.message ILIKE '%auth service%' OR p.message ILIKE '%postgresql%');
