"""
Safety guardrails for the experiment agent.

Prevents destructive operations (DROP, TRUNCATE, DELETE without WHERE)
and enforces transaction boundaries.
"""

import re


class SafetyViolation(Exception):
    """Raised when a command violates safety rules."""
    pass


class SafetyGuard:
    """Check bash commands for dangerous operations."""

    # Commands that are always blocked
    BLOCKED_PATTERNS = [
        # DDL operations
        (r"\bDROP\s+(TABLE|DATABASE|SCHEMA|INDEX|VIEW|SEQUENCE|FUNCTION)\b",
         "DROP operations are not allowed"),
        (r"\bTRUNCATE\b",
         "TRUNCATE is not allowed"),
        (r"\bALTER\s+TABLE\b.*\bDROP\b",
         "ALTER TABLE DROP is not allowed"),
        (r"\bCREATE\s+(TABLE|DATABASE|SCHEMA)\b",
         "DDL CREATE operations are not allowed"),

        # Dangerous DML
        (r"\bDELETE\s+FROM\s+\w+\s*;",
         "DELETE without WHERE clause is not allowed"),
        (r"\bDELETE\s+FROM\s+\w+\s*$",
         "DELETE without WHERE clause is not allowed"),
        (r"\bUPDATE\s+\w+\s+SET\b(?!.*\bWHERE\b)",
         "UPDATE without WHERE clause is not allowed"),

        # System-level dangerous commands
        (r"\brm\s+-rf\s+/",
         "Recursive deletion of root paths is not allowed"),
        (r"\bshutdown\b",
         "System shutdown is not allowed"),
        (r"\breboot\b",
         "System reboot is not allowed"),
        (r"\bkill\s+-9\b",
         "Force kill is not allowed"),
        (r"\bdocker\s+(rm|stop|kill|down)",
         "Docker container management is not allowed during experiment"),
    ]

    # Patterns that trigger a warning but are allowed
    WARNING_PATTERNS = [
        (r"\bDELETE\b",
         "DELETE operation detected - ensure WHERE clause is specific"),
        (r"\bUPDATE\b.*\bWHERE\s+1\s*=\s*1",
         "UPDATE with always-true WHERE clause is dangerous"),
    ]

    def check(self, command: str) -> list[str]:
        """
        Check a command for safety violations.

        Args:
            command: The bash command to check

        Returns:
            List of warning messages (may be empty)

        Raises:
            SafetyViolation: If the command is blocked
        """
        warnings = []

        # Check blocked patterns
        for pattern, message in self.BLOCKED_PATTERNS:
            if re.search(pattern, command, re.IGNORECASE | re.DOTALL):
                raise SafetyViolation(message)

        # Check warning patterns
        for pattern, message in self.WARNING_PATTERNS:
            if re.search(pattern, command, re.IGNORECASE | re.DOTALL):
                warnings.append(message)

        return warnings

    @staticmethod
    def wrap_in_transaction(sql: str) -> str:
        """Wrap a SQL statement in a transaction if it's a write operation."""
        write_patterns = [r"\bINSERT\b", r"\bUPDATE\b", r"\bDELETE\b"]
        for pattern in write_patterns:
            if re.search(pattern, sql, re.IGNORECASE):
                return f"BEGIN;\n{sql}\nCOMMIT;"
        return sql
