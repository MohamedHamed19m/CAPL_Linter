"""
CAPL Cross-Reference Builder using Tree-sitter
Tracks where symbols are used and builds a call graph in aic.db
"""

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import tree_sitter_c as tsc
from tree_sitter import Language, Node, Parser, Query, QueryCursor


@dataclass
class SymbolReference:
    """Represents a usage of a symbol in CAPL code"""

    symbol_name: str
    file_path: str
    line_number: int
    column: int
    reference_type: str  # 'call', 'usage', 'assignment', 'output'
    context: str | None = None  # Function name where the reference occurs


class CAPLCrossReferenceBuilder:
    def __init__(self, db_path: str = "aic.db"):
        self.db_path = db_path
        self.language = Language(tsc.language())
        self.parser = Parser(self.language)
        self._init_database()

    def _init_database(self):
        """Create tables for cross-reference tracking"""
        conn = sqlite3.connect(self.db_path)
        try:
            with conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS symbol_references (
                        ref_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        file_id INTEGER NOT NULL,
                        symbol_name TEXT NOT NULL,
                        line_number INTEGER,
                        column_number INTEGER,
                        reference_type TEXT,
                        context TEXT,
                        FOREIGN KEY (file_id) REFERENCES files(file_id)
                    )
                """)

                conn.execute("""
                    CREATE TABLE IF NOT EXISTS message_usage (
                        usage_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        file_id INTEGER NOT NULL,
                        message_name TEXT NOT NULL,
                        usage_type TEXT, -- 'output', 'on message'
                        line_number INTEGER,
                        FOREIGN KEY (file_id) REFERENCES files(file_id)
                    )
                """)

                # Index for fast search
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_refs_name 
                    ON symbol_references(symbol_name)
                """)
        finally:
            conn.close()

    def analyze_file_references(self, file_path: str) -> int:
        """
        Scan a file for symbol usages and store them in the DB
        """
        file_path = str(Path(file_path).resolve())

        with open(file_path, "rb") as f:
            source_code = f.read()

        tree = self.parser.parse(source_code)
        root = tree.root_node
        source_text = source_code.decode("utf8")

        references = []
        references.extend(self._extract_function_calls(root, source_text, file_path))
        references.extend(self._extract_variable_usages(root, source_text, file_path))
        message_usages = self._extract_message_usages(root, source_text, file_path)

        # Store in database
        conn = sqlite3.connect(self.db_path)
        try:
            with conn:
                # Get file_id
                cursor = conn.execute(
                    "SELECT file_id FROM files WHERE file_path = ?", (file_path,)
                )
                result = cursor.fetchone()
                if not result:
                    # Register file if not exists
                    cursor = conn.execute(
                        "INSERT INTO files (file_path, parse_success) VALUES (?, 1) RETURNING file_id",
                        (file_path,),
                    )
                    file_id = cursor.fetchone()[0]
                else:
                    file_id = result[0]

                # Clear old references
                conn.execute("DELETE FROM symbol_references WHERE file_id = ?", (file_id,))
                conn.execute("DELETE FROM message_usage WHERE file_id = ?", (file_id,))

                # Store new ones
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

                for msg in message_usages:
                    conn.execute(
                        """
                        INSERT INTO message_usage (file_id, message_name, usage_type, line_number)
                        VALUES (?, ?, ?, ?)
                    """,
                        (file_id, msg["name"], msg["type"], msg["line"]),
                    )
        finally:
            conn.close()

        return len(references)

    def _extract_function_calls(self, root: Node, source: str, file_path: str) -> list[SymbolReference]:
        """Find all function calls: name(args)"""
        refs = []
        query = Query(
            self.language,
            """
            (call_expression
              function: (identifier) @func_name) @call
        """,
        )
        cursor = QueryCursor(query)
        cursor.set_byte_range(0, len(source.encode("utf8")))
        matches = cursor.matches(root)

        for pattern_index, captures_dict in matches:
            if "func_name" in captures_dict:
                for node in captures_dict["func_name"]:
                    func_name = source[node.start_byte : node.end_byte]
                    line = node.start_point[0] + 1
                    col = node.start_point[1]
                    context = self._get_enclosing_function(node, source)

                    refs.append(
                        SymbolReference(
                            symbol_name=func_name,
                            file_path=file_path,
                            line_number=line,
                            column=col,
                            reference_type="call",
                            context=context,
                        )
                    )
        return refs

    def _extract_variable_usages(self, root: Node, source: str, file_path: str) -> list[SymbolReference]:
        """Find variable usages in expressions"""
        refs = []
        # Query for identifiers not part of a declaration or function name
        query = Query(
            self.language,
            """
            (identifier) @id
        """,
        )
        cursor = QueryCursor(query)
        cursor.set_byte_range(0, len(source.encode("utf8")))
        matches = cursor.matches(root)

        for pattern_index, captures_dict in matches:
            for node in captures_dict["id"]:
                if self._is_actual_usage(node):
                    name = source[node.start_byte : node.end_byte]
                    line = node.start_point[0] + 1
                    col = node.start_point[1]
                    context = self._get_enclosing_function(node, source)

                    # Determine if it's an assignment
                    ref_type = "usage"
                    if node.parent and node.parent.type == "assignment_expression":
                        # Check if it's the left side
                        left_node = node.parent.child_by_field_name("left")
                        if left_node == node:
                            ref_type = "assignment"

                    refs.append(
                        SymbolReference(
                            symbol_name=name,
                            file_path=file_path,
                            line_number=line,
                            column=col,
                            reference_type=ref_type,
                            context=context,
                        )
                    )
        return refs

    def _is_actual_usage(self, node: Node) -> bool:
        """Filter out declarations, function names, etc."""
        p = node.parent
        if not p:
            return False

        # Ignore if part of a declaration
        if p.type in ("declaration", "init_declarator", "parameter_declaration", "field_declaration"):
            return False

        # Ignore if it's the name of a function being defined
        if p.type == "function_declarator":
            return False

        # Ignore if it's a member access (the part after the dot)
        if p.type == "field_expression":
            field_node = p.child_by_field_name("field")
            if field_node == node:
                return False

        return True

    def _extract_message_usages(self, root: Node, source: str, file_path: str) -> list[dict]:
        """Find 'output(msg)' calls and 'on message' handlers"""
        usages = []

        # 1. Find output(msg)
        query_out = Query(
            self.language,
            """
            (call_expression
              function: (identifier) @func
              arguments: (argument_list (identifier) @msg_name))
        """,
        )
        cursor = QueryCursor(query_out)
        cursor.set_byte_range(0, len(source.encode("utf8")))
        for pattern_index, captures_dict in cursor.matches(root):
            if "func" in captures_dict and "msg_name" in captures_dict:
                func_node = captures_dict["func"][0]
                if source[func_node.start_byte : func_node.end_byte] == "output":
                    msg_node = captures_dict["msg_name"][0]
                    usages.append(
                        {
                            "name": source[msg_node.start_byte : msg_node.end_byte],
                            "type": "output",
                            "line": msg_node.start_point[0] + 1,
                        }
                    )

        # 2. Find 'on message' handlers (already extracted as symbols, but good to have here too)
        # For simplicity, we assume linter will check both tables if needed.

        return usages

    def _get_enclosing_function(self, node: Node, source: str) -> str | None:
        """Find the name of the function containing this node"""
        curr = node
        while curr:
            if curr.type == "function_definition":
                # Find function name in declarator
                decl = curr.child_by_field_name("declarator")
                if decl:
                    # Support both normal functions and 'on message' style
                    if decl.type == "function_declarator":
                        name_node = decl.child_by_field_name("declarator")
                        if name_node:
                            return source[name_node.start_byte : name_node.end_byte]
                # Fallback to first line
                return source[curr.start_byte : curr.end_byte].split("{")[0].strip()
            curr = curr.parent
        return None

    def find_all_references(self, symbol_name: str) -> list[SymbolReference]:
        """Find all usages of a symbol across the entire project"""
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.execute(
                """
                SELECT f.file_path, r.line_number, r.column_number, r.reference_type, r.context
                FROM symbol_references r
                JOIN files f ON r.file_id = f.file_id
                WHERE r.symbol_name = ?
                ORDER BY f.file_path, r.line_number
            """,
                (symbol_name,),
            )

            results = []
            for file_path, line, col, ref_type, context in cursor.fetchall():
                results.append(
                    SymbolReference(
                        symbol_name=symbol_name,
                        file_path=file_path,
                        line_number=line,
                        column=col,
                        reference_type=ref_type,
                        context=context,
                    )
                )
            return results
        finally:
            conn.close()

    def get_call_graph(self, func_name: str) -> dict:
        """Find who calls this function and what this function calls"""
        conn = sqlite3.connect(self.db_path)
        try:
            # Who calls func_name?
            cursor = conn.execute(
                """
                SELECT DISTINCT context, f.file_path 
                FROM symbol_references r
                JOIN files f ON r.file_id = f.file_id
                WHERE symbol_name = ? AND reference_type = 'call' AND context IS NOT NULL
            """,
                (func_name,),
            )
            callers = cursor.fetchall()

            # What does func_name call?
            cursor = conn.execute(
                """
                SELECT DISTINCT symbol_name, f.file_path
                FROM symbol_references r
                JOIN files f ON r.file_id = f.file_id
                WHERE context = ? AND reference_type = 'call'
            """,
                (func_name,),
            )
            callees = cursor.fetchall()

            return {
                "name": func_name,
                "callers": [{"name": c[0], "file": c[1]} for c in callers],
                "callees": [{"name": c[0], "file": c[1]} for c in callees],
            }
        finally:
            conn.close()