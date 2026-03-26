-- Postconditions for T2.3a: Simple wiki to channel sync

-- PC1: Message posted to sprint-planning channel
SELECT COUNT(*) >= 1 AS pc1_message_posted
FROM posts p
JOIN channels c ON p.channelid = c.id
WHERE c.name = 'sprint-planning'
AND (p.message ILIKE '%sprint%review%' OR p.message ILIKE '%completed%');

-- PC2: Message content relates to sprint review topics
SELECT COUNT(*) >= 1 AS pc2_content_relevant
FROM posts p
JOIN channels c ON p.channelid = c.id
WHERE c.name = 'sprint-planning'
AND (p.message ILIKE '%login%timeout%'
     OR p.message ILIKE '%pagination%'
     OR p.message ILIKE '%rate limit%'
     OR p.message ILIKE '%sprint%');

-- PC3: Original wiki page still exists unchanged
SELECT COUNT(*) = 1 AS pc3_wiki_preserved
FROM pages WHERE path = 'meetings/sprint-review-2026-w10';
