"""
Postcondition verifier for experiment scenarios.

Supports both file-based postconditions (legacy) and inline SQL postconditions.
"""

import json
import os
import platform
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
    "miniflux": {
        "container": "pg-miniflux",
        "database": "miniflux",
        "user": "agent_ro",
    },
    "vikunja": {
        "container": "pg-vikunja",
        "database": "vikunja",
        "user": "agent_ro",
    },
    "mattermost": {
        "container": "pg-mattermost",
        "database": "mattermost",
        "user": "agent_ro",
    },
}

# Table-to-app mapping for auto-detection
TABLE_APP_MAP = {
    "gitea": ["repository", "issue", '"user"', "label", "issue_label",
              "milestone", "pull_request", "comment"],
    "miniflux": ["feeds", "entries", "categories", "feed_icons",
                 "enclosures", "integrations"],
    "vikunja": ["tasks", "projects", "labels", "label_tasks",
                "buckets", "team_members"],
    "mattermost": ["posts", "channels", "channelmembers", "teams",
                    "teammembers", "reactions", "fileinfo"],
}


def _find_bash() -> str:
    if platform.system() == "Windows":
        git_bash = r"C:\Program Files\Git\usr\bin\bash.exe"
        if os.path.exists(git_bash):
            return git_bash
    return "bash"


BASH_PATH = _find_bash()


def determine_target_db(sql: str, hint: str = None) -> str:
    """Determine which database a postcondition should run against."""
    # Explicit hint takes priority
    if hint and hint in DB_CONNECTIONS:
        return hint

    sql_lower = sql.lower()
    for app, tables in TABLE_APP_MAP.items():
        for table in tables:
            if table.strip('"').lower() in sql_lower:
                return app

    return "gitea"  # fallback


def execute_postcondition(sql: str, db_key: str) -> tuple[bool, str]:
    """Execute a single postcondition query. Returns (passed, detail)."""
    conn = DB_CONNECTIONS[db_key]

    escaped_sql = sql.replace("'", "'\\''")
    cmd = (
        f"docker exec {conn['container']} psql -U {conn['user']} "
        f"-d {conn['database']} -t -A -c '{escaped_sql}'"
    )

    try:
        result = subprocess.run(
            [BASH_PATH, "-c", cmd],
            capture_output=True, text=True, timeout=10,
        )

        output = result.stdout.strip()

        if result.returncode != 0:
            return False, f"Query error: {result.stderr[:200]}"

        if output.lower() in ("t", "true", "1"):
            return True, "passed"
        elif output.lower() in ("f", "false", "0"):
            return False, f"condition not met (got: {output})"
        elif output == "":
            return False, "no rows returned"
        else:
            return False, f"unexpected result: {output}"

    except subprocess.TimeoutExpired:
        return False, "query timed out"
    except Exception as e:
        return False, f"execution error: {str(e)}"


def verify_inline_postcondition(sql: str, target_db: str = None) -> dict:
    """Verify a single inline postcondition SQL string."""
    if not sql:
        return {"score": 1.0, "functional_class": "skip", "passed": 0,
                "total": 0, "details": {"note": "no postcondition defined"}}

    db_key = determine_target_db(sql, hint=target_db)
    ok, detail = execute_postcondition(sql, db_key)

    return {
        "score": 1.0 if ok else 0.0,
        "functional_class": "A" if ok else "F",
        "passed": 1 if ok else 0,
        "total": 1,
        "details": {"postcondition": {"passed": ok, "detail": detail, "database": db_key}},
    }


def parse_postconditions(sql_file: Path) -> list[dict]:
    """Parse a postconditions SQL file into individual checks."""
    content = sql_file.read_text()
    postconditions = []
    blocks = re.split(r'(--\s*PC\d+:.*)', content)
    current_name = None
    current_sql = ""

    for block in blocks:
        block = block.strip()
        if not block:
            continue
        if re.match(r'--\s*PC\d+:', block):
            if current_name and current_sql.strip():
                postconditions.append({"name": current_name, "sql": current_sql.strip()})
            current_name = block.lstrip("- ").strip()
            current_sql = ""
        else:
            current_sql += block + "\n"

    if current_name and current_sql.strip():
        postconditions.append({"name": current_name, "sql": current_sql.strip()})

    return postconditions


def verify_postconditions(postcond_file: Path, arm: str = "sql") -> dict:
    """Verify all postconditions in a file."""
    postconditions = parse_postconditions(postcond_file)

    if not postconditions:
        return {"score": 0.0, "functional_class": "unknown", "passed": 0,
                "total": 0, "details": {"error": "No postconditions found"}}

    results = {}
    passed = 0

    for pc in postconditions:
        db_key = determine_target_db(pc["sql"])
        ok, detail = execute_postcondition(pc["sql"], db_key)
        results[pc["name"]] = {"passed": ok, "detail": detail, "database": db_key}
        if ok:
            passed += 1

    total = len(postconditions)
    score = passed / total if total > 0 else 0.0

    if score >= 1.0:
        fc = "A"
    elif score >= 0.5:
        fc = "B"
    elif score > 0:
        fc = "C"
    else:
        fc = "F"

    return {"score": round(score, 4), "functional_class": fc,
            "passed": passed, "total": total, "details": results}


def main():
    if len(sys.argv) < 2:
        print("Usage: python verify_scenario.py <postconditions.sql> [arm]")
        print("       python verify_scenario.py --inline 'SELECT ...' [target_db]")
        sys.exit(1)

    if sys.argv[1] == "--inline":
        sql = sys.argv[2]
        target = sys.argv[3] if len(sys.argv) > 3 else None
        result = verify_inline_postcondition(sql, target)
        status = "PASS" if result["score"] >= 1.0 else "FAIL"
        print(f"[{status}] {result['details']}")
    else:
        path = Path(sys.argv[1])
        arm = sys.argv[2] if len(sys.argv) > 2 else "sql"
        results = verify_postconditions(path, arm)
        print(f"Score: {results['score']:.2f} ({results['passed']}/{results['total']})")
        print(f"Class: {results['functional_class']}")
        for name, detail in results["details"].items():
            status = "PASS" if detail["passed"] else "FAIL"
            print(f"  [{status}] {name}")
            if not detail["passed"]:
                print(f"         {detail['detail']}")


if __name__ == "__main__":
    main()
