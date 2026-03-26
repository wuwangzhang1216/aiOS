-- Wiki.js: Create scoped agent users with limited permissions
-- This runs on first DB initialization via docker-entrypoint-initdb.d

-- Read-only agent user
CREATE ROLE agent_ro LOGIN PASSWORD 'agent_wiki_pass';
GRANT CONNECT ON DATABASE wikijs TO agent_ro;
GRANT USAGE ON SCHEMA public TO agent_ro;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO agent_ro;

-- Read-write agent user (for experiment)
CREATE ROLE agent_rw LOGIN PASSWORD 'agent_wiki_pass';
GRANT CONNECT ON DATABASE wikijs TO agent_rw;
GRANT USAGE ON SCHEMA public TO agent_rw;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE ON TABLES TO agent_rw;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO agent_rw;
