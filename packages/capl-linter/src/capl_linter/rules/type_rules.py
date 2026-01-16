import sqlite3
from pathlib import Path

from capl_symbol_db.database import SymbolDatabase

from ..models import InternalIssue
from .base import BaseRule


class TypeUsageRule(BaseRule):
    @property
    def rule_id(self) -> str:
        return "type-usage"

    def check(self, file_path: Path, db: SymbolDatabase) -> list[InternalIssue]:
        issues = []
        file_path_abs = str(file_path.resolve())

        conn = sqlite3.connect(db.db_path)
        try:
            cursor = conn.execute(
                """
                SELECT s.symbol_name, s.line_number, s.signature, s.context
                FROM symbols s
                JOIN files f ON s.file_id = f.file_id
                WHERE f.file_path = ? AND s.symbol_type = 'type_usage_error'
            """,
                (file_path_abs,),
            )

            for var_name, line, sig, context in cursor.fetchall():
                type_kind = context.replace("missing_", "").replace("_keyword", "")
                type_name = sig.split()[0]  # Heuristic

                issues.append(
                    InternalIssue(
                        file_path=file_path,
                        line=line,
                        rule_id=f"missing-{type_kind}-keyword",
                        message=f"Type '{type_name}' used without '{type_kind}' keyword in declaration of '{var_name}'",
                        severity="error",
                        auto_fixable=True,
                        context=context,
                    )
                )
        finally:
            conn.close()

        return issues
