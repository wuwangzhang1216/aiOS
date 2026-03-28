-- PC1: "bug" label with correct color
SELECT 1 FROM label WHERE repo_id = (SELECT id FROM repository WHERE lower_name = 'backend-api')
  AND name = 'bug' AND color = '#d73a4a';

-- PC2: "enhancement" label with updated color
SELECT 1 FROM label WHERE repo_id = (SELECT id FROM repository WHERE lower_name = 'backend-api')
  AND name = 'enhancement' AND color = '#84b6eb';

-- PC3: "security" label created
SELECT 1 FROM label WHERE repo_id = (SELECT id FROM repository WHERE lower_name = 'backend-api')
  AND name = 'security' AND color = '#e11d48';

-- PC4: "performance" label created
SELECT 1 FROM label WHERE repo_id = (SELECT id FROM repository WHERE lower_name = 'backend-api')
  AND name = 'performance' AND color = '#fbca04';

-- PC5: No duplicate label names
SELECT 1 WHERE NOT EXISTS (
  SELECT name FROM label
  WHERE repo_id = (SELECT id FROM repository WHERE lower_name = 'backend-api')
  GROUP BY name HAVING COUNT(*) > 1
);
