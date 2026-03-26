"""
Comparison runner: runs the same 18 tasks on both bash+DB and MCP agents,
3 times each, collecting metrics for head-to-head analysis.
"""

import json
import os
import sys
import time
from pathlib import Path

# Add parent dirs to path
sys.path.insert(0, str(Path(__file__).parent.parent / "agent"))
sys.path.insert(0, str(Path(__file__).parent))

# Fix Windows encoding — set once, before any imports that also try
import platform, io
if platform.system() == "Windows":
    if not isinstance(sys.stdout, io.TextIOWrapper) or sys.stdout.encoding != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")


# ── Task definitions: 18 tasks across 6 categories ──
TASKS = [
    # Category 1: Schema Discovery
    {"id": "C1.1", "category": "schema_discovery",
     "task": "List all tables in the Gitea database and count them. Show the table names."},
    {"id": "C1.2", "category": "schema_discovery",
     "task": "Discover the data model of Miniflux: what entities (tables) exist, how many columns each has, and what are the key relationships between them?"},
    {"id": "C1.3", "category": "schema_discovery",
     "task": "For ALL 10 applications, count how many entities/tables each has. Present as a summary table: app name, entity count."},

    # Category 2: Single-App Read
    {"id": "C2.1", "category": "single_read",
     "task": "List all open issues in Gitea's 'backend-api' repository. Show issue number, title, and whether it has any labels."},
    {"id": "C2.2", "category": "single_read",
     "task": "Find all messages in the Mattermost 'backend' channel. Show who posted each message and the message content."},
    {"id": "C2.3", "category": "single_read",
     "task": "Get the full content of the Wiki.js page at path 'architecture/backend'. Show the title and content."},

    # Category 3: Single-App Write
    {"id": "C3.1", "category": "single_write",
     "task": "Create a new public repository called 'experiment-test' in Gitea, owned by user 'alice', with description 'Created by AI agent experiment'."},
    {"id": "C3.2", "category": "single_write",
     "task": "Create a new wiki page in Wiki.js at path 'reports/experiment-log' with title 'Experiment Log' and markdown content: '# Experiment Log\n\nThis page tracks our bash+DB vs MCP comparison experiment.\n\n## Status\n- Started: March 2026\n- Apps: 10\n- Tasks: 18'"},
    {"id": "C3.3", "category": "single_write",
     "task": "Post a message to the Mattermost 'general' channel saying 'Experiment run starting now. Testing 10 apps with AI agent.'"},

    # Category 4: Cross-App Read
    {"id": "C4.1", "category": "cross_read",
     "task": "Find all Gitea issues whose title or body mentions any Mattermost channel name. List matching issues and which channel they reference."},
    {"id": "C4.2", "category": "cross_read",
     "task": "Compare user lists between Gitea and Mattermost. Which usernames exist in both systems? Which exist in only one?"},
    {"id": "C4.3", "category": "cross_read",
     "task": "For each Gitea repository, check if there's a Wiki.js page whose path starts with the repo name. Report which repos have wiki pages and which don't."},

    # Category 5: Cross-App Workflow (read + write)
    {"id": "C5.1", "category": "cross_workflow",
     "task": "Read all open issues from Gitea's 'backend-api' repo. Create a Wiki.js page at 'reports/open-issues' summarizing them with titles and descriptions."},
    {"id": "C5.2", "category": "cross_workflow",
     "task": "Find the Mattermost message about 'connection pool exhaustion'. Create a Gitea issue in 'backend-api' repo with that message as the body and a concise title."},
    {"id": "C5.3", "category": "cross_workflow",
     "task": "Read the Wiki.js page at 'meetings/sprint-review-2026-w10'. Post a brief summary of its content to the Mattermost 'sprint-planning' channel."},

    # Category 6: Multi-App Aggregation
    {"id": "C6.1", "category": "multi_aggregation",
     "task": "Count the total number of users across all available apps. Report per-app user count and the grand total."},
    {"id": "C6.2", "category": "multi_aggregation",
     "task": "Generate an activity summary: for each app, count its primary entities (repos for Gitea, pages for Wiki.js, messages for Mattermost, feeds for Miniflux, etc). Present as a dashboard table."},
    {"id": "C6.3", "category": "multi_aggregation",
     "task": "Create a system health report: for each of the 10 apps, report the number of database tables and whether the app has any active data (at least 1 row in a key table)."},
]


def run_bashdb(task: str) -> dict:
    """Run a task with the bash+DB agent."""
    from simple_agent import run_agent
    return run_agent(task)


def run_mcp(task: str) -> dict:
    """Run a task with the MCP agent."""
    from mcp_agent import run_mcp_agent
    return run_mcp_agent(task)


def _run_single(job: dict) -> dict:
    """Execute a single task run. Used by both serial and parallel modes."""
    tid = job["task_id"]
    cat = job["category"]
    task_text = job["task"]
    arm_name = job["arm"]
    run = job["run"]
    arm_fn = run_bashdb if arm_name == "bashdb" else run_mcp

    start = time.time()
    try:
        transcript = arm_fn(task_text)
        elapsed = time.time() - start
        return {
            "task_id": tid, "category": cat, "arm": arm_name, "run": run,
            "total_tokens": transcript.get("total_tokens", 0),
            "num_turns": transcript.get("num_turns", 0),
            "num_tool_calls": transcript.get("num_tool_calls",
                sum(len(t.get("tool_calls", [])) for t in transcript.get("turns", []))),
            "duration_s": round(elapsed, 1),
            "first_turn_tokens": transcript.get("first_turn_tokens", 0),
            "success": True, "error": None,
        }
    except Exception as e:
        elapsed = time.time() - start
        return {
            "task_id": tid, "category": cat, "arm": arm_name, "run": run,
            "total_tokens": 0, "num_turns": 0, "num_tool_calls": 0,
            "duration_s": round(elapsed, 1), "first_turn_tokens": 0,
            "success": False, "error": str(e),
        }


