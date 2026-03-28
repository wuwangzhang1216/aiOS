"""
Batch runner: executes all scenario variants sequentially.
Supports multiple models, multiple runs, both arms (sql/mcp), reseed between variants.
"""

import json
import subprocess
import time
from datetime import datetime
from pathlib import Path

import yaml

from agent import Agent, AgentConfig
from verify_scenario import verify_inline_postcondition, verify_postconditions

MODELS = [
    "minimax/minimax-m2.7",
    "xiaomi/mimo-v2-pro",
    "google/gemini-3-flash-preview",
    "openai/gpt-5.4-mini",
]

PROJECT_ROOT = Path(__file__).parent.parent


def load_all_scenarios(scenarios_root: Path) -> list[dict]:
    scenarios = []
    for sf in sorted(scenarios_root.rglob("scenario.yaml")):
        with open(sf, encoding="utf-8") as f:
            data = yaml.safe_load(f)
            data["_dir"] = sf.parent
        scenarios.append(data)
    return scenarios


def verify_variant(variant: dict, scenario_dir: Path, arm: str) -> dict:
    if "postcondition" in variant:
        sql = variant["postcondition"]
        if not sql:
            return {"score": 1.0, "functional_class": "skip",
                    "passed": 0, "total": 0, "details": {}}
        target_db = variant.get("target_db")
        return verify_inline_postcondition(sql, target_db)
    if "postconditions_file" in variant:
        pc_file = scenario_dir / variant["postconditions_file"]
        if pc_file.exists():
            return verify_postconditions(pc_file, arm)
    return {"score": 0, "functional_class": "?", "details": {}}


def model_short(model: str) -> str:
    return model.split("/")[-1]


def reseed(arm: str = "both"):
    """Clean and reseed all databases. ~5s."""
    script = PROJECT_ROOT / "scripts" / "reseed.sh"
    result = subprocess.run(
        ["bash", str(script), "--arm", arm],
        capture_output=True, text=True, timeout=60,
    )
    if result.returncode != 0:
        print(f"    [reseed warning] {result.stderr[:200]}")


def llm_call_with_retry(client, max_retries=2, **kwargs):
    """Call LLM with retry on transient errors."""
    for attempt in range(max_retries + 1):
        try:
            return client.chat.completions.create(**kwargs)
        except Exception as e:
            if attempt < max_retries and ("timeout" in str(e).lower() or "502" in str(e) or "503" in str(e) or "rate" in str(e).lower()):
                wait = 10 * (attempt + 1)
                print(f"\n    [retry {attempt+1}/{max_retries}] {str(e)[:80]}... waiting {wait}s")
                time.sleep(wait)
            else:
                raise


def run_batch(
    scenarios_root: Path,
    registry_path: Path,
    output_dir: Path,
    arm: str = "sql",
    tier_filter: int = None,
    scenario_filter: str = None,
    models: list[str] = None,
    runs: int = 1,
    do_reseed: bool = True,
):
    if models is None:
        models = MODELS

    scenarios = load_all_scenarios(scenarios_root)
    if tier_filter is not None:
        scenarios = [s for s in scenarios if s.get("tier") == tier_filter]
    if scenario_filter:
        scenarios = [s for s in scenarios if scenario_filter in s["scenario_id"]]

    arms = ["sql", "mcp"] if arm == "both" else [arm]

    if "mcp" in arms:
        from mcp_agent import MCPAgent

    variants = []
    for s in scenarios:
        for v in s["variants"]:
            variants.append((s, v))

    total_jobs = len(variants) * len(models) * runs * len(arms)

    # Resume: load existing results to skip completed jobs
    out_file = output_dir / f"batch_{arm}_multi.json"
    all_results = []
    completed_keys = set()
    if out_file.exists():
        try:
            with open(out_file) as f:
                data = json.load(f)
            all_results = data.get("results", []) if isinstance(data, dict) else data
            for r in all_results:
                completed_keys.add((r.get("model",""), r.get("arm",""), r.get("variant",""), r.get("run",0)))
            print(f"  Resuming: {len(completed_keys)} jobs already done")
        except Exception:
            pass
    done = len(completed_keys)

    print(f"{'='*70}")
    print(f"  Experiment: {len(variants)} variants x {len(models)} models x {runs} runs x {len(arms)} arms = {total_jobs} jobs")
    print(f"  Arms: {arms} | Models: {[model_short(m) for m in models]}")
    print(f"  Reseed: {'ON' if do_reseed else 'OFF'} | Remaining: {total_jobs - done}")
    print(f"{'='*70}\n")

    for model in models:
        model_tag = model_short(model)
        print(f"\n{'─'*70}")
        print(f"  MODEL: {model}")
        print(f"{'─'*70}")

        for run_num in range(1, runs + 1):
            for scenario, variant in variants:
                for current_arm in arms:
                    vid = variant["id"]
                    scenario_dir = scenario["_dir"]

                    # Skip if already completed (resume mode)
                    job_key = (model, current_arm, vid, run_num)
                    if job_key in completed_keys:
                        done += 1
                        continue

                    done += 1
                    label = f"[{done}/{total_jobs}] {model_tag} r{run_num} {current_arm} {vid}"
                    print(f"  {label}...", end=" ", flush=True)

                    # Reseed before each variant
                    if do_reseed:
                        reseed(arm=current_arm)

                    config = AgentConfig(
                        arm=current_arm,
                        registry_path=str(registry_path),
                        model=model,
                    )

                    if current_arm == "mcp":
                        agent = MCPAgent(config)
                    else:
                        agent = Agent(config)

                    start = time.time()
                    try:
                        transcript = agent.run(variant["task"], vid, run_number=run_num)
                        elapsed = time.time() - start

                        pc = verify_variant(variant, scenario_dir, current_arm)

                        result = {
                            "variant": vid,
                            "tier": scenario.get("tier"),
                            "category": scenario.get("category"),
                            "arm": current_arm,
                            "model": model,
                            "run": run_num,
                            "score": pc["score"],
                            "class": pc["functional_class"],
                            "turns": len(transcript.turns),
                            "tokens": transcript.measurements.get("total_tokens", {}),
                            "sql_ops": transcript.measurements.get("sql_ops", {}),
                            "mcp_ops": transcript.measurements.get("mcp_ops", {}),
                            "elapsed_s": round(elapsed, 1),
                            "pc_details": pc.get("details", {}),
                        }
                        all_results.append(result)

                        status = "PASS" if pc["score"] >= 0.75 else "PART" if pc["score"] > 0 else "FAIL"
                        if pc["functional_class"] == "skip":
                            status = "SKIP"
                        tok = result["tokens"].get("total", "?")
                        print(f"{status} ({elapsed:.1f}s, {tok} tok)")

                        # Save transcript
                        t_dir = output_dir / "transcripts" / current_arm / model_tag / vid
                        t_dir.mkdir(parents=True, exist_ok=True)
                        with open(t_dir / f"run_{run_num}.json", "w") as f:
                            json.dump(transcript.to_dict(), f, indent=2, default=str)

                    except Exception as e:
                        elapsed = time.time() - start
                        print(f"ERROR ({elapsed:.1f}s): {e}")
                        all_results.append({
                            "variant": vid, "tier": scenario.get("tier"),
                            "category": scenario.get("category"),
                            "arm": current_arm, "model": model, "run": run_num,
                            "score": 0, "class": "F", "error": str(e),
                            "elapsed_s": round(elapsed, 1),
                        })

                    # Incremental save
                    _save_results(output_dir, arm, all_results, models, runs, arms, len(variants))

    _print_summary(all_results, models, arms)
    return all_results


