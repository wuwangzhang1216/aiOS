# Database-as-Interface vs. Tool-per-Application: An Empirical Evaluation of Integration Paradigms for LLM-Based Operating System Agents

## Abstract

The emergence of AI-native operating systems necessitates a principled approach to integrating LLM agents with heterogeneous application ecosystems. Two dominant paradigms have emerged: *direct database access* via a universal shell interface, and *per-application tool APIs* exemplified by the Model Context Protocol (MCP). We present a controlled empirical comparison of these paradigms across 4 self-hosted applications, 31 task scenarios spanning 4 difficulty tiers, 4 LLM backends, and 3 independent runs per configuration (N=744 total evaluations). Our results demonstrate that the database-as-interface approach achieves a mean pass rate of 75.8% across models, compared to 27.4% for MCP (p < 0.001 by McNemar's test on paired outcomes). This advantage is consistent across all four models tested, including minimax-m2.7 (89% vs. 26%), mimo-v2-pro (89% vs. 33%), GPT-5.4-mini (81% vs. 26%), and Gemini-3-Flash (44% vs. 25%). MCP consumes 2.2x more tokens on average, driven by per-turn schema overhead that scales with the number of registered tools. Critically, both paradigms achieve comparable wall-clock latency, and tool invocation counts are similar, indicating that MCP's token penalty is structural rather than operational. These findings have implications for the design of agentic operating systems and the role of application-layer abstractions in LLM tool use.

## 1. Introduction

### 1.1 Motivation

As large language models demonstrate increasing capability in tool use and multi-step reasoning, a natural question arises: how should an AI agent interact with the diverse software ecosystem of a personal or organizational computing environment? The conventional approach—wrapping each application in a bespoke API and exposing it as a structured tool—has been formalized by protocols such as MCP (Model Context Protocol). An alternative, less explored in the literature, is to bypass application APIs entirely and interact with the underlying data layer, typically a relational database accessible via SQL.

This paper presents what is, to our knowledge, the first controlled head-to-head comparison of these two paradigms under identical task specifications, evaluation criteria, and LLM backends.

### 1.2 Research Questions

- **RQ1**: Does the choice of integration paradigm (database vs. API tools) affect task completion rates for LLM agents?
- **RQ2**: How do the paradigms compare in terms of token efficiency, latency, and tool invocation patterns?
- **RQ3**: Are these effects consistent across different LLM backends and task complexity levels?

## 2. Experimental Design

### 2.1 Application Testbed

We deploy four self-hosted, open-source applications, each backed by a PostgreSQL database:

| Application | Domain | Version | Key Entities | DB Tables |
|-------------|--------|---------|-------------|-----------|
| Gitea | Git hosting & issue tracking | 1.22 | repositories, issues, labels, users | ~40 |
| Miniflux | RSS feed reader | 2.1 | feeds, entries, categories | ~10 |
| Vikunja | Task & project management | 2.2 | tasks, projects, labels, users | ~30 |
| Mattermost | Team messaging | 9.x | channels, posts, users, teams | ~50 |

All applications run as Docker containers with dedicated PostgreSQL instances. Seed data provides a realistic baseline: 2 users (alice, bob), 1 Gitea repository with 5 issues and 5 labels, 3 RSS feeds with entries, 2 Vikunja projects with 5 tasks and 4 labels, and 5 Mattermost channels with 7 messages.

### 2.2 Treatment Arms

**bash+SQL (database-as-interface)**: The agent is provided a single `bash` tool. A system prompt (~800 tokens) lists database connection parameters for all four applications. The agent discovers schemas via `\dt` and `\d table`, reads data via `SELECT`, and writes via `INSERT`/`UPDATE`, all through `docker exec ... psql` commands.

**MCP (tool-per-application)**: The agent is provided 63 MCP tools aggregated from four community-maintained MCP servers: Gitea (11 tools), Miniflux (5 tools), Vikunja (31 tools), and Mattermost (16 tools). Tool schemas are transmitted in every LLM request, consuming approximately 8,214 tokens per turn. Each server communicates via JSON-RPC over stdio, and tools are prefixed with the application name (e.g., `gitea__list_issues`, `vikunja__tasks_create`).

### 2.3 Task Scenarios

We design 31 task variants organized into four tiers of increasing complexity:

| Tier | Category | Variants | Description |
|------|----------|----------|-------------|
| T1 | Single-app CRUD | 13 | Create repositories, tasks, messages; query with filters; update records |
| T2 | Cross-app workflow | 6 | Read from one application, write to another (e.g., RSS entry → task) |
| T3 | Multi-hop aggregation | 2 | Aggregate data from 3-4 applications into a formatted digest |
| T4 | Advanced operations | 10 | Idempotent upserts, exact-format aggregation, multi-step dependency chains, transactional consistency |

All task descriptions use natural language exclusively, with no database column names, SQL syntax, or implementation-specific terminology. This ensures neither arm receives implicit hints about the underlying data representation.

### 2.4 Evaluation Protocol

Each task defines one or more **postconditions**: SQL queries executed against the database that return TRUE if the task was completed correctly. Multi-check scenarios (T4) use file-based postconditions with partial scoring (score = fraction of checks passed). A task is classified as PASS if score >= 0.75, PARTIAL if 0 < score < 0.75, and FAIL if score = 0.

**Database reset**: Between each task evaluation, all databases are cleaned and reseeded to the canonical baseline state, ensuring independence between trials.

### 2.5 LLM Backends

To assess generalizability, we test four models via the OpenRouter API gateway:

| Model | Provider | Parameter Class |
|-------|----------|----------------|
| minimax-m2.7 | MiniMax | Large |
| mimo-v2-pro | Xiaomi | Large |
| GPT-5.4-mini | OpenAI | Medium |
| Gemini-3-Flash-Preview | Google | Medium-Fast |

All models are evaluated at temperature 0, max output tokens 4,096, and a maximum of 30 agent turns per task. The OpenRouter `provider.sort=throughput` setting is used to select the fastest available endpoint.

### 2.6 Sample Size

Each of the 31 variants is evaluated 3 times per model per arm, yielding:

$$N = 31 \text{ variants} \times 4 \text{ models} \times 3 \text{ runs} \times 2 \text{ arms} = 744 \text{ total evaluations}$$

## 3. Results

### 3.1 Overall Pass Rates (RQ1)

| Model | SQL Pass Rate | MCP Pass Rate | Delta |
|-------|:------------:|:-------------:|:-----:|
| minimax-m2.7 | **89.2%** (83/93) | 25.8% (24/93) | +63.4 pp |
| mimo-v2-pro | **89.2%** (83/93) | 33.3% (31/93) | +55.9 pp |
| GPT-5.4-mini | **80.6%** (75/93) | 25.8% (24/93) | +54.8 pp |
| Gemini-3-Flash | **44.1%** (41/93) | 24.7% (23/93) | +19.4 pp |
| **Pooled** | **75.8%** (282/372) | **27.4%** (102/372) | **+48.4 pp** |

The SQL arm outperforms MCP on every model tested. The effect is largest for the strongest models (minimax and mimo, +60 pp) and smallest for the weakest model (Gemini-3-Flash, +19 pp), suggesting that stronger models benefit more from the flexibility of direct database access.

### 3.2 Per-Tier Breakdown (RQ3)

| Tier | SQL (pooled) | MCP (pooled) | SQL Adv. |
|------|:-----------:|:------------:|:--------:|
| T1: Single App (13 var × 12 runs) | 141/156 (90.4%) | 56/156 (35.9%) | +54.5 pp |
| T2: Cross App (6 var × 12 runs) | 57/72 (79.2%) | 19/72 (26.4%) | +52.8 pp |
| T3: Multi Hop (2 var × 12 runs) | 16/24 (66.7%) | 15/24 (62.5%) | +4.2 pp |
| T4: Advanced (10 var × 12 runs) | 68/120 (56.7%) | 12/120 (10.0%) | +46.7 pp |

**T3 is the only tier where MCP approaches parity with SQL.** These tasks (weekly digest, per-person activity report) involve reading data from multiple applications and composing a text summary—operations well-served by MCP's structured read tools. However, even here, MCP consumes substantially more tokens (see Section 3.3).

**T4 reveals the largest gap.** Tasks requiring exact-format output, conditional logic (update-or-create), cross-database aggregation (COUNT queries), and multi-step dependency chains expose fundamental limitations of the MCP tool interface. SQL agents can express JOINs, GROUP BY, COUNT, and conditional INSERT in a single query; MCP agents must orchestrate multiple tool calls, manually accumulate counts, and handle pagination—often unsuccessfully.

### 3.3 Token Efficiency (RQ2)

| Model | SQL Avg Tokens | MCP Avg Tokens | Ratio |
|-------|:--------------:|:--------------:|:-----:|
| minimax-m2.7 | 46,700 | 117,432 | 2.5x |
| mimo-v2-pro | 33,348 | 146,698 | 4.4x |
| Gemini-3-Flash | 13,664 | 98,487 | 7.2x |
| GPT-5.4-mini | 24,274 | 18,492 | 0.8x |
| **Pooled** | **29,497** | **95,277** | **3.2x** |

MCP consumes 3.2x more tokens on average. The exception is GPT-5.4-mini, where MCP is actually more token-efficient (0.8x)—this model produces extremely concise tool calls and terminates early (often within 2-3 turns), even when the task is incomplete. The high MCP token cost for other models is driven by the 63-tool schema (~8,214 tokens) transmitted in every API request, creating an overhead of:

$$\text{Schema overhead} = 8{,}214 \times T \text{ tokens per task}$$

where $T$ is the number of agent turns. For a typical 10-turn task, this adds ~82,000 tokens of pure schema overhead—explaining nearly the entire SQL-MCP token gap.

### 3.4 Latency

| Model | SQL Avg Time | MCP Avg Time |
|-------|:------------:|:------------:|
| minimax-m2.7 | 482.1s* | 36.3s |
| mimo-v2-pro | 52.5s | 48.9s |
| Gemini-3-Flash | 66.1s | 45.2s |
| GPT-5.4-mini | 11.1s | 5.5s |

*minimax-m2.7 SQL time includes outlier runs with LLM retries.

Wall-clock time is comparable between arms for most models, despite MCP's higher token count. This is because MCP tool executions (HTTP API calls) are faster than SQL tool executions (`docker exec psql` subprocess invocations). The faster tool execution partially offsets the increased LLM inference time from larger prompts.

### 3.5 Per-Model Per-Tier Heatmap

Pass rates by model × tier × arm (out of respective totals):

```
                    T1          T2          T3          T4
Model          SQL   MCP   SQL   MCP   SQL   MCP   SQL   MCP
─────────────────────────────────────────────────────────────
minimax-m2.7   100%  36%   94%   17%  100%   67%   70%   10%
mimo-v2-pro    100%  38%   94%   39%  100%  100%   70%   10%
GPT-5.4-mini    97%  31%   78%   33%   67%   50%   63%   10%
Gemini-3-Flash  64%  38%   50%   17%    0%   33%   23%   10%
```

**Key observations:**
- SQL achieves 100% on T1 for three of four models; MCP never exceeds 38% on T1.
- T4 MCP pass rate is uniformly 10% regardless of model capability—the bottleneck is the tool interface, not the model.
- mimo-v2-pro achieves 100% on T3 for both arms, demonstrating that read-heavy aggregation is MCP's strongest scenario.

## 4. Analysis

### 4.1 Why SQL Outperforms MCP on Write Operations

Transcript analysis reveals that MCP failures concentrate on write operations (create, update, delete). Three root causes emerge:

1. **Permission scoping**: MCP tool tokens authenticate as a service user who may lack write access to resources owned by other users. SQL operates as `agent_rw` with blanket INSERT/UPDATE permissions.

2. **Tool coverage gaps**: Community MCP servers expose incomplete CRUD surfaces. For example, the Gitea MCP server can list repositories but cannot create repositories owned by arbitrary users. The Vikunja MCP server has 31 tools but lacks a direct "update task priority" endpoint.

3. **Implicit constraints**: Applications enforce business logic through their APIs that does not exist at the database level. Mattermost requires channel membership to post messages; Vikunja requires project ownership to create tasks. SQL bypasses these constraints entirely.

### 4.2 Structural Token Overhead

MCP's token penalty is not caused by agents making more tool calls. Across all evaluations, the mean number of tool invocations per task is 13.2 (SQL) vs. 14.9 (MCP)—a negligible difference. The 3.2x token gap is almost entirely attributable to transmitting 63 tool schemas in every LLM API request.

This overhead scales as $O(A \times T_A \times N)$, where $A$ is the number of applications, $T_A$ is the average tools per application, and $N$ is the number of agent turns. For our 4-application setup:

$$\text{Per-task overhead} \approx 4 \times 15.75 \times N \times 130 \approx 8{,}190 \times N \text{ tokens}$$

Extrapolating to 10 applications (~160 tools), the per-turn overhead would exceed 21,000 tokens, making MCP increasingly impractical as application count grows.

### 4.3 SQL's Composability Advantage

SQL provides three capabilities that MCP lacks as a native primitive:

1. **JOINs**: A single SQL statement can correlate data across tables (e.g., issues with labels, tasks with projects). MCP requires sequential tool calls with manual correlation.

2. **Aggregation**: COUNT, GROUP BY, and HAVING are single-query operations in SQL. MCP agents must paginate through list endpoints and count manually—a process that consumed up to 50 tool calls and 459k tokens in T4.2a.

3. **Atomic transactions**: SQL supports BEGIN/INSERT/INSERT/COMMIT across related tables. MCP provides no transaction semantics; partial failures leave inconsistent state.

### 4.4 MCP's Relative Strengths

MCP achieves near-parity with SQL on T3 (multi-hop read + summarize) tasks, and in some configurations (mimo-v2-pro T3) achieves 100% pass rate. These tasks align well with MCP's design: structured read operations with clear entity semantics, no complex filtering, and write operations limited to posting text messages. MCP tools also return structured data that requires less parsing than raw `psql` output, reducing error rates in the data extraction phase.

## 5. Threats to Validity

**Internal validity:**
- *Postcondition bias*: All postconditions are SQL queries that verify database state. MCP operations via API may produce correct user-visible effects that are stored differently than what postconditions check (e.g., different column encoding, application-level caching). This may systematically disadvantage MCP.
- *MCP server quality*: We use community-maintained MCP servers of varying maturity. Better-engineered servers with broader API coverage could improve MCP's write success rates.
- *Temperature determinism*: We use temperature=0, but OpenRouter's routing layer introduces non-determinism via backend selection. Three runs per configuration partially mitigates this.

**External validity:**
- *Application sample*: Four PostgreSQL-backed applications may not represent the full diversity of real-world software (NoSQL databases, SaaS APIs, desktop applications).
- *Scale*: Our extrapolation of token overhead to 10+ applications is theoretical; the actual scaling behavior requires empirical validation.
- *Model sample*: While we test four models spanning three providers, results may differ for frontier models (e.g., Claude Opus, GPT-5) with stronger tool-use capabilities.

**Construct validity:**
- *Task realism*: T4 tasks with exact output formatting (e.g., "OPEN_ISSUES: <N>") are more demanding than typical user requests and may not reflect real-world usage patterns. However, they serve to stress-test precision capabilities.

## 6. Related Work

Tool-augmented LLMs have been extensively studied (Schick et al., 2023; Qin et al., 2024), but the choice of *tool interface design* has received less attention. Most benchmarks (API-Bank, ToolBench) assume a fixed set of function-calling APIs. Our work differs by comparing *interface paradigms*—structured tool APIs versus a universal database interface—under controlled conditions.

The Model Context Protocol (MCP) was introduced by Anthropic (2024) as a standardized interface for LLM-application integration. To our knowledge, no prior work has empirically evaluated MCP's efficiency or accuracy against alternative integration approaches.

The concept of database-as-integration-layer has precedent in enterprise integration patterns (Hohpe & Woolf, 2003), but its application to LLM agents is novel.

## 7. Conclusion

Our results provide strong empirical evidence that, for the class of tasks studied, direct database access via a universal shell interface substantially outperforms per-application MCP tools in both accuracy (75.8% vs. 27.4%) and token efficiency (3.2x). This advantage is consistent across four LLM backends and four tiers of task complexity.

These findings suggest three design principles for AI-native operating systems:

1. **Prefer universal interfaces over per-application wrappers.** A single `bash` tool with database access provides strictly more capability than dozens of specialized tools—at lower token cost.

2. **Minimize tool schema surface area.** The per-turn cost of transmitting tool definitions dominates MCP's token budget. Architectures that reduce or amortize this overhead (e.g., tool selection, schema compression, or single-tool designs) will be more efficient.

3. **Leverage SQL's composability.** JOINs, aggregations, and transactions are primitives that agents can learn to use; decomposing them into multi-step tool workflows adds complexity and failure modes without adding capability.

We release all code, seed data, task definitions, evaluation scripts, and raw transcripts to facilitate replication and extension of this work.

## Data Availability

All experimental artifacts are available at the project repository:

| Artifact | Path | Description |
|----------|------|-------------|
| Raw results | `results/batch_both_multi.json` | 744 evaluation records with scores, tokens, latency |
| Summary statistics | `results/experiment_summary.json` | Aggregated per-model, per-tier statistics |
| Agent transcripts | `results/transcripts/{arm}/{model}/{variant}/` | Full conversation logs |
| Task definitions | `scenarios/t{1-4}_*/` | YAML scenario files with postconditions |
| Seed data | `seeds/*.sql` | Database initialization scripts |
| Agent code | `agent/agent.py`, `agent/mcp_agent.py` | Both agent implementations |
| MCP servers | `mcp_control/` | Server configuration and dependencies |
| Evaluation | `agent/verify_scenario.py` | Postcondition verification logic |

## Appendix A: Per-Variant Results (Pooled Across Models and Runs)

```
Variant    Tier  Category                SQL Pass  MCP Pass  SQL Tokens  MCP Tokens
──────────────────────────────────────────────────────────────────────────────────
T1.1a      T1    single_app_crud           11/12     2/12      30,847      13,684
T1.1b      T1    single_app_crud           11/12     1/12      31,524      21,159
T1.2a      T1    single_app_crud           12/12     3/12      14,254      36,488
T1.2b      T1    single_app_crud           12/12     4/12      13,721      23,167
T1.3a      T1    single_app_crud           11/12     4/12      18,006      42,327
T1.3b      T1    single_app_crud           11/12     3/12      22,614      49,887
T1.4a      T1    single_app_crud           12/12     7/12      20,181      23,461
T1.4b      T1    single_app_crud           10/12     3/12      27,397      59,783
T1.5a      T1    single_app_read           12/12     8/12      33,298      51,221
T1.5b      T1    single_app_read           12/12     7/12      35,879     182,418
T1.5c      T1    single_app_read           11/12     6/12      42,097     167,889
T1.6a      T1    single_app_update          8/12     5/12      26,714      67,143
T1.6b      T1    single_app_update          8/12     3/12      15,482      38,661
T2.1a      T2    cross_app_workflow        10/12     3/12      22,437      79,412
T2.1b      T2    cross_app_workflow        10/12     5/12      34,098      63,722
T2.2a      T2    cross_app_workflow         9/12     1/12      30,885     157,934
T2.2b      T2    cross_app_workflow         9/12     2/12      40,612      83,228
T2.3a      T2    cross_app_workflow        10/12     4/12      32,156      58,342
T2.3b      T2    cross_app_workflow         9/12     4/12      23,872      44,218
T3.1a      T3    multi_hop_workflow         8/12     8/12      41,892     201,443
T3.1b      T3    multi_hop_workflow         8/12     7/12      35,124      68,219
T4.1a      T4    conditional_logic         10/12     2/12      16,428      52,887
T4.1b      T4    conditional_logic         10/12     2/12      28,413     104,627
T4.2a      T4    complex_aggregation        3/12     0/12      42,218     198,443
T4.2b      T4    complex_aggregation        4/12     1/12      38,116      47,882
T4.3a      T4    data_transformation        9/12     3/12      39,228      41,667
T4.3b      T4    data_transformation        2/12     0/12      44,871      62,334
T4.4a      T4    multi_step_dependency      5/12     1/12      41,098     121,446
T4.4b      T4    multi_step_dependency      9/12     1/12      48,223     208,771
T4.5a      T4    transactional              6/12     1/12      33,614      63,827
T4.5b      T4    transactional             10/12     1/12      61,443      93,882
```
