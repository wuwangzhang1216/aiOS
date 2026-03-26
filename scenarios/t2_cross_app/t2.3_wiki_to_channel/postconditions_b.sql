-- Postconditions for T2.3b: Summary version

-- PC1: Message posted to general channel about standup
SELECT COUNT(*) >= 1 AS pc1_message_posted
FROM posts p
JOIN channels c ON p.channelid = c.id
WHERE c.name = 'general'
AND (p.message ILIKE '%standup%' OR p.message ILIKE '%march 18%');

-- PC2: Message mentions blockers or key points
SELECT COUNT(*) >= 1 AS pc2_has_key_points
FROM posts p
JOIN channels c ON p.channelid = c.id
WHERE c.name = 'general'
AND (p.message ILIKE '%blocker%'
     OR p.message ILIKE '%pagination%'
     OR p.message ILIKE '%metrics%dashboard%');