def _save_results(output_dir: Path, arm: str, results: list[dict],
                  models=None, runs=None, arms=None, n_variants=None):
    output_dir.mkdir(parents=True, exist_ok=True)
    out_file = output_dir / f"batch_{arm}_multi.json"
    output = {
        "metadata": {
            "experiment": "aios-sql-vs-mcp",
            "date": datetime.now().isoformat(),
            "models": models or [],
            "runs": runs,
            "arms": arms or [],
            "variants": n_variants or 0,
        },
        "results": results,
    }
    with open(out_file, "w") as f:
        json.dump(output, f, indent=2, default=str)


def _print_summary(results: list[dict], models: list[str], arms: list[str]):
    print(f"\n\n{'='*70}")
    print(f"  RESULTS SUMMARY")
    print(f"{'='*70}\n")

    header = f"  {'Model':<22s} {'Arm':<5s} {'Pass':>6s} {'Rate':>7s} {'Avg tok':>10s} {'Avg time':>10s}"
    print(header)
    print(f"  {'─'*62}")

    for model in models:
        for arm in arms:
            mr = [r for r in results if r["model"] == model and r["arm"] == arm]
            if not mr:
                continue
            scored = [r for r in mr if r.get("class") != "skip"]
            passed = sum(1 for r in scored if r["score"] >= 0.75)
            total = len(scored)
            rate = f"({100*passed/max(total,1):.0f}%)"
            avg_tok = sum(r.get("tokens", {}).get("total", 0) for r in mr) / max(len(mr), 1)
            avg_t = sum(r.get("elapsed_s", 0) for r in mr) / max(len(mr), 1)
            tag = model_short(model)
            print(f"  {tag:<22s} {arm:<5s} {passed}/{total:>3} {rate:>7s} {avg_tok:>10,.0f} {avg_t:>9.1f}s")

    # Per-tier
    tiers = sorted(set(r.get("tier") for r in results if r.get("tier") is not None))
    if tiers:
        print(f"\n  Per-tier pass rates:")
        tier_hdr = f"  {'Model':<22s} {'Arm':<5s}" + "".join(f" {'T'+str(t):>6s}" for t in tiers)
        print(tier_hdr)
        print(f"  {'─'*55}")
        for model in models:
            for arm in arms:
                tag = model_short(model)
                cells = []
                for t in tiers:
                    tr = [r for r in results if r["model"] == model and r["arm"] == arm
                          and r.get("tier") == t and r.get("class") != "skip"]
                    p = sum(1 for r in tr if r["score"] >= 0.75)
                    cells.append(f"{p}/{len(tr)}")
                print(f"  {tag:<22s} {arm:<5s}" + "".join(f" {c:>6s}" for c in cells))

    print()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--arm", default="both", choices=["sql", "mcp", "both"])
    parser.add_argument("--tier", type=int, default=None)
    parser.add_argument("--scenario", default=None)
    parser.add_argument("--models", nargs="+", default=None)
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--no-reseed", action="store_true")
    parser.add_argument("--scenarios-dir", default="../scenarios")
    parser.add_argument("--registry", default="../db_registry.json")
    parser.add_argument("--output", default="../results")
    args = parser.parse_args()

    run_batch(
        scenarios_root=Path(args.scenarios_dir),
        registry_path=Path(args.registry),
        output_dir=Path(args.output),
        arm=args.arm,
        tier_filter=args.tier,
        scenario_filter=args.scenario,
        models=args.models,
        runs=args.runs,
        do_reseed=not args.no_reseed,
    )
