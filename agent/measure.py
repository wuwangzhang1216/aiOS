"""
Measurement framework for experiment metrics.

Intercepts and classifies all bash commands, tracks token usage,
timing, and SQL operations for analysis.
"""

import re
import time
from dataclasses import dataclass, field
from enum import Enum


class SQLCategory(str, Enum):
    """Classification of SQL operations."""
    SCHEMA_DISCOVERY = "schema_discovery"
    READ = "read"
    WRITE = "write"
    TRANSACTION = "transaction"
    FAILED = "failed"
    OTHER = "other"


@dataclass
class Measurement:
    """A single measurement data point."""
    timestamp: float
    category: str
    command: str
    duration_ms: float
    success: bool
    sql_category: str | None = None
    details: dict = field(default_factory=dict)


class SQLClassifier:
    """Classify SQL statements by type."""

    # Patterns for schema discovery
    SCHEMA_PATTERNS = [
        r"\\dt",
        r"\\d\s+\w+",
        r"\\d\+",
        r"\\dn",
        r"\\di",
        r"information_schema",
        r"pg_catalog",
        r"SHOW\s+(TABLES|COLUMNS|DATABASES|CREATE)",
        r"DESCRIBE\s+",
        r"EXPLAIN\s+",
    ]

    # Patterns for read operations
    READ_PATTERNS = [
        r"\bSELECT\b",
        r"\bWITH\b.*\bSELECT\b",
    ]

    # Patterns for write operations
    WRITE_PATTERNS = [
        r"\bINSERT\b",
        r"\bUPDATE\b",
        r"\bDELETE\b",
        r"\bUPSERT\b",
        r"\bMERGE\b",
    ]

    # Patterns for transaction control
    TRANSACTION_PATTERNS = [
        r"\bBEGIN\b",
        r"\bCOMMIT\b",
        r"\bROLLBACK\b",
        r"\bSAVEPOINT\b",
    ]

    @classmethod
    def classify(cls, command: str) -> SQLCategory:
        """Classify a bash command containing SQL."""
        upper = command.upper()

        # Check if this is even a SQL-related command
        if not any(tool in command.lower() for tool in ["psql", "mysql", "mongosh", "sqlite3"]):
            return SQLCategory.OTHER

        # Check categories — WRITE before TRANSACTION so BEGIN+INSERT = WRITE
        for pattern in cls.SCHEMA_PATTERNS:
            if re.search(pattern, command, re.IGNORECASE):
                return SQLCategory.SCHEMA_DISCOVERY

        for pattern in cls.WRITE_PATTERNS:
            if re.search(pattern, upper):
                return SQLCategory.WRITE

        for pattern in cls.READ_PATTERNS:
            if re.search(pattern, upper):
                return SQLCategory.READ

        for pattern in cls.TRANSACTION_PATTERNS:
            if re.search(pattern, upper):
                return SQLCategory.TRANSACTION

        return SQLCategory.OTHER

    @classmethod
    def extract_target_app(cls, command: str, registry_apps: list) -> str | None:
        """Extract which app a database command targets."""
        for app in registry_apps:
            conn = app["connection"]
            # Check for port or database name in command
            if str(conn["port"]) in command or conn["database"] in command:
                return app["id"]
        return None


class MeasurementCollector:
    """Collect and summarize experiment measurements."""

    def __init__(self):
        self.measurements: list[Measurement] = []
        self.total_input_tokens: int = 0
        self.total_output_tokens: int = 0
        self.start_time: float = time.time()
        self._first_discovery_time: float | None = None
        self._first_operational_time: float | None = None

    def record_bash(self, command: str, duration_ms: float, success: bool):
        """Record a bash command execution."""
        sql_cat = SQLClassifier.classify(command)

        # Track schema discovery timing
        now = time.time()
        if sql_cat == SQLCategory.SCHEMA_DISCOVERY and self._first_discovery_time is None:
            self._first_discovery_time = now
        if sql_cat in (SQLCategory.READ, SQLCategory.WRITE) and self._first_operational_time is None:
            self._first_operational_time = now

        m = Measurement(
            timestamp=now,
            category="bash",
            command=command,
            duration_ms=duration_ms,
            success=success,
            sql_category=sql_cat.value if sql_cat != SQLCategory.OTHER else None,
        )
        self.measurements.append(m)

    def record_tokens(self, input_tokens: int, output_tokens: int):
        """Record token usage from an API call."""
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens

    def summarize(self) -> dict:
        """Generate a summary of all measurements."""
        # SQL operation counts
        sql_ops = {
            "schema_discovery": 0,
            "read": 0,
            "write": 0,
            "transaction": 0,
            "failed": 0,
        }
        total_bash_ms = 0.0
        total_llm_ms = 0.0

        for m in self.measurements:
            if m.category == "bash":
                total_bash_ms += m.duration_ms
                if m.sql_category:
                    if not m.success:
                        sql_ops["failed"] += 1
                    elif m.sql_category in sql_ops:
                        sql_ops[m.sql_category] += 1

        # Schema discovery time
        schema_discovery_ms = None
        if self._first_discovery_time and self._first_operational_time:
            schema_discovery_ms = (
                self._first_operational_time - self._first_discovery_time
            ) * 1000

        return {
            "sql_ops": sql_ops,
            "total_sql_ops": sum(sql_ops.values()),
            "total_tokens": {
                "input": self.total_input_tokens,
                "output": self.total_output_tokens,
                "total": self.total_input_tokens + self.total_output_tokens,
            },
            "timing": {
                "total_bash_ms": round(total_bash_ms, 1),
                "schema_discovery_ms": round(schema_discovery_ms, 1) if schema_discovery_ms else None,
            },
            "total_bash_commands": len(
                [m for m in self.measurements if m.category == "bash"]
            ),
            "success_rate": (
                sum(1 for m in self.measurements if m.success)
                / max(len(self.measurements), 1)
            ),
        }
