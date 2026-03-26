# Bash + DB: The Two-Primitive AI-Native Operating System

**An Architecture Proof and Experimental Design**

*Steve Wu (Wangzhang Wu) · W Axis Inc. (doXmind)*
*Draft — March 2026*

---

## Abstract

We propose that an AI agent requires only two primitives to operate any software application: **bash** (execution) and **database access** (state). We argue that protocol layers such as MCP (Model Context Protocol) introduce unnecessary abstraction, and that a simpler architecture — where applications expose their database endpoints and agents speak SQL directly — is sufficient, more flexible, and more aligned with how an AI-native operating system should work.

To validate this thesis, we design and execute an experiment: deploying 10 popular open-source applications locally, each with its own database, and demonstrating that a single AI agent equipped with only a bash tool can perform meaningful cross-application workflows using raw SQL.

---

## 1. Motivation

### 1.1 Every SaaS App Is a Database with a UI

Strip away the frontend, the API layer, the webhooks, the SDKs — and every application reduces to:

```
App = Database + Business Logic + UI
```

Notion is PostgreSQL with a block editor. Linear is PostgreSQL with a kanban board. Slack is a message store with a chat interface. The data model is the application.

### 1.2 The MCP Tax

MCP and similar protocols (OpenAPI-based tool calling, LangChain tools, etc.) reconstruct the "API gateway" pattern for AI agents:

```
Agent → MCP Client → JSON-RPC → MCP Server → App Logic → Database
```

Each app must build and maintain an MCP server. Each server defines its own tool schema. The agent must discover tools, negotiate capabilities, and handle per-server authentication. This creates an O(N) integration cost where N is the number of apps.

### 1.3 The Alternative: Direct Database Access

If every app simply exposed its database with scoped tokens:

```
Agent → bash/psql → Database
```

The integration cost drops to O(1). SQL is a 50-year-old universal standard. Every relational database speaks it. The agent needs no per-app SDK, no protocol negotiation, no tool discovery — just a connection string.

---

## 2. Architecture

### 2.1 The Two Primitives

| Primitive | Role | Analogy |
|-----------|------|---------|
| **bash** | Execute arbitrary commands, orchestrate workflows, transform data, call CLI tools | The CPU — instruction execution |
| **SQL** (via database connections) | Read, write, query, join, and mutate application state | The memory bus — state access |

Together, these form a complete interface for an agent to interact with any application.

### 2.2 System Architecture

```
┌─────────────────────────────────────────────────┐
│                   AI Agent                       │
│        (LLM + System Prompt + Memory)            │
│                                                  │
│  Tools: [ bash ]                                 │
│  Credentials: [ db_tokens.json ]                 │
└───────────────┬─────────────────────────────────┘
                │
                │  bash: psql / mysql / sqlite3
                │
    ┌───────────┼───────────────────────────────┐
    │           │                               │
    ▼           ▼           ▼           ▼       ▼
┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐
│Gitea DB│ │Wiki DB │ │Todo DB │ │Chat DB │ │CRM DB  │
│ (PG)   │ │ (PG)   │ │(MySQL) │ │(MySQL) │ │ (PG)   │
└────────┘ └────────┘ └────────┘ └────────┘ └────────┘
    ▲           ▲           ▲           ▲       ▲
    │           │           │           │       │
┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐
│ Gitea  │ │ Wiki.js│ │Vikunja │ │Rocket  │ │Twenty  │
│ Server │ │ Server │ │ Server │ │  Chat  │ │  CRM   │
└────────┘ └────────┘ └────────┘ └────────┘ └────────┘
```

### 2.3 App Registry Schema

Each application registers itself with a simple JSON manifest:

```json
{
  "app_id": "gitea",
  "display_name": "Gitea",
  "description": "Self-hosted Git service",
  "db": {
    "type": "postgresql",
    "host": "localhost",
    "port": 5432,
    "database": "gitea",
    "schema": "public"
  },
  "auth": {
    "method": "token",
    "env_var": "GITEA_DB_TOKEN"
  },
  "capabilities": ["code", "issues", "pull_requests", "users", "repositories"]
}
```

The agent loads all registered apps from a `registry.json` file and uses bash to connect to any of them.

### 2.4 Agent System Prompt (Simplified)

```
You are an AI agent operating as an AI-native OS.
You have one tool: bash.
You have database credentials for the following apps:
{loaded from registry.json}

To interact with any app, use psql/mysql CLI via bash.
To discover schema, use \dt, \d table_name, or INFORMATION_SCHEMA.
To perform operations, write and execute SQL.
To chain workflows across apps, pipe data between queries.

Rules:
- Always inspect schema before writing to a table
- Use transactions for multi-step writes
- Respect permissions (read-only vs read-write per app)
```

