"""
Dynamic system prompt generator.

Builds the agent's system prompt from the app registry,
tailored to the experimental arm (sql, api, or mcp).
"""

import json
import os
from pathlib import Path


def build_system_prompt(registry: dict, arm: str = "sql") -> str:
    """
    Build the system prompt for the agent based on the registry and arm.

    Args:
        registry: Parsed db_registry.json
        arm: Experimental arm - "sql", "api", or "mcp"

    Returns:
        Complete system prompt string
    """
    if arm == "sql":
        return _build_sql_prompt(registry)
    elif arm == "api":
        return _build_api_prompt(registry)
    elif arm == "mcp":
        return _build_mcp_prompt(registry)
    else:
        raise ValueError(f"Unknown arm: {arm}")


def _build_sql_prompt(registry: dict) -> str:
    """System prompt for the bash+SQL arm."""

    # Build app connection reference
    app_sections = []
    for app in registry["apps"]:
        conn = app["connection"]

        app_sections.append(
            f"### {app['name']} (id: {app['id']})\n"
            f"- Description: {app['description']}\n"
            f"- Database: {app['type']} — {conn['database']} (container: {conn['container']})\n"
            f"- Interactive: `{app['cli_connect']}`\n"
            f"- Single query: `{app['cli_command']} \"YOUR SQL HERE\"`\n"
            f"- Permissions: {', '.join(app['permissions'])}\n"
            f"- Key tables: {', '.join(app['key_tables'])}"
        )

    apps_text = "\n\n".join(app_sections)

    return f"""You are an AI agent operating as part of an AI-native operating system experiment.

## Your Capabilities
You have exactly ONE tool: **bash**. You use it to execute shell commands.

## Your Task
You interact with applications by directly accessing their databases using CLI tools (psql, mysql, mongosh) via bash.

## Available Applications

{apps_text}

## How to Work

1. **Discover schema first**: Before writing to any table, inspect its schema.
   - PostgreSQL: `\\dt` to list tables, `\\d table_name` to see columns
   - Or query: `SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'xxx' ORDER BY ordinal_position;`

2. **Read before write**: SELECT sample rows to understand data patterns, ID formats, and required fields.

3. **Use transactions for writes**: Wrap INSERT/UPDATE operations in BEGIN...COMMIT.
   ```
   psql ... -c "BEGIN; INSERT INTO ...; COMMIT;"
   ```

4. **Handle errors gracefully**: If a query fails, read the error, inspect the schema, and retry with corrected SQL.

5. **Cross-app workflows**: To move data between apps, SELECT from one database and use the results to INSERT into another. You can store intermediate data in shell variables or temporary files.

## Rules
- ALWAYS inspect schema before writing to a table you haven't seen before
- Use transactions for multi-step writes
- Respect permissions: only SELECT, INSERT, UPDATE (no DELETE, no DDL)
- Use `-t -A` flags with psql for clean output (no headers, no alignment)
- When querying for verification, use `-c` flag for single commands
- If you encounter an error, analyze it and try a different approach
- Report what you did and the results when you're finished

## Important
- You are in an experiment. Complete the task as accurately and efficiently as possible.
- Explain your reasoning briefly before each action.
- When done, summarize what you accomplished and any issues encountered.
"""


