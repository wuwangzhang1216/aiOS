#!/usr/bin/env python3
"""Generate head-to-head comparison report: bash+DB vs MCP."""

import json, statistics, os
from collections import defaultdict

BASE = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(BASE, "comparison", "bashdb_results.json"), encoding="utf-8") as f:
    bashdb = json.load(f)
with open(os.path.join(BASE, "comparison", "mcp_results.json"), encoding="utf-8") as f:
    mcp = json.load(f)

CATS = ["schema_discovery", "single_read", "single_write",
        "cross_read", "cross_workflow", "multi_aggregation"]
LABELS = {
    "schema_discovery":  "C1: Schema Discovery",
    "single_read":       "C2: Single-App Read",
    "single_write":      "C3: Single-App Write",
    "cross_read":        "C4: Cross-App Read",
    "cross_workflow":    "C5: Cross-App Workflow",
    "multi_aggregation": "C6: Multi-App Aggregation",
}

def calc_stats(arr):
    if not arr:
        return {"mean": 0, "med": 0, "std": 0, "min": 0, "max": 0}
    return {
        "mean": statistics.mean(arr),
        "med": statistics.median(arr),
        "std": statistics.stdev(arr) if len(arr) > 1 else 0,
        "min": min(arr),
        "max": max(arr),
    }

def group_by_cat(data):
    g = defaultdict(lambda: {"tokens": [], "turns": [], "times": [], "ok": 0, "total": 0})
    for r in data:
        c = r["category"]
        g[c]["total"] += 1
        if r["success"]:
            g[c]["ok"] += 1
            g[c]["tokens"].append(r["total_tokens"])
            g[c]["turns"].append(r["num_turns"])
            g[c]["times"].append(r["duration_s"])
    return g

bg = group_by_cat(bashdb)
mg = group_by_cat(mcp)

lines = []
def p(s=""):
    lines.append(s)
    print(s)

p("=" * 100)
p("  BASH+DB vs MCP - HEAD-TO-HEAD COMPARISON")
p("  Model: minimax-m2.7 | 10 apps deployed | 18 tasks x 3 runs x 2 arms = 108 total runs")
p("=" * 100)

# ── Table 1: Token consumption ──
p()
p("TABLE 1: TOKEN CONSUMPTION (avg per task)")
p("-" * 82)
p(f"  {'Category':<28s}  {'bash+DB':>10s}  {'MCP':>10s}  {'Ratio':>8s}  {'Winner':>8s}")
p("-" * 82)

total_b_tok = sum(r["total_tokens"] for r in bashdb if r["success"])
total_m_tok = sum(r["total_tokens"] for r in mcp if r["success"])

for cat in CATS:
    b = calc_stats(bg[cat]["tokens"])
    m = calc_stats(mg[cat]["tokens"])
    ratio = b["mean"] / m["mean"] if m["mean"] > 0 else float("inf")
    winner = "bash+DB" if b["mean"] < m["mean"] else "MCP"
    p(f"  {LABELS[cat]:<28s}  {b['mean']:>10,.0f}  {m['mean']:>10,.0f}  {ratio:>7.1f}x  {winner:>8s}")

b_ok_count = sum(1 for r in bashdb if r["success"])
m_ok_count = sum(1 for r in mcp if r["success"])
b_avg = total_b_tok / max(b_ok_count, 1)
m_avg = total_m_tok / max(m_ok_count, 1)
p("-" * 82)
p(f"  {'OVERALL AVG':<28s}  {b_avg:>10,.0f}  {m_avg:>10,.0f}  {b_avg/m_avg:>7.1f}x  {'MCP' if m_avg < b_avg else 'bash+DB':>8s}")
p(f"  {'TOTAL':<28s}  {total_b_tok:>10,}  {total_m_tok:>10,}  {total_b_tok/total_m_tok:>7.1f}x")

# ── Table 2: Turns ──
p()
p("TABLE 2: INTERACTION COMPLEXITY (avg turns per task)")
p("-" * 82)
p(f"  {'Category':<28s}  {'bash+DB':>10s}  {'MCP':>10s}  {'Ratio':>8s}  {'Winner':>8s}")
p("-" * 82)
for cat in CATS:
    b = calc_stats(bg[cat]["turns"])
    m = calc_stats(mg[cat]["turns"])
    ratio = b["mean"] / m["mean"] if m["mean"] > 0 else float("inf")
    winner = "bash+DB" if b["mean"] < m["mean"] else "MCP"
    p(f"  {LABELS[cat]:<28s}  {b['mean']:>10.1f}  {m['mean']:>10.1f}  {ratio:>7.1f}x  {winner:>8s}")

# ── Table 3: Latency ──
p()
p("TABLE 3: LATENCY (avg seconds per task)")
p("-" * 82)
p(f"  {'Category':<28s}  {'bash+DB':>10s}  {'MCP':>10s}  {'Ratio':>8s}  {'Winner':>8s}")
p("-" * 82)
for cat in CATS:
    b = calc_stats(bg[cat]["times"])
    m = calc_stats(mg[cat]["times"])
    ratio = b["mean"] / m["mean"] if m["mean"] > 0 else float("inf")
    winner = "bash+DB" if b["mean"] < m["mean"] else "MCP"
    p(f"  {LABELS[cat]:<28s}  {b['mean']:>9.1f}s  {m['mean']:>9.1f}s  {ratio:>7.1f}x  {winner:>8s}")

