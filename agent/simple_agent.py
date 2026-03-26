"""
Minimal agent: prove that bash + a simple app map = operate any number of apps.

This is the entire agent. The system prompt is just the map.
"""

import json
import os
import platform
import subprocess
import time
from pathlib import Path

from openai import OpenAI

# ── Find bash ──
BASH = r"C:\Program Files\Git\usr\bin\bash.exe" if platform.system() == "Windows" else "bash"

# ── LLM client ──
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ["OPENROUTER_API_KEY"],
)

MODEL = os.environ.get("MODEL", "minimax/minimax-m2.7")

# ── Load the map ──
MAP_PATH = Path(__file__).parent.parent / "app_map.json"
with open(MAP_PATH) as f:
    APP_MAP = json.load(f)

# ── Build system prompt from the map — this is the entire "OS" ──
app_lines = []
for name, info in APP_MAP["apps"].items():
    app_lines.append(f"- **{name}** ({info['what']}): `{info['db']}`")
APP_LIST = "\n".join(app_lines)

SYSTEM_PROMPT = f"""You are an AI agent. You have one tool: bash.

You can operate these 10 applications by querying their databases directly:

{APP_LIST}

## How to use
- To run a single SQL query: `<db command> -c "SELECT ..."`
  - PostgreSQL example: `docker exec pg-gitea psql -U postgres -d gitea -c "SELECT * FROM repository LIMIT 5;"`
  - MySQL example: `docker exec mysql-bookstack mysql -u bookstack -psecret bookstack -e "SELECT * FROM pages LIMIT 5;"`
- To discover a schema: use `\\dt` (PostgreSQL) or `SHOW TABLES` (MySQL), then `\\d tablename` or `DESCRIBE tablename`
- To move data between apps: SELECT from one DB, use the result to INSERT into another
- Use `-t -A` flags with psql for clean output (no headers/borders)
- Always inspect schema before writing

You have full read/write access. Be efficient. Explain briefly what you do."""

# ── Tool ──
TOOLS = [{
    "type": "function",
    "function": {
        "name": "bash",
        "description": "Execute a bash command",
        "parameters": {
            "type": "object",
            "properties": {"command": {"type": "string", "description": "bash command"}},
            "required": ["command"],
        },
    },
}]


def run_bash(command: str) -> str:
    """Execute bash and return output."""
    try:
        r = subprocess.run([BASH, "-c", command], capture_output=True, text=True, timeout=30)
        out = r.stdout[:50000]
        if r.stderr:
            out += f"\n[stderr]: {r.stderr[:5000]}"
        if r.returncode != 0:
            out += f"\n[exit code]: {r.returncode}"
        return out or "(no output)"
    except subprocess.TimeoutExpired:
        return "[timed out]"


def run_agent(task: str, max_turns: int = 30) -> dict:
    """Run the agent on a task. Returns transcript. Hard cap at max_turns to prevent infinite loops."""
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": task},
    ]
    transcript = {"task": task, "model": MODEL, "turns": [], "total_tokens": 0}
    start = time.time()

    for turn in range(max_turns):
        resp = client.chat.completions.create(
            model=MODEL,
            temperature=0,
            max_tokens=4096,
            tools=TOOLS,
            messages=messages,
            extra_body={"provider": {"sort": "throughput"}},
        )
        choice = resp.choices[0]
        msg = choice.message

        # Track tokens (usage can be None on some providers)
        if resp.usage:
            pt = resp.usage.prompt_tokens or 0
            ct = resp.usage.completion_tokens or 0
            transcript["total_tokens"] += (pt + ct)
            if turn == 0:
                transcript["first_turn_tokens"] = pt

        # Log
        turn_log = {"turn": turn, "text": msg.content or "", "tool_calls": []}

        if not msg.tool_calls:
            transcript["turns"].append(turn_log)
            break

        messages.append(msg.model_dump())

        for tc in msg.tool_calls:
            try:
                args = json.loads(tc.function.arguments) if tc.function.arguments else {}
            except (json.JSONDecodeError, TypeError):
                args = {"command": str(tc.function.arguments)}
            cmd = args.get("command", "")
            turn_log["tool_calls"].append(cmd)
            print(f"  [Turn {turn}] $ {cmd[:120]}")

            output = run_bash(cmd)
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": output})

        transcript["turns"].append(turn_log)

    transcript["duration_s"] = round(time.time() - start, 1)
    transcript["num_turns"] = len(transcript["turns"])

    # Print final answer
    last_text = transcript["turns"][-1]["text"]
    if last_text:
        print(f"\n{'─'*60}")
        print(last_text[:500].encode("utf-8", errors="replace").decode("utf-8", errors="replace"))

    print(f"\n  ⏱ {transcript['duration_s']}s | 🔄 {transcript['num_turns']} turns | 🪙 {transcript['total_tokens']} tokens")
    return transcript


if __name__ == "__main__":
    if platform.system() == "Windows" and hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    task = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else input("Task: ")
    result = run_agent(task)

    # Save
    Path("../results").mkdir(exist_ok=True)
    with open(f"../results/run_{int(time.time())}.json", "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False, default=str)
