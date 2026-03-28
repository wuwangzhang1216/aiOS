"""
Core agent loop: OpenRouter (OpenAI-compatible) + single bash tool.

This is the bash+SQL experimental arm. The agent receives a task description
and uses only bash (with psql/mysql CLI) to accomplish it by directly
querying and writing to application databases.

Uses OpenRouter as the LLM gateway, allowing easy model switching
(Claude, GPT, Gemini, open-source models, etc.) via a single API.
"""

import json
import os
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path

from openai import OpenAI

from measure import Measurement, MeasurementCollector
from safety import SafetyGuard, SafetyViolation
from system_prompt import build_system_prompt


@dataclass
class BashResult:
    """Result of executing a bash command."""
    command: str
    stdout: str
    stderr: str
    returncode: int
    duration_ms: float


@dataclass
class AgentConfig:
    """Configuration for the experiment agent."""
    model: str = "minimax/minimax-m2.7"
    temperature: float = 0.0
    max_tokens: int = 4096
    max_turns: int = 30
    bash_timeout: int = 30  # seconds
    registry_path: str = "db_registry.json"
    arm: str = "sql"  # "sql", "api", or "mcp"


@dataclass
class AgentTranscript:
    """Full transcript of an agent run."""
    scenario_id: str
    arm: str
    run_number: int
    config: dict
    turns: list = field(default_factory=list)
    measurements: dict = field(default_factory=dict)
    start_time: float = 0.0
    end_time: float = 0.0

    def to_dict(self) -> dict:
        return {
            "scenario_id": self.scenario_id,
            "arm": self.arm,
            "run_number": self.run_number,
            "config": self.config,
            "turns": self.turns,
            "measurements": self.measurements,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "total_duration_ms": (self.end_time - self.start_time) * 1000,
        }


def _find_bash() -> str:
    """Find the correct bash executable (Git Bash on Windows, /bin/bash elsewhere)."""
    import platform
    if platform.system() == "Windows":
        # Prefer Git Bash over WSL bash
        git_bash = r"C:\Program Files\Git\usr\bin\bash.exe"
        if os.path.exists(git_bash):
            return git_bash
    return "bash"


BASH_PATH = _find_bash()