def run_comparison(
    runs_per_task: int = 3,
    task_filter: str = None,
    category_filter: str = None,
    arm_filter: str = None,
    parallel: int = 1,
):
    """Run the full comparison experiment, optionally in parallel."""
    from concurrent.futures import ThreadPoolExecutor, as_completed

    tasks = TASKS
    if task_filter:
        tasks = [t for t in tasks if task_filter in t["id"]]
    if category_filter:
        tasks = [t for t in tasks if category_filter in t["category"]]

    arm_names = []
    if arm_filter is None or arm_filter == "bashdb":
        arm_names.append("bashdb")
    if arm_filter is None or arm_filter == "mcp":
        arm_names.append("mcp")

    # Build job list
    jobs = []
    for task_def in tasks:
        for arm in arm_names:
            for run in range(1, runs_per_task + 1):
                jobs.append({
                    "task_id": task_def["id"], "category": task_def["category"],
                    "task": task_def["task"], "arm": arm, "run": run,
                })

    total = len(jobs)
    print(f"{'='*70}")
    print(f"  COMPARISON EXPERIMENT")
    print(f"  Tasks: {len(tasks)} | Arms: {arm_names} | Runs/task: {runs_per_task}")
    print(f"  Total runs: {total} | Parallel workers: {parallel}")
    print(f"{'='*70}\n")

    results = []
    # Incremental save path — so we don't lose data if a run hangs
    out_dir = Path(__file__).parent.parent / "results" / "comparison"
    out_dir.mkdir(parents=True, exist_ok=True)
    incremental_file = out_dir / "raw_results_incremental.json"

    def _save_incremental():
        with open(incremental_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False, default=str)

    if parallel <= 1:
        for i, job in enumerate(jobs):
            print(f"  [{i+1}/{total}] {job['arm']} | {job['task_id']} | run {job['run']}", flush=True)
            result = _run_single(job)
            results.append(result)
            _save_incremental()
            print(f"    -> {result['total_tokens']} tok | {result['num_turns']} turns | {result['duration_s']}s"
                  f"{' ERROR: ' + result['error'] if result['error'] else ''}")
    else:
        done = 0
        with ThreadPoolExecutor(max_workers=parallel) as pool:
            future_to_job = {pool.submit(_run_single, job): job for job in jobs}
            for future in as_completed(future_to_job):
                done += 1
                job = future_to_job[future]
                result = future.result()
                results.append(result)
                _save_incremental()
                status = "OK" if result["success"] else f"ERR: {result['error']}"
                print(f"  [{done}/{total}] {job['arm']} | {job['task_id']} r{job['run']} "
                      f"-> {result['total_tokens']} tok | {result['num_turns']} turns | "
                      f"{result['duration_s']}s | {status}", flush=True)

    # ── Summary ──
    print(f"\n\n{'='*70}")
    print(f"  EXPERIMENT COMPLETE — SUMMARY")
    print(f"{'='*70}\n")

    for arm_name in arm_names:
        arm_results = [r for r in results if r["arm"] == arm_name]
        if not arm_results:
            continue
        avg_tok = sum(r["total_tokens"] for r in arm_results) / len(arm_results)
        avg_time = sum(r["duration_s"] for r in arm_results) / len(arm_results)
        success = sum(1 for r in arm_results if r["success"])
        print(f"  [{arm_name.upper():6s}] {len(arm_results)} runs | "
              f"Avg tokens: {avg_tok:.0f} | Avg time: {avg_time:.1f}s | "
              f"Success: {success}/{len(arm_results)}")

    # By category
    if len(arm_names) == 2:
        print(f"\n  {'Category':<22s} {'bash+DB tokens':>15s} {'MCP tokens':>12s} {'Ratio':>8s}")
        print(f"  {'─'*60}")
        categories = sorted(set(t["category"] for t in tasks))
        for cat in categories:
            bashdb_avg = mcp_avg = 0
            for arm_name in arm_names:
                cat_results = [r for r in results if r["category"] == cat and r["arm"] == arm_name]
                avg = sum(r["total_tokens"] for r in cat_results) / max(len(cat_results), 1)
                if arm_name == "bashdb":
                    bashdb_avg = avg
                else:
                    mcp_avg = avg
            ratio = f"{mcp_avg / max(bashdb_avg, 1):.1f}x" if bashdb_avg > 0 else "N/A"
            print(f"  {cat:<22s} {bashdb_avg:>15.0f} {mcp_avg:>12.0f} {ratio:>8s}")

    # Save results
    out_dir = Path(__file__).parent.parent / "results" / "comparison"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "raw_results.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False, default=str)
    print(f"\n  Results saved to: {out_file}")

    return results


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Run MCP vs bash+DB comparison")
    parser.add_argument("--runs", type=int, default=3, help="Runs per task per arm")
    parser.add_argument("--task", default=None, help="Filter by task ID (e.g. C1.1)")
    parser.add_argument("--category", default=None, help="Filter by category")
    parser.add_argument("--arm", default=None, choices=["bashdb", "mcp"], help="Run only one arm")
    parser.add_argument("--parallel", type=int, default=1, help="Number of parallel workers (default: 1)")
    args = parser.parse_args()

    run_comparison(
        runs_per_task=args.runs,
        task_filter=args.task,
        category_filter=args.category,
        arm_filter=args.arm,
        parallel=args.parallel,
    )