---

## 3. Experiment Design

### 3.1 The 10 Applications

We select 10 popular open-source applications spanning common SaaS categories. All are self-hostable via Docker and use standard relational databases.

| # | App | Category | Database | Docker Image | Key Tables |
|---|-----|----------|----------|-------------|------------|
| 1 | **Gitea** | Code / Git | PostgreSQL | `gitea/gitea` | `repository`, `issue`, `pull_request`, `user`, `comment` |
| 2 | **Wiki.js** | Knowledge Base | PostgreSQL | `requarks/wiki` | `pages`, `pageHistory`, `comments`, `users`, `tags` |
| 3 | **Vikunja** | Task Management | MySQL | `vikunja/vikunja` | `tasks`, `projects`, `labels`, `teams`, `buckets` |
| 4 | **Rocket.Chat** | Messaging | MongoDB* | `rocket.chat` | `rocketchat_message`, `rocketchat_room`, `users` |
| 5 | **Twenty** | CRM | PostgreSQL | `twentycrm/twenty` | `person`, `company`, `opportunity`, `note`, `task` |
| 6 | **Nocodb** | Spreadsheet/DB | PostgreSQL | `nocodb/nocodb` | Dynamic per-base tables, `nc_users`, `nc_projects` |
| 7 | **Matterbridge** + **Mattermost** | Team Chat | PostgreSQL | `mattermost/mattermost` | `Posts`, `Channels`, `Users`, `Teams` |
| 8 | **Plane** | Project Management | PostgreSQL | `makeplane/plane` | `issues`, `projects`, `cycles`, `modules`, `states` |
| 9 | **Cal.com** | Scheduling | PostgreSQL | `calcom/cal.com` | `Booking`, `EventType`, `Availability`, `User`, `Schedule` |
| 10 | **Invoice Ninja** | Invoicing | MySQL | `invoiceninja/invoiceninja` | `invoices`, `clients`, `payments`, `products`, `quotes` |

> *Note: Rocket.Chat uses MongoDB. We include it to test whether the bash+db model extends beyond SQL to NoSQL (via `mongosh`). If the thesis holds, it should work with any query language the DB supports.

### 3.2 Infrastructure Setup

All apps run locally via Docker Compose. A single `docker-compose.yml` defines the full environment:

