-- Postconditions for T2.3e: Notify with mention

-- PC1: Welcome message posted to general channel
SELECT COUNT(*) >= 1 AS pc1_message_posted
FROM posts p
JOIN channels c ON p.channelid = c.id
WHERE c.name = 'general'
AND (p.message ILIKE '%welcome%' OR p.message ILIKE '%onboarding%');

-- PC2: Message mentions bob
SELECT COUNT(*) >= 1 AS pc2_mentions_bob
FROM posts p
JOIN channels c ON p.channelid = c.id
WHERE c.name = 'general'
AND p.message ILIKE '%bob%'
AND (p.message ILIKE '%onboarding%' OR p.message ILIKE '%welcome%');
