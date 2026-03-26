"""
Postcondition verifier for experiment scenarios.

Executes pre-registered SQL postcondition queries against the databases
and computes completion scores.
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path


# DB connection info per app — uses docker exec
DB_CONNECTIONS = {
    "gitea": {
        "container": "pg-gitea",
        "database": "gitea",
        "user": "agent_ro",
    },
    "wikijs": {
        "container": "pg-wiki",
        "database": "wikijs",
        "user": "agent_ro",
    },
    "mattermost": {
        "container": "pg-mattermost",
        "database": "mattermost",
        "user": "agent_ro",
    },
}


def parse_postconditions(sql_file: Path) -> list[dict]:
    """
    Parse a postconditions SQL file into individual checks.

    Each postcondition is a SELECT that returns a boolean column.
    Comments starting with '-- PC' identify each postcondition.
    """
    content = sql_file.read_text()
    postconditions = []

    # Split by postcondition comments
    blocks = re.split(r'(--\s*PC\d+:.*)', content)

    current_name = None
    current_sql = ""

    for block in blocks:
        block = block.strip()
        if not block:
            continue

        if re.match(r'--\s*PC\d+:', block):
            # Save previous postcondition
            if current_name and current_sql.strip():
                postconditions.append({
                    "name": current_name,
                    "sql": current_sql.strip(),
                })
            current_name = block.lstrip("- ").strip()
            current_sql = ""
        else:
            current_sql += block + "\n"

    # Save last postcondition
    if current_name and current_sql.strip():
        postconditions.append({
            "name": current_name,
            "sql": current_sql.strip(),
        })

    return postconditions


def determine_target_db(sql: str, postcond_file: Path) -> str:
    """Determine which database a postcondition should run against."""
    sql_lower = sql.lower()

    # Check table names to infer the target database
    # Check table names to infer target DB (order matters — more specific first)
    if any(t in sql_lower for t in ["repository", "issue", '"user"', "label", "issue_label", "milestone", "pull_request"]):
        return "gitea"
    if any(t in sql_lower for t in ["pages", '"pagetags"', '"pagehistory"', '"pagelinks"']):
        return "wikijs"
    if any(t in sql_lower for t in ["posts", "channels", "channelmembers"]):
        return "mattermost"
    # Secondary: less specific table names
    if "tags" in sql_lower and "page" in sql_lower:
        return "wikijs"

    # Fallback: infer from file path
    path_str = str(postcond_file).lower()
    if "gitea" in path_str or "repo" in path_str or "issue" in path_str:
        return "gitea"
    if "wiki" in path_str or "page" in path_str:
        return "wikijs"
    if "mattermost" in path_str or "chat" in path_str or "message" in path_str or "channel" in path_str:
        return "mattermost"

    # Default to gitea
    return "gitea"


def execute_postcondition(sql: str, db_key: str) -> tuple[bool, str]:
    """
    Execute a single postcondition query.

    Returns:
        (passed: bool, detail: str)
    """
    conn = DB_CONNECTIONS[db_key]

    # Escape single quotes in SQL for shell
    escaped_sql = sql.replace("'", "'\\''")
    cmd = (
        f"docker exec {conn['container']} psql -U {conn['user']} "
        f"-d {conn['database']} -t -A -c '{escaped_sql}'"
    )

    try:
        import platform
        bash = r"C:\Program Files\Git\usr\bin\bash.exe" if platform.system() == "Windows" else "bash"
        result = subprocess.run(
            [bash, "-c", cmd],
            capture_output=True,
            text=True,
            timeout=10,
        )

        output = result.stdout.strip()

        if result.returncode != 0:
            return False, f"Query error: {result.stderr[:200]}"

        # Parse boolean result
        # PostgreSQL returns 't' for true, 'f' for false
        if output.lower() in ("t", "true", "1"):
            return True, "passed"
        elif output.lower() in ("f", "false", "0"):
            return False, f"condition not met (got: {output})"
        elif output == "":
            return False, "no rows returned"
        else:
            # Try to interpret as a value
            return False, f"unexpected result: {output}"

    except subprocess.TimeoutExpired:
        return False, "query timed out"
    except Exception as e:
        return False, f"execution error: {str(e)}"


def verify_postconditions(postcond_file: Path, arm: str = "sql") -> dict:
    """
    Verify all postconditions in a file.

    Returns:
        dict with score, functional_class, and details
    """
    postconditions = parse_postconditions(postcond_file)

    if not postconditions:
        return {
            "score": 0.0,
            "functional_class": "unknown",
            "details": {"error": "No postconditions found in file"},
        }

    results = {}
    passed = 0
    total = len(postconditions)

    for pc in postconditions:
        db_key = determine_target_db(pc["sql"], postcond_file)
        ok, detail = execute_postcondition(pc["sql"], db_key)
        results[pc["name"]] = {
            "passed": ok,
            "detail": detail,
            "database": db_key,
        }
        if ok:
            passed += 1

    # Compute score
    score = passed / total if total > 0 else 0.0

    # Determine functional class
    # A = Full: all postconditions pass (app-level correctness)
    # B = Data-only: most pass but some fail (data exists but side effects missing)
    # C = Partial: some pass, some fail
    if score >= 1.0:
        functional_class = "A"  # Full
    elif score >= 0.5:
        functional_class = "B"  # Data-only
    elif score > 0:
        functional_class = "C"  # Partial
    else:
        functional_class = "F"  # Failed

    return {
        "score": round(score, 4),
        "functional_class": functional_class,
        "passed": passed,
        "total": total,
        "details": results,
    }


def main():
    """CLI interface for verifying postconditions."""
    if len(sys.argv) < 2:
        print("Usage: python verify_scenario.py <postconditions.sql> [arm]")
        print("       python verify_scenario.py <result.json>")
        sys.exit(1)

    path = Path(sys.argv[1])
    arm = sys.argv[2] if len(sys.argv) > 2 else "sql"

    if path.suffix == ".json":
        # Load result file and find the postconditions
        with open(path) as f:
            result = json.load(f)
        print(f"Result for {result.get('scenario_id', '?')}:")
        print(f"  Score: {result.get('completion_score', '?')}")
        print(f"  Class: {result.get('functional_class', '?')}")
        if "postconditions" in result:
            for name, detail in result["postconditions"].items():
                status = "PASS" if detail.get("passed") else "FAIL"
                print(f"  [{status}] {name}: {detail.get('detail', '')}")
    elif path.suffix == ".sql":
        # Verify postconditions directly
        results = verify_postconditions(path, arm)
        print(f"Score: {results['score']:.2f} ({results['passed']}/{results['total']})")
        print(f"Class: {results['functional_class']}")
        print()
        for name, detail in results["details"].items():
            status = "PASS" if detail["passed"] else "FAIL"
            print(f"  [{status}] {name}")
            if not detail["passed"]:
                print(f"         {detail['detail']}")
    else:
        print(f"Unknown file type: {path.suffix}")
        sys.exit(1)


if __name__ == "__main__":
    main()