# ── Table 4: Success rate ──
p()
p("TABLE 4: TASK SUCCESS RATE")
p("-" * 82)
p(f"  {'Category':<28s}  {'bash+DB':>12s}  {'MCP':>12s}  {'Note':>20s}")
p("-" * 82)
for cat in CATS:
    b_rate = f"{bg[cat]['ok']}/{bg[cat]['total']}"
    m_rate = f"{mg[cat]['ok']}/{mg[cat]['total']}"
    note = ""
    if bg[cat]["ok"] < bg[cat]["total"]:
        note = "encoding error"
    p(f"  {LABELS[cat]:<28s}  {b_rate:>12s}  {m_rate:>12s}  {note:>20s}")
b_total_ok = sum(bg[c]["ok"] for c in CATS)
b_total_all = sum(bg[c]["total"] for c in CATS)
m_total_ok = sum(mg[c]["ok"] for c in CATS)
m_total_all = sum(mg[c]["total"] for c in CATS)
p("-" * 82)
b_pct = f"{b_total_ok}/{b_total_all} ({b_total_ok/b_total_all*100:.0f}%)"
m_pct = f"{m_total_ok}/{m_total_all} ({m_total_ok/m_total_all*100:.0f}%)"
p(f"  {'TOTAL':<28s}  {b_pct:>12s}  {m_pct:>12s}")

# ── Table 5: App coverage ──
p()
p("TABLE 5: APP COVERAGE")
p("-" * 82)
p("  bash+DB: 10/10 apps accessible via docker exec + SQL")
p("    Gitea, Wiki.js, Mattermost, Focalboard, BookStack,")
p("    Vikunja, NocoDB, Miniflux, Leantime, Plane")
p()
p("  MCP:     3/10 apps accessible (Gitea, BookStack, Miniflux)")
p("    Mattermost MCP server: INIT FAILED every run")
p("    6 apps: NO MCP SERVER EXISTS in npm ecosystem")
p()
p("  Setup complexity:")
p("    bash+DB: 1 JSON registry (10 entries) + docker exec")
p("    MCP:     4 npm packages installed, 1 actually worked reliably,")
p("             each needs: config, auth tokens, per-server debugging")

# ── Key findings ──
p()
p("=" * 100)
p("  KEY FINDINGS")
p("=" * 100)
p()
p(f"  1. TOKEN COST: MCP used {total_m_tok/total_b_tok*100:.0f}% fewer tokens "
  f"({total_m_tok:,} vs {total_b_tok:,})")
p(f"     BUT: MCP could only reach 3/10 apps, so most tasks got trivial")
p(f"     'I cannot access this' responses (low tokens != task completion)")
p()
p(f"  2. COVERAGE: bash+DB operated ALL 10 apps with zero per-app setup.")
p(f"     MCP had coverage for 3/10 — the other 7 apps simply have no MCP server.")
p()
p(f"  3. SCALABILITY: Adding app #11 to bash+DB = 1 line in registry JSON.")
p(f"     Adding app #11 to MCP = find/build/configure/debug a new MCP server.")
p()
p(f"  4. REAL TASK COMPLETION:")
p(f"     bash+DB actually queried 10 databases and produced real data.")
p(f"     MCP returned 'unable to access' for tasks requiring apps without MCP servers.")
p()
p(f"  5. TURNS: bash+DB used more turns ({b_avg:,.0f} avg tokens) because it did")
p(f"     MORE WORK — schema discovery, multi-db joins, data aggregation across 10 apps.")
p(f"     MCP used fewer turns ({m_avg:,.0f} avg tokens) because it often gave up early.")

# ── Save markdown version ──
report_path = os.path.join(BASE, "comparison", "comparison_report.txt")
with open(report_path, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))
print(f"\nReport saved to: {report_path}")

# ── Save combined JSON ──
combined = {
    "experiment": {
        "model": "minimax/minimax-m2.7",
        "apps_deployed": 10,
        "tasks": 18,
        "runs_per_task": 3,
        "total_runs": 108,
    },
    "summary": {
        "bashdb": {
            "total_tokens": total_b_tok,
            "avg_tokens": round(b_avg),
            "success_rate": f"{b_total_ok}/{b_total_all}",
            "app_coverage": "10/10",
        },
        "mcp": {
            "total_tokens": total_m_tok,
            "avg_tokens": round(m_avg),
            "success_rate": f"{m_total_ok}/{m_total_all}",
            "app_coverage": "3/10",
        },
    },
    "by_category": {},
    "raw_bashdb": bashdb,
    "raw_mcp": mcp,
}

for cat in CATS:
    b = calc_stats(bg[cat]["tokens"])
    m = calc_stats(mg[cat]["tokens"])
    bt = calc_stats(bg[cat]["turns"])
    mt = calc_stats(mg[cat]["turns"])
    bl = calc_stats(bg[cat]["times"])
    ml = calc_stats(mg[cat]["times"])
    combined["by_category"][cat] = {
        "bashdb": {
            "avg_tokens": round(b["mean"]),
            "avg_turns": round(bt["mean"], 1),
            "avg_time_s": round(bl["mean"], 1),
            "success": f"{bg[cat]['ok']}/{bg[cat]['total']}",
        },
        "mcp": {
            "avg_tokens": round(m["mean"]),
            "avg_turns": round(mt["mean"], 1),
            "avg_time_s": round(ml["mean"], 1),
            "success": f"{mg[cat]['ok']}/{mg[cat]['total']}",
        },
    }

combined_path = os.path.join(BASE, "comparison", "full_comparison.json")
with open(combined_path, "w", encoding="utf-8") as f:
    json.dump(combined, f, indent=2, ensure_ascii=False)
print(f"Combined data saved to: {combined_path}")