```yaml
version: '3.8'

services:
  # ── Databases ──
  postgres-gitea:
    image: postgres:16
    environment:
      POSTGRES_DB: gitea
      POSTGRES_USER: agent
      POSTGRES_PASSWORD: ${GITEA_DB_PASS}
    ports: ["5501:5432"]

  postgres-wiki:
    image: postgres:16
    environment:
      POSTGRES_DB: wikijs
      POSTGRES_USER: agent
      POSTGRES_PASSWORD: ${WIKI_DB_PASS}
    ports: ["5502:5432"]

  postgres-twenty:
    image: postgres:16
    environment:
      POSTGRES_DB: twenty
      POSTGRES_USER: agent
      POSTGRES_PASSWORD: ${TWENTY_DB_PASS}
    ports: ["5503:5432"]

  postgres-mattermost:
    image: postgres:16
    environment:
      POSTGRES_DB: mattermost
      POSTGRES_USER: agent
      POSTGRES_PASSWORD: ${MM_DB_PASS}
    ports: ["5504:5432"]

  postgres-plane:
    image: postgres:16
    environment:
      POSTGRES_DB: plane
      POSTGRES_USER: agent
      POSTGRES_PASSWORD: ${PLANE_DB_PASS}
    ports: ["5505:5432"]

  postgres-calcom:
    image: postgres:16
    environment:
      POSTGRES_DB: calcom
      POSTGRES_USER: agent
      POSTGRES_PASSWORD: ${CAL_DB_PASS}
    ports: ["5506:5432"]

  postgres-nocodb:
    image: postgres:16
    environment:
      POSTGRES_DB: nocodb
      POSTGRES_USER: agent
      POSTGRES_PASSWORD: ${NOCODB_DB_PASS}
    ports: ["5507:5432"]

  mysql-vikunja:
    image: mysql:8
    environment:
      MYSQL_DATABASE: vikunja
      MYSQL_USER: agent
      MYSQL_PASSWORD: ${VIKUNJA_DB_PASS}
      MYSQL_ROOT_PASSWORD: ${VIKUNJA_ROOT_PASS}
    ports: ["3501:3306"]

  mysql-invoiceninja:
    image: mysql:8
    environment:
      MYSQL_DATABASE: invoiceninja
      MYSQL_USER: agent
      MYSQL_PASSWORD: ${INVOICE_DB_PASS}
      MYSQL_ROOT_PASSWORD: ${INVOICE_ROOT_PASS}
    ports: ["3502:3306"]

  mongo-rocketchat:
    image: mongo:6
    ports: ["27501:27017"]

  # ── Applications ──
  gitea:
    image: gitea/gitea:latest
    depends_on: [postgres-gitea]
    ports: ["3000:3000"]
    environment:
      GITEA__database__DB_TYPE: postgres
      GITEA__database__HOST: postgres-gitea:5432
      GITEA__database__NAME: gitea
      GITEA__database__USER: agent
      GITEA__database__PASSWD: ${GITEA_DB_PASS}

  wikijs:
    image: requarks/wiki:2
    depends_on: [postgres-wiki]
    ports: ["3001:3000"]
    environment:
      DB_TYPE: postgres
      DB_HOST: postgres-wiki
      DB_PORT: 5432
      DB_USER: agent
      DB_PASS: ${WIKI_DB_PASS}
      DB_NAME: wikijs

  vikunja:
    image: vikunja/vikunja:latest
    depends_on: [mysql-vikunja]
    ports: ["3002:3456"]

  rocketchat:
    image: rocket.chat:latest
    depends_on: [mongo-rocketchat]
    ports: ["3003:3000"]

  twenty:
    image: twentycrm/twenty:latest
    depends_on: [postgres-twenty]
    ports: ["3004:3000"]

  nocodb:
    image: nocodb/nocodb:latest
    depends_on: [postgres-nocodb]
    ports: ["3005:8080"]

  mattermost:
    image: mattermost/mattermost-team-edition:latest
    depends_on: [postgres-mattermost]
    ports: ["3006:8065"]

  plane:
    image: makeplane/plane-ce:latest
    depends_on: [postgres-plane]
    ports: ["3007:80"]

  calcom:
    image: calcom/cal.com:latest
    depends_on: [postgres-calcom]
    ports: ["3008:3000"]

  invoiceninja:
    image: invoiceninja/invoiceninja:latest
    depends_on: [mysql-invoiceninja]
    ports: ["3009:9000"]
```

### 3.3 Database Credential Registry

The agent loads a single credential file:

```json
// db_registry.json
{
  "apps": [
    {
      "id": "gitea",
      "name": "Gitea (Code & Git)",
      "type": "postgresql",
      "connection": "postgresql://agent:${GITEA_DB_PASS}@localhost:5501/gitea",
      "cli": "psql",
      "permissions": ["read", "write"]
    },
    {
      "id": "wikijs",
      "name": "Wiki.js (Knowledge Base)",
      "type": "postgresql",
      "connection": "postgresql://agent:${WIKI_DB_PASS}@localhost:5502/wikijs",
      "cli": "psql",
      "permissions": ["read", "write"]
    },
    {
      "id": "vikunja",
      "name": "Vikunja (Tasks)",
      "type": "mysql",
      "connection": "mysql://agent:${VIKUNJA_DB_PASS}@localhost:3501/vikunja",
      "cli": "mysql",
      "permissions": ["read", "write"]
    },
    {
      "id": "rocketchat",
      "name": "Rocket.Chat (Messaging)",
      "type": "mongodb",
      "connection": "mongodb://localhost:27501/rocketchat",
      "cli": "mongosh",
      "permissions": ["read", "write"]
    },
    {
      "id": "twenty",
      "name": "Twenty CRM",
      "type": "postgresql",
      "connection": "postgresql://agent:${TWENTY_DB_PASS}@localhost:5503/twenty",
      "cli": "psql",
      "permissions": ["read", "write"]
    },
    {
      "id": "nocodb",
      "name": "NocoDB (Spreadsheet)",
      "type": "postgresql",
      "connection": "postgresql://agent:${NOCODB_DB_PASS}@localhost:5507/nocodb",
      "cli": "psql",
      "permissions": ["read", "write"]
    },
    {
      "id": "mattermost",
      "name": "Mattermost (Team Chat)",
      "type": "postgresql",
      "connection": "postgresql://agent:${MM_DB_PASS}@localhost:5504/mattermost",
      "cli": "psql",
      "permissions": ["read", "write"]
    },
    {
      "id": "plane",
      "name": "Plane (Project Management)",
      "type": "postgresql",
      "connection": "postgresql://agent:${PLANE_DB_PASS}@localhost:5505/plane",
      "cli": "psql",
      "permissions": ["read", "write"]
    },
    {
      "id": "calcom",
      "name": "Cal.com (Scheduling)",
      "type": "postgresql",
      "connection": "postgresql://agent:${CAL_DB_PASS}@localhost:5506/calcom",
      "cli": "psql",
      "permissions": ["read", "write"]
    },
    {
      "id": "invoiceninja",
      "name": "Invoice Ninja (Invoicing)",
      "type": "mysql",
      "connection": "mysql://agent:${INVOICE_DB_PASS}@localhost:3502/invoiceninja",
      "cli": "mysql",
      "permissions": ["read", "write"]
    }
  ]
}
```

