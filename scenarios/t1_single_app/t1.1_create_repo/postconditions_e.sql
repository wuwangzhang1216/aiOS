-- Postconditions for T1.1e: Duplicate name handling

-- PC1: Original "backend-api" still exists (not corrupted)
SELECT COUNT(*) = 1 AS pc1_original_exists
FROM repository
WHERE lower_name = 'backend-api';

-- PC2: Either the agent detected the conflict, or created backend-api-v2
SELECT (
    -- The v2 repo exists
    (SELECT COUNT(*) FROM repository WHERE lower_name = 'backend-api-v2') = 1
    OR
    -- Or the original still has exactly 1 entry (agent detected conflict, didn't create duplicate)
    (SELECT COUNT(*) FROM repository WHERE lower_name = 'backend-api') = 1
) AS pc2_conflict_handled;

-- PC3: No duplicate backend-api entries
SELECT COUNT(*) = 1 AS pc3_no_duplicates
FROM repository
WHERE lower_name = 'backend-api';
