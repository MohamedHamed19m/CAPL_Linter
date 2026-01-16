import sqlite3
from pathlib import Path

from capl_symbol_db.database import SymbolDatabase

from ..models import InternalIssue
from .base import BaseRule


class VariablePlacementRule(BaseRule):
    @property
    def rule_id(self) -> str:
        return "variable-placement"

    def check(self, file_path: Path, db: SymbolDatabase) -> list[InternalIssue]:
        issues = []
        file_path_abs = str(file_path.resolve())

        conn = sqlite3.connect(db.db_path)
        try:
            # 1. Check for variables outside variables block
            cursor = conn.execute(
                """
                SELECT s.symbol_name, s.line_number
                FROM symbols s
                JOIN files f ON s.file_id = f.file_id
                WHERE f.file_path = ? 
                  AND s.symbol_type = 'variable'
                  AND s.scope = 'global'
            """,
                (file_path_abs,),
            )

            for name, line in cursor.fetchall():
                issues.append(
                    InternalIssue(
                        file_path=file_path,
                        line=line,
                        rule_id="variable-outside-block",
                        message=f"Variable '{name}' declared outside 'variables {{}}' block",
                        severity="error",
                        auto_fixable=True,
                    )
                )

            # 2. Check for mid-block declarations
            cursor = conn.execute(
                """
                SELECT s.symbol_name, s.line_number, s.parent_symbol
                FROM symbols s
                JOIN files f ON s.file_id = f.file_id
                WHERE f.file_path = ? 
                  AND s.symbol_type = 'variable'
                  AND s.scope = 'local'
                  AND s.declaration_position = 'mid_block'
            """,
                (file_path_abs,),
            )

            for name, line, parent in cursor.fetchall():
                issues.append(
                    InternalIssue(
                        file_path=file_path,
                        line=line,
                        rule_id="variable-mid-block",
                        message=f"Variable '{name}' declared after executable statements in '{parent}'",
                        severity="error",
                        auto_fixable=True,
                        context=parent,
                    )
                )
        finally:
            conn.close()

        return issues
