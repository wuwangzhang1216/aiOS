"""
MCP Agent: operates 10 applications via MCP servers.

Mirror of simple_agent.py but uses MCP tool schemas instead of bash+SQL.
Same LLM, same temperature, same max_turns — only the interface differs.
"""

import asyncio
import json
import os
import platform
import subprocess
import sys
import time
from contextlib import asynccontextmanager
from pathlib import Path

from openai import OpenAI

# Fix Windows encoding
if platform.system() == "Windows":
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

BASH = r"C:\Program Files\Git\usr\bin\bash.exe" if platform.system() == "Windows" else "bash"

# ── LLM client (same as bash+DB agent) ──
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ["OPENROUTER_API_KEY"],
)
MODEL = os.environ.get("MODEL", "minimax/minimax-m2.7")

# ── Load MCP config ──
CONFIG_PATH = Path(__file__).parent / "mcp_config.json"
with open(CONFIG_PATH, encoding="utf-8") as f:
    MCP_CONFIG = json.load(f)


class MCPServerManager:
    """Manages MCP server subprocesses and tool aggregation."""

    def __init__(self):
        self.servers = {}  # app_name -> subprocess
        self.tools = []  # aggregated OpenAI-format tools
        self.tool_to_server = {}  # tool_name -> app_name
        self.raw_tools_by_app = {}  # app_name -> list of raw tool defs
        self.total_schema_tokens = 0

    def start_all(self):
        """Start all MCP servers and collect their tools."""
        print("Starting MCP servers...")
        for app_name, config in MCP_CONFIG["servers"].items():
            try:
                self._start_server(app_name, config)
            except Exception as e:
                print(f"  [{app_name}] FAILED: {e}")

        print(f"\nMCP servers ready: {len(self.servers)}/{len(MCP_CONFIG['servers'])}")
        print(f"Total tools: {len(self.tools)}")
        print(f"Estimated schema tokens: {self._estimate_tokens()}")

    def _start_server(self, app_name: str, config: dict):
        """Start a single MCP server and collect its tools via initialize + tools/list."""
        # Resolve env vars
        env = os.environ.copy()
        for k, v in config.get("env", {}).items():
            if v.startswith("${") and v.endswith("}"):
                env_key = v[2:-1]
                env[k] = os.environ.get(env_key, "")
            else:
                env[k] = v

        cmd = [config["command"]] + config.get("args", [])
        print(f"  [{app_name}] Starting: {' '.join(cmd)}...", end=" ", flush=True)

        try:
            popen_kwargs = dict(
                stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, env=env,
                encoding="utf-8", errors="replace",
            )
            if platform.system() == "Windows":
                popen_kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
                # On Windows, npx must be invoked via shell or as npx.cmd
                popen_kwargs["shell"] = True
                cmd = " ".join(cmd)  # shell=True needs string on Windows
            proc = subprocess.Popen(cmd, **popen_kwargs)

            # MCP protocol: send initialize, then tools/list
            init_msg = {
                "jsonrpc": "2.0", "id": 1, "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "experiment-agent", "version": "1.0"}
                }
            }
            self._send_jsonrpc(proc, init_msg)
            init_resp = self._recv_jsonrpc(proc, timeout=15)

            if not init_resp or "error" in init_resp:
                proc.kill()
                print(f"INIT FAILED: {init_resp}")
                return

            # Send initialized notification
            self._send_jsonrpc(proc, {
                "jsonrpc": "2.0", "method": "notifications/initialized"
            })

            # Request tool list
            tools_msg = {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
            self._send_jsonrpc(proc, tools_msg)
            tools_resp = self._recv_jsonrpc(proc, timeout=10)

            if not tools_resp or "error" in tools_resp:
                proc.kill()
                print(f"TOOLS FAILED: {tools_resp}")
                return

            raw_tools = tools_resp.get("result", {}).get("tools", [])
            self.servers[app_name] = proc
            self.raw_tools_by_app[app_name] = raw_tools

            # Convert MCP tools to OpenAI function format with app prefix
            for tool in raw_tools:
                prefixed_name = f"{app_name}__{tool['name']}"
                openai_tool = {
                    "type": "function",
                    "function": {
                        "name": prefixed_name,
                        "description": f"[{app_name}] {tool.get('description', '')}",
                        "parameters": tool.get("inputSchema", {"type": "object", "properties": {}}),
                    },
                }
                self.tools.append(openai_tool)
                self.tool_to_server[prefixed_name] = app_name

            print(f"OK ({len(raw_tools)} tools)")

        except Exception as e:
            print(f"ERROR: {e}")

    def call_tool(self, prefixed_name: str, arguments: dict) -> str:
        """Call a tool on the appropriate MCP server."""
        app_name = self.tool_to_server.get(prefixed_name)
        if not app_name or app_name not in self.servers:
            return f"Error: unknown tool {prefixed_name}"

        # Strip prefix to get original tool name
        original_name = prefixed_name.split("__", 1)[1]
        proc = self.servers[app_name]

        call_msg = {
            "jsonrpc": "2.0", "id": 3,
            "method": "tools/call",
            "params": {"name": original_name, "arguments": arguments}
        }

        try:
            self._send_jsonrpc(proc, call_msg)
            resp = self._recv_jsonrpc(proc, timeout=30)

            if not resp:
                return "Error: no response from MCP server (timeout)"
            if "error" in resp:
                return f"Error: {resp['error']}"

            result = resp.get("result", {})
            content = result.get("content", [])
            texts = []
            for item in content:
                if isinstance(item, dict) and "text" in item:
                    texts.append(item["text"])
                elif isinstance(item, str):
                    texts.append(item)

            return "\n".join(texts) if texts else json.dumps(result, indent=2, default=str)

        except Exception as e:
            return f"Error calling {prefixed_name}: {e}"

    def _send_jsonrpc(self, proc, msg):
        """Send a JSON-RPC message as a single line (no Content-Length framing)."""
        data = json.dumps(msg)
        proc.stdin.write(data + "\n")
        proc.stdin.flush()

    def _recv_jsonrpc(self, proc, timeout=15):
        """Receive a JSON-RPC response — handles both bare JSON lines and Content-Length framing."""
        start = time.time()
        while time.time() - start < timeout:
            line = proc.stdout.readline()
            if not line:
                time.sleep(0.1)
                continue

            stripped = line.strip()
            if not stripped:
                continue

            # Try bare JSON (most servers use this)
            try:
                obj = json.loads(stripped)
                # Return responses (have "id") and skip notifications (no "id")
                if "id" in obj or "result" in obj or "error" in obj:
                    return obj
                # It's a notification — keep reading
                continue
            except (json.JSONDecodeError, ValueError):
                pass

            # Content-Length framing — read the body after the header
            if stripped.lower().startswith("content-length:"):
                content_length = int(stripped.split(":")[1].strip())
                # Read blank line
                proc.stdout.readline()
                # Read body
                body = proc.stdout.read(content_length)
                try:
                    return json.loads(body)
                except (json.JSONDecodeError, ValueError):
                    continue

        return None

    def _estimate_tokens(self) -> int:
        """Rough estimate of total tool schema tokens."""
        schema_str = json.dumps(self.tools)
        return len(schema_str) // 4  # ~4 chars per token

    def stop_all(self):
        """Kill all MCP server processes."""
        for name, proc in self.servers.items():
            try:
                proc.kill()
            except:
                pass
        self.servers.clear()

    def get_static_metrics(self) -> dict:
        """Return static cost metrics for the MCP arm."""
        return {
            "num_servers": len(self.servers),
            "num_tools_total": len(self.tools),
            "tools_per_app": {
                app: len(tools) for app, tools in self.raw_tools_by_app.items()
            },
            "estimated_schema_tokens": self._estimate_tokens(),
            "config_lines": sum(1 for _ in open(CONFIG_PATH, encoding="utf-8")),
        }


# ── System prompt for MCP arm (minimal — tools ARE the documentation) ──
SYSTEM_PROMPT = """You are an AI agent operating 10 applications via MCP tools.

Each tool is prefixed with the app name:
- gitea__* — Git & Code (repos, issues, users)
- wikijs__* — Wiki / Knowledge Base (pages, tags)
- mattermost__* — Team Chat (channels, posts, users)
- vikunja__* — Task Management (tasks, projects)
- nocodb__* — Spreadsheet / Database UI
- miniflux__* — RSS Reader (feeds, entries)
- grafana__* — Monitoring Dashboard (dashboards, datasources)
- redmine__* — Issue Tracker (issues, projects, users)
- directus__* — Headless CMS (collections, items, assets)
- hasura__* — GraphQL Engine (queries, mutations, metadata)

Use the appropriate tools to accomplish the task.
Be efficient. Explain briefly what you do."""


def run_mcp_agent(task: str, max_turns: int = 30) -> dict:
    """Run the MCP agent on a task."""
    mgr = MCPServerManager()
    mgr.start_all()

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": task},
    ]

    transcript = {
        "task": task, "model": MODEL, "arm": "mcp",
        "turns": [], "total_tokens": 0,
        "static_metrics": mgr.get_static_metrics(),
    }
    start = time.time()

    try:
        for turn in range(max_turns):
            resp = client.chat.completions.create(
                model=MODEL,
                temperature=0,
                max_tokens=4096,
                tools=mgr.tools if mgr.tools else None,
                messages=messages,
                extra_body={"provider": {"sort": "throughput"}},
            )
            choice = resp.choices[0]
            msg = choice.message

            if resp.usage:
                pt = resp.usage.prompt_tokens or 0
                ct = resp.usage.completion_tokens or 0
                transcript["total_tokens"] += (pt + ct)
                if turn == 0:
                    transcript["first_turn_tokens"] = pt

            turn_log = {"turn": turn, "text": msg.content or "", "tool_calls": []}

            if not msg.tool_calls:
                transcript["turns"].append(turn_log)
                break

            messages.append(msg.model_dump())

            for tc in msg.tool_calls:
                try:
                    args = json.loads(tc.function.arguments) if tc.function.arguments else {}
                except (json.JSONDecodeError, TypeError):
                    args = {}
                tool_name = tc.function.name
                turn_log["tool_calls"].append({"tool": tool_name, "args": args})
                print(f"  [Turn {turn}] {tool_name}({json.dumps(args)[:80]})")

                output = mgr.call_tool(tool_name, args)
                messages.append({"role": "tool", "tool_call_id": tc.id, "content": output[:10000]})

            transcript["turns"].append(turn_log)

    finally:
        mgr.stop_all()

    transcript["duration_s"] = round(time.time() - start, 1)
    transcript["num_turns"] = len(transcript["turns"])
    transcript["num_tool_calls"] = sum(len(t["tool_calls"]) for t in transcript["turns"])

    # Print final answer
    last_text = transcript["turns"][-1]["text"] if transcript["turns"] else ""
    if last_text:
        print(f"\n{'─'*60}")
        print(last_text[:500])

    print(f"\n  [MCP] {transcript['duration_s']}s | {transcript['num_turns']} turns | "
          f"{transcript['num_tool_calls']} tool calls | {transcript['total_tokens']} tokens")

    return transcript


if __name__ == "__main__":
    task = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else input("Task: ")
    result = run_mcp_agent(task)

    Path("../results/comparison").mkdir(parents=True, exist_ok=True)
    with open(f"../results/comparison/mcp_run_{int(time.time())}.json", "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False, default=str)
