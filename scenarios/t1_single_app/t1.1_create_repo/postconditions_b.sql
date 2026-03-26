-- Postconditions for T1.1b: Create repo with unicode name

-- PC1: Repository exists with correct unicode name
SELECT COUNT(*) = 1 AS pc1_repo_exists
FROM repository
WHERE lower_name = '测试仓库-unicode';

-- PC2: Repository has correct unicode description
SELECT description LIKE '%Unicode test%' AS pc2_description_has_prefix
FROM repository
WHERE lower_name = '测试仓库-unicode';

-- PC3: Repository is owned by alice
SELECT EXISTS (
    SELECT 1 FROM repository r
    JOIN "user" u ON r.owner_id = u.id
    WHERE r.lower_name = '测试仓库-unicode'
    AND u.lower_name = 'alice'
) AS pc3_owner_correct;
