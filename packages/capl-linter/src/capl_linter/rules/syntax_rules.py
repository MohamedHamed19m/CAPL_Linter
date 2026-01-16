import sqlite3
from pathlib import Path
from typing import List
from .base import BaseRule
from ..models import InternalIssue
from capl_symbol_db.database import SymbolDatabase


class ForbiddenSyntaxRule(BaseRule):
    @property
    def rule_id(self) -> str:
        return "forbidden-syntax"

    def check(self, file_path: Path, db: SymbolDatabase) -> List[InternalIssue]:
        issues = []
        file_path_abs = str(file_path.resolve())

        conn = sqlite3.connect(db.db_path)
        try:
            cursor = conn.execute(
                """
                SELECT s.symbol_name, s.line_number, s.context
                FROM symbols s
                JOIN files f ON s.file_id = f.file_id
                WHERE f.file_path = ? AND s.symbol_type = 'forbidden_syntax'
            """,
                (file_path_abs,),
            )

            for name, line, context in cursor.fetchall():
                rule_id = (
                    "function-declaration"
                    if context == "function_declaration"
                    else "extern-keyword"
                )
                msg = f"Forbidden syntax: {context.replace('_', ' ')}"

                issues.append(
                    InternalIssue(
                        file_path=file_path,
                        line=line,
                        rule_id=rule_id,
                        message=msg,
                        severity="error",
                        auto_fixable=True,
                        context=context,
                    )
                )
        finally:
            conn.close()

        return issues


class GlobalTypeDefinitionRule(BaseRule):
    @property
    def rule_id(self) -> str:
        return "global-type-definition"

    def check(self, file_path: Path, db: SymbolDatabase) -> List[InternalIssue]:
        issues = []
        file_path_abs = str(file_path.resolve())

        conn = sqlite3.connect(db.db_path)
        try:
            # We look for symbols that are enums/structs defined at global scope
            # In our current extractor, these are stored in 'symbols' table with context 'enum_definition' or 'struct_definition'
            # and scope 'global'.
            # Note: We might want to use a dedicated 'type_definitions' table later as in old code.
            cursor = conn.execute(
                """
                SELECT s.symbol_name, s.line_number, s.context
                FROM symbols s
                JOIN files f ON s.file_id = f.file_id
                WHERE f.file_path = ? 
                  AND s.scope = 'global'
                  AND s.context IN ('enum_definition', 'struct_definition')
            """,
                (file_path_abs,),
            )

            for name, line, context in cursor.fetchall():
                type_kind = "enum" if context == "enum_definition" else "struct"
                issues.append(
                    InternalIssue(
                        file_path=file_path,
                        line=line,
                        rule_id=f"global-{type_kind}-definition",
                        message=f"{type_kind.capitalize()} '{name}' defined outside 'variables {{}}' block",
                        severity="error",
                        auto_fixable=True,
                        context=context,
                    )
                )
        finally:
            conn.close()

        return issues
