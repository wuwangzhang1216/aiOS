"""
Batch runner: executes all scenario variants sequentially.
Supports both inline postconditions and file-based postconditions.
"""

import json
import time
from pathlib import Path

import yaml

from agent import Agent, AgentConfig
from verify_scenario import verify_inline_postcondition, verify_postconditions


def load_all_scenarios(scenarios_root: Path) -> list[dict]:
    """Load all scenarios with their variants."""
    scenarios = []
    for sf in sorted(scenarios_root.rglob("scenario.yaml")):
        with open(sf, encoding="utf-8") as f:
            data = yaml.safe_load(f)
            data["_dir"] = sf.parent
        scenarios.append(data)
    return scenarios


def verify_variant(variant: dict, scenario_dir: Path, arm: str) -> dict:
    """Verify postconditions for a variant (inline or file-based)."""
    # Inline postcondition (new format)
    if "postcondition" in variant:
        sql = variant["postcondition"]
        if not sql:
            return {"score": 1.0, "functional_class": "skip",
                    "passed": 0, "total": 0, "details": {}}
        target_db = variant.get("target_db")
        return verify_inline_postcondition(sql, target_db)

    # File-based postcondition (legacy format)
    if "postconditions_file" in variant:
        pc_file = scenario_dir / variant["postconditions_file"]
        if pc_file.exists():
            return verify_postconditions(pc_file, arm)

    return {"score": 0, "functional_class": "?", "details": {}}


def run_batch(
    scenarios_root: Path,
    registry_path: Path,
    output_dir: Path,
    arm: str = "sql",
    tier_filter: int = None,
    scenario_filter: str = None,
):
    """Run one pass of all scenarios (1 run per variant)."""
    scenarios = load_all_scenarios(scenarios_root)
    if tier_filter is not None:
        scenarios = [s for s in scenarios if s.get("tier") == tier_filter]
    if scenario_filter:
        scenarios = [s for s in scenarios if scenario_filter in s["scenario_id"]]

    config = AgentConfig(arm=arm, registry_path=str(registry_path))
    results = []
    total = sum(len(s["variants"]) for s in scenarios)
    done = 0

    print(f"{'='*60}")
    print(f"  Batch Run: {total} variants, arm={arm}")
    print(f"{'='*60}\n")

    for scenario in scenarios:
        sid = scenario["scenario_id"]
        desc = scenario.get("description", "")[:60] if isinstance(scenario.get("description"), str) else sid
        print(f"── {sid}: {desc}")
        scenario_dir = scenario["_dir"]

        for variant in scenario["variants"]:
            done += 1
            vid = variant["id"]
            print(f"  [{done}/{total}] {vid}...", end=" ", flush=True)

            agent = Agent(config)
            start = time.time()

            try:
                transcript = agent.run(variant["task"], vid, run_number=1)
                elapsed = time.time() - start

                pc = verify_variant(variant, scenario_dir, arm)

                result = {
                    "variant": vid,
                    "tier": scenario.get("tier"),
                    "category": scenario.get("category"),
                    "arm": arm,
                    "score": pc["score"],
                    "class": pc["functional_class"],
                    "turns": len(transcript.turns),
                    "tokens": transcript.measurements.get("total_tokens", {}),
                    "sql_ops": transcript.measurements.get("sql_ops", {}),
                    "elapsed_s": round(elapsed, 1),
                    "pc_details": pc.get("details", {}),
                }
                results.append(result)

                status = "PASS" if pc["score"] >= 0.75 else "PARTIAL" if pc["score"] > 0 else "FAIL"
                if pc["functional_class"] == "skip":
                    status = "SKIP"
                tok = result["tokens"].get("total", "?")
                print(f"{status} (score={pc['score']:.2f}, {elapsed:.1f}s, {tok} tok)")

                # Save transcript
                t_dir = output_dir / "transcripts" / arm / vid
                t_dir.mkdir(parents=True, exist_ok=True)
                with open(t_dir / "run_1.json", "w") as f:
                    json.dump(transcript.to_dict(), f, indent=2, default=str)

            except Exception as e:
                elapsed = time.time() - start
                print(f"ERROR ({elapsed:.1f}s): {e}")
                results.append({
                    "variant": vid, "tier": scenario.get("tier"),
                    "category": scenario.get("category"),
                    "arm": arm, "score": 0,
                    "class": "F", "error": str(e), "elapsed_s": round(elapsed, 1),
                })

    # Summary
    print(f"\n{'='*60}")
    print(f"  RESULTS SUMMARY")
    print(f"{'='*60}")
    passed = sum(1 for r in results if r["score"] >= 0.75)
    partial = sum(1 for r in results if 0 < r["score"] < 0.75)
    failed = sum(1 for r in results if r["score"] == 0 and r.get("class") != "skip")
    skipped = sum(1 for r in results if r.get("class") == "skip")
    scored = [r for r in results if r.get("class") != "skip"]
    avg_score = sum(r["score"] for r in scored) / max(len(scored), 1)
    avg_tokens = sum(r.get("tokens", {}).get("total", 0) for r in results) / max(len(results), 1)

    print(f"  Total: {len(results)} | Pass: {passed} | Partial: {partial} | Fail: {failed} | Skip: {skipped}")
    print(f"  Avg score: {avg_score:.2f} | Avg tokens: {avg_tokens:.0f}")

    # Per-tier breakdown
    tiers = sorted(set(r.get("tier") for r in results if r.get("tier") is not None))
    for tier in tiers:
        tier_results = [r for r in results if r.get("tier") == tier]
        tier_pass = sum(1 for r in tier_results if r["score"] >= 0.75)
        print(f"  Tier {tier}: {tier_pass}/{len(tier_results)} passed")

    print()
    for r in results:
        s = "PASS" if r["score"] >= 0.75 else "PART" if r["score"] > 0 else "FAIL"
        if r.get("class") == "skip":
            s = "SKIP"
        cat = r.get("category", "")[:15]
        print(f"  [{s:4s}] {r['variant']:8s} T{r.get('tier','?')} {cat:15s} {r.get('elapsed_s',0):5.1f}s  {r.get('tokens',{}).get('total','?'):>6} tok")

    # Save aggregate
    output_dir.mkdir(parents=True, exist_ok=True)
    with open(output_dir / f"batch_{arm}.json", "w") as f:
        json.dump(results, f, indent=2, default=str)

    print(f"\n  Saved to {output_dir / f'batch_{arm}.json'}")
    return results


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--arm", default="sql", choices=["sql", "api", "mcp"])
    parser.add_argument("--tier", type=int, default=None, help="Filter by tier (0, 1, 2, or 3)")
    parser.add_argument("--scenario", default=None, help="Filter by scenario ID")
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
    )