### 3.4 Test Scenarios

We design 10 test scenarios that exercise single-app CRUD, cross-app workflows, and complex multi-hop operations.

#### Tier 1: Single-App CRUD (Baseline)

| # | Scenario | App | Operations |
|---|----------|-----|------------|
| T1.1 | Create a Git repository | Gitea | INSERT into `repository` |
| T1.2 | Create a task with labels | Vikunja | INSERT into `tasks`, `labels`, `label_tasks` |
| T1.3 | Send a message to a channel | Mattermost | INSERT into `Posts` |

#### Tier 2: Cross-App Workflows

| # | Scenario | Apps | Operations |
|---|----------|------|------------|
| T2.1 | Create issue from chat message | Mattermost → Plane | SELECT from `Posts` → INSERT into `issues` |
| T2.2 | Sync meeting notes to wiki | Cal.com → Wiki.js | SELECT from `Booking` → INSERT into `pages` |
| T2.3 | Generate invoice from completed tasks | Vikunja → Invoice Ninja | SELECT SUM from `tasks` → INSERT into `invoices` |
| T2.4 | Log CRM activity from email | Twenty → Wiki.js | INSERT into `note` + INSERT into `pages` |

#### Tier 3: Complex Multi-Hop Workflows

| # | Scenario | Apps | Operations |
|---|----------|------|------------|
| T3.1 | Sprint retrospective report | Plane + Gitea + Mattermost → Wiki.js | Aggregate issues, PRs, messages → generate wiki page |
| T3.2 | Client billing pipeline | Cal.com + Vikunja + Twenty → Invoice Ninja | Sum hours + match client + generate invoice |
| T3.3 | Onboarding automation | Twenty (new hire) → Gitea (repo access) + Mattermost (channel) + Plane (tasks) + Cal.com (onboarding meeting) | Cross-write into 4 apps from CRM trigger |

### 3.5 Evaluation Metrics

| Metric | Description | Target |
|--------|-------------|--------|
| **Task Completion Rate** | % of scenarios completed successfully | >90% |
| **SQL Operations per Task** | Number of SQL statements executed | Measure |
| **Schema Discovery Time** | Time for agent to understand a new app's schema | <30s |
| **Cross-App Join Feasibility** | Can data from multiple DBs be combined in one workflow? | Yes |
| **Error Recovery Rate** | Agent's ability to recover from SQL errors | >80% |
| **Token Efficiency** | Tokens consumed vs. equivalent MCP-based approach | <50% of MCP |
| **Latency** | End-to-end time per scenario | Measure |

### 3.6 Control Group: MCP Equivalent

For each scenario, we also implement the equivalent MCP-based approach using available MCP servers (where they exist) and measure the same metrics. This enables direct comparison.

---

## 4. Implementation Plan

### Phase 1: Infrastructure (Week 1)

- [ ] Write `docker-compose.yml` with all 10 apps
- [ ] Configure each app's initial setup (admin user, sample data)
- [ ] Create `db_registry.json` with all connection strings
- [ ] Write `seed.sql` per app — populate with realistic sample data
- [ ] Verify all databases are accessible via CLI from host

### Phase 2: Agent Setup (Week 2)

- [ ] Build agent harness (Python/Claude API) with single `bash` tool
- [ ] Implement system prompt with registry loading
- [ ] Add schema introspection helper (auto-run `\dt` on first connect)
- [ ] Build logging infrastructure (record all SQL, tokens, timing)
- [ ] Implement safety guardrails (transaction wrapping, read-only mode)

### Phase 3: Scenario Execution (Week 3)