def _build_api_prompt(registry: dict) -> str:
    """System prompt for the bash+REST API arm."""

    # Build API reference with real tokens from env
    app_sections = []
    api_info = {
        "gitea": {
            "base_url": "http://localhost:3000/api/v1",
            "token_env": "GITEA_API_TOKEN",
            "auth_prefix": "token",
            "endpoints": [
                "GET /repos/search - Search repositories",
                "POST /user/repos - Create a repo: {\"name\":\"x\",\"description\":\"y\",\"auto_init\":true}",
                "GET /repos/{owner}/{repo} - Get repo details",
                "GET /repos/{owner}/{repo}/issues - List issues",
                "POST /repos/{owner}/{repo}/issues - Create issue: {\"title\":\"x\",\"body\":\"y\"}",
                "PATCH /repos/{owner}/{repo}/issues/{index} - Edit issue",
                "GET /repos/{owner}/{repo}/labels - List labels",
                "POST /repos/{owner}/{repo}/issues/{index}/labels - Add labels: {\"labels\":[id]}",
                "GET /users/{username} - Get user info",
            ],
        },
        "wikijs": {
            "base_url": "http://localhost:3001/graphql",
            "token_env": "WIKIJS_API_TOKEN",
            "auth_prefix": "Bearer",
            "type": "graphql",
            "endpoints": [
                "Query: { pages { list { id title path } } }",
                "Query: { pages { single(id:INT) { id title content path } } }",
                "Mutation: pages.create(content, description, editor:\"markdown\", isPublished:true, isPrivate:false, locale:\"en\", path, title)",
                "Mutation: pages.update(id, content, ...)",
                "Query: { pages { tags { id tag title } } }",
            ],
        },
        "mattermost": {
            "base_url": "http://localhost:3006/api/v4",
            "token_env": "MM_API_TOKEN",
            "auth_prefix": "Bearer",
            "endpoints": [
                "GET /teams - List teams",
                "GET /teams/name/{name} - Get team by name",
                "GET /teams/{team_id}/channels/name/{name} - Get channel by name",
                "POST /posts - Create post: {\"channel_id\":\"x\",\"message\":\"y\"}",
                "GET /channels/{channel_id}/posts - Get channel posts",
                "GET /users/username/{username} - Get user by username",
            ],
        },
    }

    for app in registry["apps"]:
        info = api_info.get(app["id"], {})
        token = os.environ.get(info.get("token_env", ""), "<NOT_SET>")
        base = info.get("base_url", "N/A")
        prefix = info.get("auth_prefix", "Bearer")
        endpoints = "\n".join(f"  - `{ep}`" for ep in info.get("endpoints", []))
        gql = info.get("type") == "graphql"

        if gql:
            example = f'curl -s {base} -H "Content-Type: application/json" -H "Authorization: {prefix} {token}" -d \'{{"query":"{{ pages {{ list {{ id title path }} }} }}"}}\''
        else:
            example = f'curl -s {base}/repos/search -H "Authorization: {prefix} {token}"'

        app_sections.append(
            f"### {app['name']} (id: {app['id']})\n"
            f"- Description: {app['description']}\n"
            f"- Base URL: `{base}`\n"
            f"- Auth header: `Authorization: {prefix} {token}`\n"
            f"- {'GraphQL' if gql else 'REST'} Endpoints:\n{endpoints}\n"
            f"- Example: `{example}`"
        )

    apps_text = "\n\n".join(app_sections)

    return f"""You are an AI agent operating as part of an AI-native operating system experiment.

## Your Capabilities
You have exactly ONE tool: **bash**. You use it to execute shell commands.

## Your Task
You interact with applications using their REST APIs via `curl` commands in bash.

## Available Applications

{apps_text}

## How to Work

1. **Discover API endpoints**: Use the app's API documentation or explore endpoints.
   - Most apps support: GET /api/v1/... for listing, POST for creation
   - Use `curl -s URL | jq .` to format JSON responses

2. **Authenticate**: Include auth headers in every request.

3. **Create resources**: Use POST with JSON body.
   ```bash
   curl -s -X POST "URL" -H "Content-Type: application/json" -H "Authorization: ..." -d '{{"key":"value"}}'
   ```

4. **Cross-app workflows**: Query one API, extract data with `jq`, and use it in another API call.

## Rules
- Always use `-s` (silent) flag with curl to suppress progress bars
- Use `jq` to parse JSON responses
- Use proper HTTP methods: GET for read, POST for create, PUT/PATCH for update
- Include Content-Type and Authorization headers
- Handle errors: check HTTP status codes
- Report what you did and the results when you're finished

## Important
- You are in an experiment. Complete the task as accurately and efficiently as possible.
- Explain your reasoning briefly before each action.
- When done, summarize what you accomplished and any issues encountered.
"""


def _build_mcp_prompt(registry: dict) -> str:
    """System prompt for the MCP arm (placeholder)."""
    return """You are an AI agent operating as part of an AI-native operating system experiment.

## Your Capabilities
You have MCP tools available for interacting with applications.

## Note
This is a placeholder. MCP tools will be configured based on available MCP servers
for each application. Only apps with existing community MCP servers will be tested
in this arm.
"""


if __name__ == "__main__":
    # Quick test: print the SQL prompt
    import sys

    registry_path = sys.argv[1] if len(sys.argv) > 1 else "../db_registry.json"
    with open(registry_path) as f:
        registry = json.load(f)

    arm = sys.argv[2] if len(sys.argv) > 2 else "sql"
    print(build_system_prompt(registry, arm=arm))
