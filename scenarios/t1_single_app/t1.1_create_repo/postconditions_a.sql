-- Postconditions for T1.1a: Create repo with default settings
-- Each query must return TRUE for the postcondition to pass

-- PC1: Repository exists with correct name
SELECT COUNT(*) = 1 AS pc1_repo_exists
FROM repository
WHERE lower_name = 'test-repo-default';

-- PC2: Repository has correct description
SELECT description = 'A test repository created by the AI agent' AS pc2_description_correct
FROM repository
WHERE lower_name = 'test-repo-default';

-- PC3: Repository is owned by alice
SELECT EXISTS (
    SELECT 1 FROM repository r
    JOIN "user" u ON r.owner_id = u.id
    WHERE r.lower_name = 'test-repo-default'
    AND u.lower_name = 'alice'
) AS pc3_owner_correct;

-- PC4: Repository is public (not private)
SELECT is_private = false AS pc4_is_public
FROM repository
WHERE lower_name = 'test-repo-default';

-- PC5: Repository is not a fork
SELECT is_fork = false AS pc5_not_fork
FROM repository
WHERE lower_name = 'test-repo-default';
