-- Postconditions for T1.1d: Create private repository

-- PC1: Repository exists
SELECT COUNT(*) = 1 AS pc1_repo_exists
FROM repository
WHERE lower_name = 'secret-project';

-- PC2: Repository IS private
SELECT is_private = true AS pc2_is_private
FROM repository
WHERE lower_name = 'secret-project';

-- PC3: Repository is owned by alice
SELECT EXISTS (
    SELECT 1 FROM repository r
    JOIN "user" u ON r.owner_id = u.id
    WHERE r.lower_name = 'secret-project'
    AND u.lower_name = 'alice'
) AS pc3_owner_correct;

-- PC4: Description is correct
SELECT description = 'Confidential project' AS pc4_description_correct
FROM repository
WHERE lower_name = 'secret-project';
