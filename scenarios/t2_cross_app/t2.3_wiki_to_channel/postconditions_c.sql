-- Postconditions for T2.3c: Action items extraction

-- PC1: Message posted to backend channel
SELECT COUNT(*) >= 1 AS pc1_message_posted
FROM posts p
JOIN channels c ON p.channelid = c.id
WHERE c.name = 'backend'
AND (p.message ILIKE '%action%' OR p.message ILIKE '%deploy%' OR p.message ILIKE '%review%pool%');

-- PC2: Message mentions specific action items from the wiki
SELECT COUNT(*) >= 1 AS pc2_has_action_items
FROM posts p
JOIN channels c ON p.channelid = c.id
WHERE c.name = 'backend'
AND (p.message ILIKE '%staging%' OR p.message ILIKE '%pool settings%');
