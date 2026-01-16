import sqlite3
from pathlib import Path
from typing import List, Optional, Dict
from capl_tree_sitter.parser import CAPLParser
from capl_tree_sitter.queries import CAPLQueryHelper
from capl_tree_sitter.ast_walker import ASTWalker
from .database import SymbolDatabase
from dataclasses import dataclass


@dataclass
class SymbolReference:
    """Represents a usage of a symbol in CAPL code"""

    symbol_name: str
    file_path: str
    line_number: int
    column: int
    reference_type: str  # 'call', 'usage', 'assignment', 'output'
    context: Optional[str] = None


class CrossReferenceBuilder:
    """Tracks symbol usages and builds a call graph"""

    def __init__(self, db: SymbolDatabase):
        self.db = db
        self.parser = CAPLParser()
        self.query_helper = CAPLQueryHelper()

    def analyze_file_references(self, file_path: Path) -> int:
        """Scan a file for symbol usages and store them in the DB"""
        file_path_abs = file_path.resolve()

        result = self.parser.parse_file(file_path_abs)
        root = result.tree.root_node
        source = result.source

        # Register/get file_id
        with open(file_path_abs, "rb") as f:
            file_id = self.db.store_file(file_path_abs, f.read())

        references = []
        references.extend(self._extract_function_calls(root, source, str(file_path_abs)))
        references.extend(self._extract_variable_usages(root, source, str(file_path_abs)))

        # Store in database
        conn = sqlite3.connect(self.db.db_path)
        try:
            with conn:
                conn.execute("DELETE FROM symbol_references WHERE file_id = ?", (file_id,))

                for ref in references:
                    conn.execute(
                        """
                        INSERT INTO symbol_references 
                        (file_id, symbol_name, line_number, column_number, reference_type, context)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """,
                        (
                            file_id,
                            ref.symbol_name,
                            ref.line_number,
                            ref.column,
                            ref.reference_type,
                            ref.context,
                        ),
                    )
        finally:
            conn.close()

        return len(references)

    def _extract_function_calls(self, root, source, file_path) -> List[SymbolReference]:
        refs = []
        query = "(call_expression function: (identifier) @func_name) @call"
        matches = self.query_helper.query(query, root)

        for m in matches:
            if "func_name" in m.captures:
                node = m.captures["func_name"]
                name = source[node.start_byte : node.end_byte]
                refs.append(
                    SymbolReference(
                        symbol_name=name,
                        file_path=file_path,
                        line_number=node.start_point[0] + 1,
                        column=node.start_point[1],
                        reference_type="call",
                        context=self._get_enclosing_function(node, source),
                    )
                )
        return refs

    def _extract_variable_usages(self, root, source, file_path) -> List[SymbolReference]:
        refs = []
        query = "(identifier) @id"
        matches = self.query_helper.query(query, root)

        for m in matches:
            node = m.captures["id"]
            if self._is_actual_usage(node):
                name = source[node.start_byte : node.end_byte]

                # Determine type
                ref_type = "usage"
                parent = node.parent
                if parent and parent.type == "assignment_expression":
                    if parent.child_by_field_name("left") == node:
                        ref_type = "assignment"

                refs.append(
                    SymbolReference(
                        symbol_name=name,
                        file_path=file_path,
                        line_number=node.start_point[0] + 1,
                        column=node.start_point[1],
                        reference_type=ref_type,
                        context=self._get_enclosing_function(node, source),
                    )
                )
        return refs

    def _is_actual_usage(self, node) -> bool:
        p = node.parent
        if not p:
            return False
        if p.type in (
            "declaration",
            "init_declarator",
            "parameter_declaration",
            "field_declaration",
        ):
            return False
        if p.type == "function_declarator":
            return False
        return True

    def _get_enclosing_function(self, node, source) -> Optional[str]:
        func_node = ASTWalker.find_parent_of_type(node, "function_definition")
        if func_node:
            # Fallback for now: use first line
            return source[func_node.start_byte : func_node.end_byte].split("{")[0].strip()
        return None