- [ ] Execute all 10 test scenarios
- [ ] Record full transcripts (agent reasoning + SQL + results)
- [ ] Measure all evaluation metrics
- [ ] Document failure cases and error patterns
- [ ] Execute MCP control group (where possible)

### Phase 4: Analysis & Paper (Week 4)

- [ ] Compile results into comparison tables
- [ ] Analyze failure modes and limitations
- [ ] Write paper draft
- [ ] Create visualizations (latency, token usage, success rates)
- [ ] Prepare demo video

---

## 5. Anticipated Challenges & Mitigations

### 5.1 Security: Direct DB Access Is Dangerous

**Challenge:** Exposing database endpoints gives agents destructive power (DROP TABLE, DELETE FROM).

**Mitigation:**
- Scoped database users with per-table GRANT permissions
- Read-only mode by default, write-only for specific tables
- Transaction wrapping with explicit COMMIT requirement
- Row-level security (RLS) policies in PostgreSQL
- Agent system prompt enforces `BEGIN`/`ROLLBACK` patterns

```sql
-- Example: Scoped agent user for Gitea
CREATE ROLE agent_gitea LOGIN PASSWORD 'xxx';
GRANT SELECT ON ALL TABLES IN SCHEMA public TO agent_gitea;
GRANT INSERT, UPDATE ON issue, comment TO agent_gitea;
-- No DELETE, no DDL
```

### 5.2 Schema Complexity & Undocumented Columns

**Challenge:** Real app schemas have hundreds of tables with non-obvious column meanings.

**Mitigation:**
- Agent starts with `\dt` then `\d table_name` to introspect
- LLMs are excellent at inferring column semantics from names
- We provide a lightweight `schema_hints.json` per app (optional enrichment)
- The agent can SELECT sample rows to understand data patterns

### 5.3 Business Logic Bypass

