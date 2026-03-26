"""
Automated scenario executor for the Bash+DB experiment.

Runs scenarios across experimental arms with multiple repetitions,
handling database resets between runs for reproducibility.
"""

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import yaml

from agent import Agent, AgentConfig, AgentTranscript
from verify_scenario import verify_postconditions


def load_scenario(scenario_dir: Path) -> dict:
    """Load a scenario definition from YAML."""
    scenario_file = scenario_dir / "scenario.yaml"
    if not scenario_file.exists():
        raise FileNotFoundError(f"No scenario.yaml found in {scenario_dir}")
    with open(scenario_file) as f:
        return yaml.safe_load(f)


def find_all_scenarios(scenarios_root: Path) -> list[dict]:
    """Discover all scenario definitions recursively."""
    scenarios = []
    for scenario_file in sorted(scenarios_root.rglob("scenario.yaml")):
        with open(scenario_file) as f:
            data = yaml.safe_load(f)
            data["_dir"] = scenario_file.parent
            scenarios.append(data)
    return scenarios


def reset_databases(project_dir: Path):
    """Reset all databases to clean state."""
    reset_script = project_dir / "scripts" / "reset-all.sh"
    print("  Resetting databases...", flush=True)
    result = subprocess.run(
        ["bash", str(reset_script)],
        capture_output=True,
        text=True,
        timeout=300,
        cwd=str(project_dir),
    )
    if result.returncode != 0:
        print(f"  WARNING: Database reset had issues: {result.stderr[:500]}")
    else:
        print("  Databases reset successfully.")


def run_variant(
    agent: Agent,
    variant: dict,
    scenario_dir: Path,
    arm: str,
    run_number: int,
    output_dir: Path,
) -> dict:
    """Run a single variant and return results."""
    variant_id = variant["id"]
    task = variant["task"]

    print(f"    [{variant_id}] Run {run_number}...", end=" ", flush=True)

    # Run the agent
    start = time.time()
    transcript = agent.run(task, variant_id, run_number)
    elapsed = time.time() - start

    # Verify postconditions
    postcond_file = scenario_dir / variant["postconditions_file"]
    if postcond_file.exists():
        pc_results = verify_postconditions(postcond_file, arm)
    else:
        pc_results = {"score": 0.0, "details": "Postconditions file not found"}

    # Build result
    result = {
        "scenario_id": variant_id,
        "arm": arm,
        "run": run_number,
        "completion_score": pc_results.get("score", 0.0),
        "functional_class": pc_results.get("functional_class", "unknown"),
        "postconditions": pc_results.get("details", {}),
        **transcript.measurements,
        "total_duration_ms": elapsed * 1000,
        "turns": len(transcript.turns),
        "transcript_path": None,  # Will be set after saving
    }

    # Save transcript
    transcript_dir = output_dir / "transcripts" / arm / variant_id
    transcript_dir.mkdir(parents=True, exist_ok=True)
    transcript_path = transcript_dir / f"run_{run_number}.jsonl"
    with open(transcript_path, "w") as f:
        json.dump(transcript.to_dict(), f, indent=2, default=str)
    result["transcript_path"] = str(transcript_path)

    # Save result
    result_dir = output_dir / arm / variant_id
    result_dir.mkdir(parents=True, exist_ok=True)
    with open(result_dir / f"run_{run_number}.json", "w") as f:
        json.dump(result, f, indent=2, default=str)

    score = result["completion_score"]
    status = "PASS" if score >= 0.75 else "PARTIAL" if score > 0 else "FAIL"
    print(f"{status} (score={score:.2f}, {elapsed:.1f}s, {result.get('total_tokens', {}).get('total', '?')} tokens)")

    return result


