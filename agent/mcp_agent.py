"""
MCP Agent: uses MCP server tools instead of bash+SQL.

Same LLM, same temperature, same max_turns, same transcript format.
Only the tool interface differs — MCP tools vs. bash.
"""

import json
import os
import platform
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from openai import OpenAI

from agent import AgentConfig, AgentTranscript

# ── MCP Server Manager ──

MCP_CONFIG_PATH = Path(__file__).parent.parent / "mcp_control" / "mcp_config.json"


class MCPServerManager:
    """Manages MCP server subprocesses and tool aggregation."""

    def __init__(self):
        self.servers = {}        # app_name -> subprocess
        self.tools = []          # aggregated OpenAI-format tools
        self.tool_to_server = {} # tool_name -> app_name
        self.raw_tools_by_app = {}

    def start_all(self):
        with open(MCP_CONFIG_PATH, encoding="utf-8") as f:
            config = json.load(f)

        for app_name, srv_config in config["servers"].items():
            try:
                self._start_server(app_name, srv_config)
            except Exception as e:
                print(f"  [{app_name}] FAILED: {e}")

        print(f"MCP servers ready: {len(self.servers)}/{len(config['servers'])}, "
              f"{len(self.tools)} tools, ~{self._estimate_tokens()} schema tokens")

    def _start_server(self, app_name: str, config: dict):
        env = os.environ.copy()
        for k, v in config.get("env", {}).items():
            if v.startswith("${") and v.endswith("}"):
                env[k] = os.environ.get(v[2:-1], "")
            else:
                env[k] = v

        cmd = [config["command"]] + config.get("args", [])
        cwd = str(Path(__file__).parent.parent / "mcp_control")

        proc = subprocess.Popen(
            cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, env=env, cwd=cwd,
            encoding="utf-8", errors="replace",
        )

        # MCP initialize
        self._send(proc, {
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "experiment-agent", "version": "1.0"},
            },
        })
        init_resp = self._recv(proc, timeout=15)
        if not init_resp or "error" in init_resp:
            proc.kill()
            return

        self._send(proc, {"jsonrpc": "2.0", "method": "notifications/initialized"})

        # Get tools
        self._send(proc, {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
        tools_resp = self._recv(proc, timeout=10)
        if not tools_resp or "error" in tools_resp:
            proc.kill()
            return

        raw_tools = tools_resp.get("result", {}).get("tools", [])
        self.servers[app_name] = proc
        self.raw_tools_by_app[app_name] = raw_tools

        for tool in raw_tools:
            prefixed = f"{app_name}__{tool['name']}"
            self.tools.append({
                "type": "function",
                "function": {
                    "name": prefixed,
                    "description": f"[{app_name}] {tool.get('description', '')}",
                    "parameters": tool.get("inputSchema", {"type": "object", "properties": {}}),
                },
            })
            self.tool_to_server[prefixed] = app_name

    def call_tool(self, prefixed_name: str, arguments: dict) -> str:
        app_name = self.tool_to_server.get(prefixed_name)
        if not app_name or app_name not in self.servers:
            return f"Error: unknown tool {prefixed_name}"

        original_name = prefixed_name.split("__", 1)[1]
        proc = self.servers[app_name]

        self._send(proc, {
            "jsonrpc": "2.0", "id": 3,
            "method": "tools/call",
            "params": {"name": original_name, "arguments": arguments},
        })
        resp = self._recv(proc, timeout=30)

        if not resp:
            return "Error: no response (timeout)"
        if "error" in resp:
            return f"Error: {resp['error']}"

        content = resp.get("result", {}).get("content", [])
        texts = [
            item["text"] if isinstance(item, dict) and "text" in item else str(item)
            for item in content
        ]
        return "\n".join(texts) if texts else json.dumps(resp.get("result", {}), indent=2, default=str)

    def _send(self, proc, msg):
        proc.stdin.write(json.dumps(msg) + "\n")
        proc.stdin.flush()

    def _recv(self, proc, timeout=15):
        start = time.time()
        while time.time() - start < timeout:
            line = proc.stdout.readline()
            if not line:
                time.sleep(0.05)
                continue
            stripped = line.strip()
            if not stripped:
                continue
            try:
                obj = json.loads(stripped)
                if "id" in obj or "result" in obj or "error" in obj:
                    return obj
                continue
            except (json.JSONDecodeError, ValueError):
                pass
            if stripped.lower().startswith("content-length:"):
                content_length = int(stripped.split(":")[1].strip())
                proc.stdout.readline()  # blank line
                body = proc.stdout.read(content_length)
                try:
                    return json.loads(body)
                except (json.JSONDecodeError, ValueError):
                    continue
        return None

    def _estimate_tokens(self) -> int:
        return len(json.dumps(self.tools)) // 4

    def stop_all(self):
        for proc in self.servers.values():
            try:
                proc.kill()
            except Exception:
                pass
        self.servers.clear()


# ── MCP Agent ──

MCP_SYSTEM_PROMPT = """You are an AI agent operating as part of an AI-native operating system experiment.

## Your Capabilities
You have MCP tools for interacting with 4 applications:
- gitea__* — Git & Code (repos, issues, users, labels)
- miniflux__* — RSS Reader (feeds, entries, categories)
- vikunja__* — Task Management (tasks, projects, labels)
- mattermost__* — Team Chat (channels, posts, users)

## How to Work
1. Use the appropriate tools to accomplish the task
2. Be efficient — minimize unnecessary tool calls
3. For cross-app tasks, read from one app then write to another
4. Report what you did when finished

## Rules
- Use list/search tools before create/update tools
- Handle errors gracefully
- Complete the task as accurately and efficiently as possible
"""


class MCPAgent:
    """AI agent using MCP tools instead of bash."""

    def __init__(self, config: AgentConfig):
        self.config = config
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.environ.get("OPENROUTER_API_KEY", ""),
        )
        self.mgr = MCPServerManager()

    def _llm_call_with_retry(self, max_retries=2, **kwargs):
        kwargs.setdefault("timeout", 120)
        for attempt in range(max_retries + 1):
            try:
                return self.client.chat.completions.create(**kwargs)
            except Exception as e:
                if attempt < max_retries and any(k in str(e).lower() for k in ("timeout", "502", "503", "rate", "connect")):
                    time.sleep(10 * (attempt + 1))
                else:
                    raise

    def run(self, task: str, scenario_id: str, run_number: int) -> AgentTranscript:
        self.mgr.start_all()

        transcript = AgentTranscript(
            scenario_id=scenario_id,
            arm="mcp",
            run_number=run_number,
            config={
                "model": self.config.model,
                "temperature": self.config.temperature,
                "max_tokens": self.config.max_tokens,
                "arm": "mcp",
            },
            start_time=time.time(),
        )

        total_input = 0
        total_output = 0
        tool_call_count = 0
        tool_durations = []

        messages = [
            {"role": "system", "content": MCP_SYSTEM_PROMPT},
            {"role": "user", "content": task},
        ]

        try:
            for turn in range(self.config.max_turns):
                llm_start = time.time()
                response = self._llm_call_with_retry(
                    model=self.config.model,
                    max_tokens=self.config.max_tokens,
                    temperature=self.config.temperature,
                    tools=self.mgr.tools if self.mgr.tools else None,
                    messages=messages,
                    extra_body={"provider": {"sort": "throughput"}},
                )
                llm_ms = (time.time() - llm_start) * 1000

                choice = response.choices[0]
                msg = choice.message
                usage = response.usage
                inp = usage.prompt_tokens if usage else 0
                out = usage.completion_tokens if usage else 0
                total_input += inp
                total_output += out

                turn_data = {
                    "turn": turn,
                    "llm_duration_ms": llm_ms,
                    "input_tokens": inp,
                    "output_tokens": out,
                    "finish_reason": choice.finish_reason,
                    "content": [],
                }

                if msg.content:
                    turn_data["content"].append({"type": "text", "text": msg.content})

                tool_calls = msg.tool_calls or []
                for tc in tool_calls:
                    try:
                        args = json.loads(tc.function.arguments) if tc.function.arguments else {}
                    except (json.JSONDecodeError, TypeError):
                        args = {}
                    turn_data["content"].append({
                        "type": "tool_use",
                        "tool": tc.function.name,
                        "input": args,
                        "call_id": tc.id,
                    })

                transcript.turns.append(turn_data)

                if choice.finish_reason != "tool_calls" and not tool_calls:
                    break

                messages.append(msg.model_dump())

                for tc in tool_calls:
                    try:
                        args = json.loads(tc.function.arguments) if tc.function.arguments else {}
                    except (json.JSONDecodeError, TypeError):
                        args = {}

                    tool_start = time.time()
                    output = self.mgr.call_tool(tc.function.name, args)
                    tool_ms = (time.time() - tool_start) * 1000
                    tool_durations.append(tool_ms)
                    tool_call_count += 1

                    print(f"  [Turn {turn}] {tc.function.name}({json.dumps(args)[:60]}) -> {len(output)} chars, {tool_ms:.0f}ms")

                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": output[:10000],
                    })

        finally:
            self.mgr.stop_all()

        transcript.end_time = time.time()
        transcript.measurements = {
            "total_tokens": {
                "input": total_input,
                "output": total_output,
                "total": total_input + total_output,
            },
            "mcp_ops": {
                "total_tool_calls": tool_call_count,
                "total_tool_ms": round(sum(tool_durations), 1),
                "tools_per_app": {
                    app: len(tools) for app, tools in self.mgr.raw_tools_by_app.items()
                },
                "schema_tokens": self.mgr._estimate_tokens(),
            },
        }

        return transcript