**Challenge:** Direct DB writes skip application validation (e.g., Gitea's permission checks, webhook triggers).

**Mitigation:**
- This is the core trade-off: power vs. safety
- For the experiment, we accept this and document which operations require app-layer logic
- In production, apps could expose a "validated write" endpoint alongside raw DB access
- Foreign keys and CHECK constraints still enforce data integrity at DB level

### 5.4 MongoDB / NoSQL Apps

**Challenge:** Not all apps use SQL. Rocket.Chat uses MongoDB.

**Mitigation:**
- The thesis generalizes: bash + **query language** (SQL, MQL, etc.)
- `mongosh` is the bash-callable CLI for MongoDB
- The agent uses `db.collection.find()` and `db.collection.insertOne()` instead of SQL
- If this works, it strengthens the argument that the pattern is universal

### 5.5 Schema Migrations & Breaking Changes

**Challenge:** App updates may change the schema, breaking agent queries.

**Mitigation:**
- Agent uses introspection (`\dt`, `\d`) at runtime, not hardcoded schemas
- Schema changes are detectable: agent can diff current schema vs. cached
- This is actually an advantage over MCP: no need to update server code per migration

---

## 6. Theoretical Analysis

### 6.1 Why This Works: The Expressiveness Argument

SQL is Turing-complete (with recursive CTEs). Any operation that an MCP tool exposes can be expressed as SQL, because every MCP tool ultimately translates to database operations. The MCP layer adds expressiveness overhead (tool schemas, JSON-RPC, transport) without adding computational power.

```
Expressiveness(bash + SQL) ≥ Expressiveness(MCP tools)
```

### 6.2 Complexity Analysis

| | MCP Model | Bash+DB Model |
|---|-----------|---------------|
| New app integration | O(N) — build N MCP servers | O(1) — expose DB endpoint |
| Agent tool count | O(N × T) — N apps × T tools each | O(1) — one bash tool |
| Context window cost | O(N × T × S) — tool schemas | O(1) — single tool schema |
| Cross-app operation | O(K) hops — K MCP calls | O(1) — single SQL join or bash pipe |

### 6.3 The AI-Native OS Analogy

| Traditional OS | AI-Native OS (Proposed) |
|----------------|------------------------|
| Kernel | LLM (reasoning engine) |
| System calls | bash (execution primitive) |
| Filesystem | Databases (state primitive) |
| Drivers | DB connection strings (per-app adapters) |
| APIs/SDKs | SQL (universal query language) |
| Process model | Agent loop (observe → reason → act) |

---

## 7. Related Work

- **MCP (Model Context Protocol)** — Anthropic, 2024. Standardized protocol for LLM-tool interaction. Our work argues this layer is unnecessary when apps expose databases directly.
- **Computer Use / Browser Use** — Anthropic, 2024; various. Agents operate apps through UI simulation. Our approach is strictly more efficient: skip the UI, access the data layer.
- **Text-to-SQL** — A large body of research (Spider, WikiSQL, BIRD, etc.) demonstrates that LLMs can generate accurate SQL from natural language. Our work leverages this capability in a systems context.
- **AutoGPT / Open Interpreter** — Early agent frameworks that use bash/code execution as a primary tool. Our work formalizes and narrows this to the database-access pattern specifically.
- **Datasette / PostgREST** — Tools that auto-generate APIs from database schemas. These validate our premise: the database IS the API.

---

## 8. Paper Outline (Draft)

**Title:** *"Bash and Database: Two Primitives Are All an AI Agent Needs"*

1. **Introduction** — The protocol proliferation problem. MCP, OpenAPI, LangChain tools all reconstruct the API gateway for AI. We propose a simpler alternative.

2. **Background** — MCP architecture, text-to-SQL, agent frameworks.

3. **Architecture** — The two-primitive model. App registry. Agent system prompt. Security model.

4. **Experiment** — 10 apps, 10 scenarios, metrics, control group.

5. **Results** — Task completion rates, token efficiency, latency, failure analysis.

6. **Discussion** — Trade-offs (security, business logic bypass, schema coupling). When MCP is still needed (event streams, real-time subscriptions). The continuum between raw DB and full protocol.

7. **Future Work** — AI-native OS design, automatic schema mapping, federated query engines (FDW), event-driven DB triggers as webhook replacements.

8. **Conclusion** — The best middleware is no middleware. For the majority of agent-app interactions, bash + database access is sufficient, simpler, and more powerful than protocol-based approaches.

---

## 9. Quick Start

```bash
# 1. Clone the experiment repo
git clone https://github.com/user/bash-db-agent-os
cd bash-db-agent-os

# 2. Start all apps
cp .env.example .env  # Set your passwords
docker compose up -d

# 3. Seed sample data
./scripts/seed-all.sh

# 4. Verify database connectivity
./scripts/verify-connections.sh

# 5. Run agent scenarios
python agent/run_scenarios.py --all --log-dir results/

# 6. Generate report
python agent/generate_report.py results/ --output paper/results.md
```

---

## 10. File Structure

```
bash-db-agent-os/
├── docker-compose.yml          # All 10 apps + databases
├── .env.example                # Database passwords template
├── db_registry.json            # App connection registry
├── schema_hints/               # Optional schema annotations
│   ├── gitea.json
│   ├── wikijs.json
│   ├── vikunja.json
│   ├── rocketchat.json
│   ├── twenty.json
│   ├── nocodb.json
│   ├── mattermost.json
│   ├── plane.json
│   ├── calcom.json
│   └── invoiceninja.json
├── seeds/                      # Sample data per app
│   ├── gitea.sql
│   ├── wikijs.sql
│   ├── vikunja.sql
│   └── ...
├── scenarios/                  # Test scenario definitions
│   ├── t1_single_app/
│   │   ├── t1.1_create_repo.yaml
│   │   ├── t1.2_create_task.yaml
│   │   └── t1.3_send_message.yaml
│   ├── t2_cross_app/
│   │   ├── t2.1_chat_to_issue.yaml
│   │   ├── t2.2_meeting_to_wiki.yaml
│   │   ├── t2.3_tasks_to_invoice.yaml
│   │   └── t2.4_crm_to_wiki.yaml
│   └── t3_multi_hop/
│       ├── t3.1_sprint_retro.yaml
│       ├── t3.2_billing_pipeline.yaml
│       └── t3.3_onboarding.yaml
├── agent/
│   ├── agent.py                # Core agent loop (Claude API + bash tool)
│   ├── system_prompt.py        # System prompt generator
│   ├── run_scenarios.py        # Scenario runner
│   ├── generate_report.py      # Results analyzer
│   └── safety.py               # Transaction wrapping, guardrails
├── mcp_control/                # MCP-based control group
│   ├── mcp_agent.py
│   └── mcp_servers/
├── results/                    # Experiment output
│   ├── transcripts/
│   ├── metrics/
│   └── comparison/
├── paper/
│   ├── main.tex
│   ├── figures/
│   └── results.md
└── scripts/
    ├── seed-all.sh
    ├── verify-connections.sh
    └── reset-all.sh
```

---

## License

MIT — W Axis Inc., 2026
