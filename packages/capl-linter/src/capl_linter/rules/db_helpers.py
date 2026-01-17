"""Database query helpers to reduce SQL duplication in rules."""

import sqlite3
from pathlib import Path
from typing import Any

from capl_symbol_db.database import SymbolDatabase


class RuleQueryHelper:
    """Helper class to run common database queries."""

    def __init__(self, db: SymbolDatabase, file_path: Path):
        self.db = db
        self.file_path_abs = str(file_path.resolve())

    def query_symbols(
        self,
        symbol_type: str | None = None,
        scope: str | None = None,
        context: str | None = None,
        contexts: list[str] | None = None,
    ) -> list[tuple[Any, ...]]:
        """Query symbols with flexible filtering.

        Returns list of tuples: (symbol_name, line_number, context, ...)
        """
        conn = sqlite3.connect(self.db.db_path)

        try:
            conditions = ["f.file_path = ?"]
            params = [self.file_path_abs]

            if symbol_type:
                conditions.append("s.symbol_type = ?")
                params.append(symbol_type)

            if scope:
                conditions.append("s.scope = ?")
                params.append(scope)

            if context:
                conditions.append("s.context = ?")
                params.append(context)

            if contexts:
                placeholders = ",".join("?" * len(contexts))
                conditions.append(f"s.context IN ({placeholders})")
                params.extend(contexts)

            where_clause = " AND ".join(conditions)

            query = f"""
                SELECT s.symbol_name, s.line_number, s.context,
                       s.signature, s.parent_symbol, s.declaration_position
                FROM symbols s
                JOIN files f ON s.file_id = f.file_id
                WHERE {where_clause}
            """

            cursor = conn.execute(query, params)
            return cursor.fetchall()

        finally:
            conn.close()

    def get_forbidden_syntax(self) -> list[tuple[str, int, str]]:
        """Get all forbidden syntax items (extern, function declarations)."""
        results = self.query_symbols(symbol_type="forbidden_syntax")
        return [(name, line, ctx) for name, line, ctx, _, _, _ in results]

    def get_type_usage_errors(self) -> list[tuple[str, int, str, str]]:
        """Get variables missing enum/struct keywords."""
        results = self.query_symbols(symbol_type="type_usage_error")
        return [(name, line, ctx, sig) for name, line, ctx, sig, _, _ in results]

    def get_global_variables(self) -> list[tuple[str, int]]:
        """Get variables declared outside variables{} block."""
        results = self.query_symbols(symbol_type="variable", scope="global")
        return [(name, line) for name, line, _, _, _, _ in results]

    def get_mid_block_variables(self) -> list[tuple[str, int, str]]:
        """Get local variables declared after statements."""
        conn = sqlite3.connect(self.db.db_path)
        try:
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
                (self.file_path_abs,),
            )
            return cursor.fetchall()
        finally:
            conn.close()
