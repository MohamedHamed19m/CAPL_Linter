import sqlite3
from pathlib import Path

from capl_symbol_db.database import SymbolDatabase

from ..builtins import CAPL_BUILTINS
from ..models import InternalIssue, Severity
from .base import BaseRule


class UndefinedSymbolRule(BaseRule):
    """E011: Detect undefined symbols (variables/functions)"""

    rule_id = "E011"
    name = "undefined-symbol"
    severity = Severity.ERROR
    description = "Symbol is not defined in the current file or its transitive includes."

    def __init__(self):
        self.custom_builtins: list[str] = []

    def check(self, file_path: Path, db: SymbolDatabase) -> list[InternalIssue]:
        issues = []
        visible = db.get_visible_symbols(file_path)

        # Create sets for fast lookup
        known_symbols = set(CAPL_BUILTINS)
        known_symbols.update(self.custom_builtins)
        for s_list in visible.values():
            for s in s_list:
                known_symbols.add(s["symbol_name"])

        # Query all references in the current file
        conn = sqlite3.connect(db.db_path)
        conn.row_factory = sqlite3.Row
        try:
            cursor = conn.execute(
                """
                SELECT symbol_name, line_number, column_number, reference_type
                FROM symbol_references
                WHERE file_id = (SELECT file_id FROM files WHERE file_path = ?)
                """,
                (str(file_path.resolve()),),
            )

            for ref in cursor.fetchall():
                name = ref["symbol_name"]
                if name not in known_symbols:
                    # Ignore some special cases or built-ins that might be missing from our list
                    if name.startswith("on"):
                        continue

                    issues.append(
                        self._create_issue(
                            file_path=file_path,
                            line=ref["line_number"],
                            column=ref["column_number"],
                            message=f"Undefined symbol '{name}'",
                        )
                    )
        finally:
            conn.close()

        return issues


class DuplicateFunctionRule(BaseRule):
    """E012: Detect duplicate function definitions (across project)"""

    rule_id = "E012"
    name = "duplicate-function"
    severity = Severity.ERROR
    description = "Multiple definitions of the same function with the same parameter count."

    def check(self, file_path: Path, db: SymbolDatabase) -> list[InternalIssue]:
        issues = []
        conn = sqlite3.connect(db.db_path)
        conn.row_factory = sqlite3.Row
        try:
            # Query functions in this file
            cursor = conn.execute(
                """
                SELECT s.symbol_name, s.param_count, s.line_number
                FROM symbols s
                JOIN files f ON s.file_id = f.file_id
                WHERE f.file_path = ? AND s.symbol_type = 'function'
                """,
                (str(file_path.resolve()),),
            )
            local_funcs = cursor.fetchall()

            for func in local_funcs:
                name = func["symbol_name"]
                p_count = func["param_count"]

                # Check if this name/p_count exists elsewhere
                # (We use param_count to allow overloading if CAPL supports it,
                # or at least to be more specific)
                check_cursor = conn.execute(
                    """
                    SELECT f.file_path, s.line_number
                    FROM symbols s
                    JOIN files f ON s.file_id = f.file_id
                    WHERE s.symbol_name = ? 
                      AND s.param_count = ?
                      AND s.symbol_type = 'function'
                      AND (f.file_path != ? OR s.line_number != ?)
                    """,
                    (name, p_count, str(file_path.resolve()), func["line_number"]),
                )
                duplicates = check_cursor.fetchall()

                if duplicates:
                    dup_locs = [
                        f"{Path(d['file_path']).name}:{d['line_number']}" for d in duplicates
                    ]
                    issues.append(
                        self._create_issue(
                            file_path=file_path,
                            line=func["line_number"],
                            message=f"Duplicate function definition '{name}' (also in: {', '.join(dup_locs)})",
                        )
                    )
        finally:
            conn.close()

        return issues


class CircularIncludeRule(BaseRule):
    """W001: Detect circular include dependencies"""

    rule_id = "W001"
    name = "circular-include"
    severity = Severity.WARNING
    description = "Circular dependency detected. While allowed in CAPL, this suggests poor file structure."

    def check(self, file_path: Path, db: SymbolDatabase) -> list[InternalIssue]:
        issues = []
        cycles = db.detect_circular_includes(file_path)

        for cycle in cycles:
            # Format the cycle for the message
            cycle_names = [Path(p).name for p in cycle]
            issues.append(
                self._create_issue(
                    file_path=file_path,
                    line=1,  # Usually reported at top of file
                    message=f"Circular include detected: {' -> '.join(cycle_names)}. Consider refactoring to avoid cycles.",
                )
            )

        return issues
