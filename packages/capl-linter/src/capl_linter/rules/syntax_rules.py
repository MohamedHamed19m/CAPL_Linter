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
            cursor = conn.execute("""
                SELECT s.symbol_name, s.line_number, s.context
                FROM symbols s
                JOIN files f ON s.file_id = f.file_id
                WHERE f.file_path = ? AND s.symbol_type = 'forbidden_syntax'
            """, (file_path_abs,))
            
            for name, line, context in cursor.fetchall():
                rule_id = "function-declaration" if context == "function_declaration" else "extern-keyword"
                msg = f"Forbidden syntax: {context.replace('_', ' ')}"
                
                issues.append(InternalIssue(
                    file_path=file_path,
                    line=line,
                    rule_id=rule_id,
                    message=msg,
                    severity="error",
                    auto_fixable=True,
                    context=context
                ))
        finally:
            conn.close()
            
        return issues
