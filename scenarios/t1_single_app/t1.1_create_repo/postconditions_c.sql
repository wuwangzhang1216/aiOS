-- Postconditions for T1.1c: Create repo under organization context

-- PC1: Repository "shared-tools" exists
SELECT COUNT(*) = 1 AS pc1_repo_exists
FROM repository
WHERE lower_name = 'shared-tools';

-- PC2: Repository is owned by bob
SELECT EXISTS (
    SELECT 1 FROM repository r
    JOIN "user" u ON r.owner_id = u.id
    WHERE r.lower_name = 'shared-tools'
    AND u.lower_name = 'bob'
) AS pc2_owner_correct;

-- PC3: Repository has correct description
SELECT description = 'Shared engineering tools' AS pc3_description_correct
FROM repository
WHERE lower_name = 'shared-tools';