def execute_bash(command: str, timeout: int = 30) -> BashResult:
    """Execute a bash command and return the result."""
    start = time.time()
    try:
        result = subprocess.run(
            [BASH_PATH, "-c", command],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        duration_ms = (time.time() - start) * 1000
        return BashResult(
            command=command,
            stdout=result.stdout[:50000],  # Truncate very long output
            stderr=result.stderr[:10000],
            returncode=result.returncode,
            duration_ms=duration_ms,
        )
    except subprocess.TimeoutExpired:
        duration_ms = (time.time() - start) * 1000
        return BashResult(
            command=command,
            stdout="",
            stderr=f"Command timed out after {timeout}s",
            returncode=-1,
            duration_ms=duration_ms,
        )


class Agent:
    """AI agent with single bash tool for database interaction."""

    def __init__(self, config: AgentConfig):
        self.config = config
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.environ.get("OPENROUTER_API_KEY", ""),
        )
        self.safety = SafetyGuard()
        self.collector = MeasurementCollector()

        # Load registry and build system prompt
        registry_path = Path(config.registry_path)
        with open(registry_path) as f:
            self.registry = json.load(f)

        self.system_prompt = build_system_prompt(self.registry, arm=config.arm)

        # Tool definition: single bash tool (OpenAI function calling format)
        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": "bash",
                    "description": (
                        "Execute a bash command. Use this to run psql/mysql/mongosh "
                        "commands to interact with application databases, inspect "
                        "schemas, query data, and perform operations."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "command": {
                                "type": "string",
                                "description": "The bash command to execute",
                            }
                        },
                        "required": ["command"],
                    },
                },
            }
        ]

    def _llm_call_with_retry(self, max_retries=2, **kwargs):
        kwargs.setdefault("timeout", 120)  # 2 min max per LLM call
        for attempt in range(max_retries + 1):
            try:
                return self.client.chat.completions.create(**kwargs)
            except Exception as e:
                if attempt < max_retries and any(k in str(e).lower() for k in ("timeout", "502", "503", "rate", "connect")):
                    time.sleep(10 * (attempt + 1))
                else:
                    raise

    def run(
        self, task: str, scenario_id: str, run_number: int
    ) -> AgentTranscript:
        """
        Execute a task using the agent loop.

        Args:
            task: Natural language description of the task
            scenario_id: Scenario identifier (e.g., "T1.1a")
            run_number: Run number for this variant (1-5)

        Returns:
            AgentTranscript with full execution log
        """
        transcript = AgentTranscript(
            scenario_id=scenario_id,
            arm=self.config.arm,
            run_number=run_number,
            config={
                "model": self.config.model,
                "temperature": self.config.temperature,
                "max_tokens": self.config.max_tokens,
                "arm": self.config.arm,
            },
            start_time=time.time(),
        )

        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": task},
        ]

        for turn in range(self.config.max_turns):
            # ── Call LLM via OpenRouter ──
            llm_start = time.time()
            response = self._llm_call_with_retry(
                model=self.config.model,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                tools=self.tools,
                messages=messages,
                extra_body={"provider": {"sort": "throughput"}},
            )
            llm_duration_ms = (time.time() - llm_start) * 1000

            choice = response.choices[0]
            message = choice.message

            # ── Record token usage ──
            usage = response.usage
            input_tokens = usage.prompt_tokens if usage else 0
            output_tokens = usage.completion_tokens if usage else 0
            self.collector.record_tokens(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
            )

            # ── Process response ──
            turn_data = {
                "turn": turn,
                "llm_duration_ms": llm_duration_ms,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "finish_reason": choice.finish_reason,
                "content": [],
            }

            # Record text content
            if message.content:
                turn_data["content"].append({
                    "type": "text",
                    "text": message.content,
                })

            # Check for tool calls
            tool_calls = message.tool_calls or []
            for tc in tool_calls:
                turn_data["content"].append({
                    "type": "tool_use",
                    "tool": tc.function.name,
                    "input": json.loads(tc.function.arguments),
                    "call_id": tc.id,
                })

            transcript.turns.append(turn_data)

            # If no tool calls, the agent is done
            if choice.finish_reason != "tool_calls" and not tool_calls:
                break

            # ── Execute tool calls ──
            # Add assistant message to conversation
            messages.append(message.model_dump())

            for tc in tool_calls:
                try:
                    args = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    args = {"command": tc.function.arguments}

                command = args.get("command", "")

                # Safety check
                try:
                    self.safety.check(command)
                except SafetyViolation as e:
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": f"SAFETY VIOLATION: {e}. Command blocked.",
                    })
                    self.collector.record_bash(
                        command=command,
                        duration_ms=0,
                        success=False,
                    )
                    continue

                # Execute bash command
                result = execute_bash(command, timeout=self.config.bash_timeout)

                # Record measurement
                self.collector.record_bash(
                    command=command,
                    duration_ms=result.duration_ms,
                    success=result.returncode == 0,
                )

                # Format output for the model
                output = result.stdout
                if result.stderr:
                    output += f"\n[stderr]: {result.stderr}"
                if result.returncode != 0:
                    output += f"\n[exit code]: {result.returncode}"

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": output or "(no output)",
                })

        # ── Finalize ──
        transcript.end_time = time.time()
        transcript.measurements = self.collector.summarize()

        return transcript


def run_single(
    task: str,
    scenario_id: str = "manual",
    run_number: int = 1,
    arm: str = "sql",
    registry_path: str = "db_registry.json",
    output_dir: str = "results",
    model: str = None,
) -> AgentTranscript:
    """Convenience function to run a single scenario."""
    config = AgentConfig(arm=arm, registry_path=registry_path)
    if model:
        config.model = model
    agent = Agent(config)
    transcript = agent.run(task, scenario_id, run_number)

    # Save transcript
    out_path = Path(output_dir) / arm / scenario_id
    out_path.mkdir(parents=True, exist_ok=True)
    with open(out_path / f"run_{run_number}.json", "w") as f:
        json.dump(transcript.to_dict(), f, indent=2, default=str)

    return transcript


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run bash+DB agent")
    parser.add_argument("task", help="Natural language task description")
    parser.add_argument("--scenario", default="manual", help="Scenario ID")
    parser.add_argument("--run", type=int, default=1, help="Run number")
    parser.add_argument("--arm", default="sql", choices=["sql", "api", "mcp"])
    parser.add_argument("--registry", default="db_registry.json")
    parser.add_argument("--output", default="results")
    parser.add_argument(
        "--model", default=None,
        help="OpenRouter model ID (e.g., anthropic/claude-sonnet-4, openai/gpt-4o, google/gemini-2.5-pro)"
    )
    args = parser.parse_args()

    transcript = run_single(
        task=args.task,
        scenario_id=args.scenario,
        run_number=args.run,
        arm=args.arm,
        registry_path=args.registry,
        output_dir=args.output,
        model=args.model,
    )

    print(f"\nCompleted in {transcript.measurements.get('total_duration_ms', 0):.0f}ms")
    print(f"Turns: {len(transcript.turns)}")
    print(f"Tokens: {transcript.measurements.get('total_tokens', {})}")
    print(f"SQL operations: {transcript.measurements.get('sql_ops', {})}")
