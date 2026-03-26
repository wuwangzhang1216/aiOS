# Bash+DB Arm Results — March 20, 2026

## Experiment Config
- **Model**: minimax/minimax-m2.7 (via OpenRouter, throughput-sorted)
- **Temperature**: 0
- **Max turns**: 20
- **Parallel workers**: 6
- **Total runs**: 54 attempted, 53 completed (1 hung on C6.3)
- **Errors**: 3 runs failed with NoneType (Windows encoding issue, not agent logic)

## Summary by Category

| Category | Runs | Success | Avg Tokens | Avg Turns | Avg Time |
|----------|------|---------|-----------|-----------|----------|
| Schema Discovery (C1) | 9 | **9/9 (100%)** | **9,600** | 3.9 | 20.0s |
| Single-App Read (C2) | 9 | 7/9 (78%) | 31,899 | 12.6 | 21.7s |
| Single-App Write (C3) | 8 | **8/8 (100%)** | 56,540 | 14.5 | 34.3s |
| Cross-App Read (C4) | 9 | **9/9 (100%)** | **14,287** | 5.9 | 15.6s |
| Cross-App Workflow (C5) | 9 | 8/9 (89%) | 63,988 | 16.4 | 35.7s |
| Multi-App Aggregation (C6) | 9 | **9/9 (100%)** | 72,057 | 10.7 | 48.1s |
| **TOTAL** | **53** | **50/53 (94%)** | **41,020** | **10.7** | **29.3s** |

## Totals
- **Total tokens consumed**: 2,051,014
- **Total wall time**: ~25 minutes (with 6-worker parallelism)
- **Overall success rate**: 94% (50/53)

## Per-Task Breakdown

### C1: Schema Discovery
| Task | r1 | r2 | r3 | Avg Tokens |
|------|----|----|-----|-----------|
| C1.1 (Gitea tables) | 3,520 / 2t | 8,020 / 4t | 8,059 / 4t | 6,533 |
| C1.2 (Miniflux model) | 10,801 / 3t | 15,011 / 4t | 15,797 / 4t | 13,870 |
| C1.3 (All 10 apps) | 11,424 / 6t | 7,096 / 4t | 6,669 / 4t | 8,396 |

### C2: Single-App Read
| Task | r1 | r2 | r3 | Avg Tokens |
|------|----|----|-----|-----------|
| C2.1 (Gitea issues) | 15,509 / 7t | 26,075 / 9t | ERR | 20,792 |
| C2.2 (MM messages) | 23,981 / 10t | 59,582 / 20t | ERR | 41,782 |
| C2.3 (Wiki page) | 25,921 / 12t | 27,230 / 13t | 44,994 / 17t | 32,715 |

### C3: Single-App Write
| Task | r1 | r2 | r3 | Avg Tokens |
|------|----|----|-----|-----------|
| C3.1 (Create repo) | 104,019 / 20t | 43,617 / 12t | — | 73,818 |
| C3.2 (Create wiki page) | 87,132 / 20t | 68,921 / 20t | 60,343 / 18t | 72,132 |
| C3.3 (Post message) | 62,183 / 15t | 11,441 / 5t | 14,668 / 6t | 29,431 |

### C4: Cross-App Read
| Task | r1 | r2 | r3 | Avg Tokens |
|------|----|----|-----|-----------|
| C4.1 (Issues+channels) | 19,018 / 7t | 25,418 / 7t | 29,555 / 10t | 24,664 |
| C4.2 (User diff) | 17,595 / 6t | 8,503 / 5t | 12,801 / 6t | 12,966 |
| C4.3 (Repo-wiki match) | 5,028 / 4t | 7,488 / 5t | 3,177 / 3t | 5,231 |

### C5: Cross-App Workflow
| Task | r1 | r2 | r3 | Avg Tokens |
|------|----|----|-----|-----------|
| C5.1 (Issues→wiki) | 105,818 / 20t | 51,311 / 16t | 78,747 / 18t | 78,625 |
| C5.2 (Chat→issue) | 71,457 / 20t | 107,806 / 20t | ERR | 89,632 |
| C5.3 (Wiki→chat) | 29,429 / 14t | 14,941 / 8t | 52,398 / 15t | 32,256 |

### C6: Multi-App Aggregation
| Task | r1 | r2 | r3 | Avg Tokens |
|------|----|----|-----|-----------|
| C6.1 (User count) | 38,957 / 9t | 191,562 / 18t | 26,036 / 8t | 85,518 |
| C6.2 (Activity dash) | 145,478 / 17t | 45,964 / 11t | 29,595 / 6t | 73,679 |
| C6.3 (Health report) | 35,121 / 7t | 112,681 / 13t | 23,117 / 7t | 56,973 |

## Key Observations

1. **Schema Discovery is cheapest**: avg 9.6K tokens — agent runs `\dt` and gets full schema, no overhead
2. **Cross-App Read is efficient**: avg 14K tokens — SQL query per DB, agent reasons about diff
3. **Writes are expensive**: avg 57K-64K tokens — agent must discover schema, understand constraints, then INSERT
4. **High variance in Multi-App**: 23K to 192K tokens — depends on how many turns agent uses to explore 10 DBs
5. **3 failures are all NoneType**: Windows GBK encoding issue with OpenRouter response, not agent logic
6. **20-turn cap hit frequently**: C3.1, C3.2, C5.1, C5.2, C6.1 all hit 20 turns — need investigation

## Static Metrics (bash+DB arm)
- **Config file**: `app_map.json` = 15 lines
- **Agent code**: `simple_agent.py` = 153 lines
- **Dependencies**: 1 (openai)
- **Tool count**: 1 (bash)
- **System prompt tokens**: ~500
- **Tool schema tokens**: ~100
- **Background processes**: 0
- **API tokens needed**: 0