def run_experiment(
    scenarios_root: Path,
    output_dir: Path,
    project_dir: Path,
    arms: list[str] = None,
    runs_per_variant: int = 5,
    scenario_filter: str = None,
    variant_filter: str = None,
    skip_reset: bool = False,
):
    """Run the full experiment."""
    if arms is None:
        arms = ["sql"]

    scenarios = find_all_scenarios(scenarios_root)
    print(f"Found {len(scenarios)} scenarios")

    # Filter scenarios if specified
    if scenario_filter:
        scenarios = [s for s in scenarios if scenario_filter in s["scenario_id"]]
        print(f"Filtered to {len(scenarios)} scenarios matching '{scenario_filter}'")

    all_results = []

    for arm in arms:
        print(f"\n{'='*60}")
        print(f"  Experimental Arm: {arm.upper()}")
        print(f"{'='*60}")

        config = AgentConfig(
            arm=arm,
            registry_path=str(project_dir / "db_registry.json"),
        )

        for scenario in scenarios:
            scenario_dir = scenario["_dir"]
            print(f"\n  Scenario: {scenario['scenario_id']} - {scenario['description']}")

            for variant in scenario["variants"]:
                if variant_filter and variant_filter not in variant["id"]:
                    continue

                for run_num in range(1, runs_per_variant + 1):
                    # Reset databases before each run for clean state
                    if not skip_reset:
                        reset_databases(project_dir)
                        time.sleep(2)  # Brief pause for DBs to stabilize

                    agent = Agent(config)
                    result = run_variant(
                        agent=agent,
                        variant=variant,
                        scenario_dir=scenario_dir,
                        arm=arm,
                        run_number=run_num,
                        output_dir=output_dir,
                    )
                    all_results.append(result)

    # Save aggregate results
    aggregate_path = output_dir / "aggregate_results.json"
    with open(aggregate_path, "w") as f:
        json.dump(all_results, f, indent=2, default=str)

    # Print summary
    print(f"\n{'='*60}")
    print(f"  EXPERIMENT COMPLETE")
    print(f"{'='*60}")
    print(f"  Total runs: {len(all_results)}")

    for arm in arms:
        arm_results = [r for r in all_results if r["arm"] == arm]
        if arm_results:
            avg_score = sum(r["completion_score"] for r in arm_results) / len(arm_results)
            pass_count = sum(1 for r in arm_results if r["completion_score"] >= 0.75)
            print(f"  [{arm.upper()}] Avg score: {avg_score:.2f}, "
                  f"Pass rate: {pass_count}/{len(arm_results)} "
                  f"({pass_count/len(arm_results)*100:.0f}%)")

    print(f"\n  Results saved to: {aggregate_path}")


def main():
    parser = argparse.ArgumentParser(description="Run Bash+DB experiment scenarios")
    parser.add_argument(
        "--scenarios", default="scenarios",
        help="Path to scenarios directory"
    )
    parser.add_argument(
        "--output", default="results",
        help="Path to output directory"
    )
    parser.add_argument(
        "--project", default=".",
        help="Project root directory"
    )
    parser.add_argument(
        "--arm", nargs="+", default=["sql"],
        choices=["sql", "api", "mcp"],
        help="Experimental arms to run"
    )
    parser.add_argument(
        "--runs", type=int, default=5,
        help="Number of runs per variant"
    )
    parser.add_argument(
        "--scenario", default=None,
        help="Filter by scenario ID (e.g., 'T1.1')"
    )
    parser.add_argument(
        "--variant", default=None,
        help="Filter by variant ID (e.g., 'T1.1a')"
    )
    parser.add_argument(
        "--skip-reset", action="store_true",
        help="Skip database reset between runs (for debugging)"
    )

    args = parser.parse_args()

    project_dir = Path(args.project).resolve()
    scenarios_root = project_dir / args.scenarios
    output_dir = project_dir / args.output

    output_dir.mkdir(parents=True, exist_ok=True)

    run_experiment(
        scenarios_root=scenarios_root,
        output_dir=output_dir,
        project_dir=project_dir,
        arms=args.arm,
        runs_per_variant=args.runs,
        scenario_filter=args.scenario,
        variant_filter=args.variant,
        skip_reset=args.skip_reset,
    )


if __name__ == "__main__":
    main()
