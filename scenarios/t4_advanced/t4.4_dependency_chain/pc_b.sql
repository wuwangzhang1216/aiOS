-- Alice's message: "Completed: login timeout fix (#3), pagination (#2). Starting: rate limiting (#4)"
-- Agent should close issues matching "login timeout" and "pagination", NOT "rate limiting"
-- Issue titles: "Fix login timeout issue" (id=1), "Add pagination to /api/users" (id=2)

-- PC1: "Fix login timeout issue" is closed
SELECT 1 FROM issue WHERE name = 'Fix login timeout issue'
  AND repo_id = (SELECT id FROM repository WHERE lower_name = 'backend-api')
  AND is_closed = true;

-- PC2: "Add pagination to /api/users" is closed
SELECT 1 FROM issue WHERE name = 'Add pagination to /api/users'
  AND repo_id = (SELECT id FROM repository WHERE lower_name = 'backend-api')
  AND is_closed = true;

-- PC3: Verification task created for login timeout
SELECT 1 FROM tasks WHERE title = 'Verify closure: Fix login timeout issue'
  AND project_id = (SELECT id FROM projects WHERE title = 'Backend API')
  AND priority = 1;

-- PC4: Verification task created for pagination
SELECT 1 FROM tasks WHERE title = 'Verify closure: Add pagination to /api/users'
  AND project_id = (SELECT id FROM projects WHERE title = 'Backend API')
  AND priority = 1;

-- PC5: "Add rate limiting middleware" must NOT be closed (alice said "Starting")
SELECT 1 FROM issue WHERE name = 'Add rate limiting middleware'
  AND repo_id = (SELECT id FROM repository WHERE lower_name = 'backend-api')
  AND is_closed = false;
