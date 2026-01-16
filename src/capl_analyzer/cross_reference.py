"""
CAPL Cross-Reference System
Tracks where symbols are used, builds call graphs, and enables "find all references"
"""

import sqlite3
from dataclasses import dataclass
from pathlib import Path

import tree_sitter_c as tsc
from tree_sitter import Language, Node, Parser, Query, QueryCursor


@dataclass
class Reference:
    """A reference to a symbol"""

    file_path: str
    line_number: int
    column: int
    context: str  # The line of code containing the reference
    reference_type: str  # 'call', 'usage', 'output', 'assignment'


class CAPLCrossReferenceBuilder:
    """Build cross-reference database for CAPL symbols"""

    def __init__(self, db_path: str = "aic.db"):
        self.db_path = db_path
        self.language = Language(tsc.language())
        self.parser = Parser(self.language)
        self._init_database()

    def _init_database(self):
        """Create cross-reference tables"""
        with sqlite3.connect(self.db_path) as conn:
            # Table for files (referenced by other tables)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS files (
                    file_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_path TEXT UNIQUE NOT NULL,
                    last_parsed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    parse_success BOOLEAN,
                    file_hash TEXT
                )
            """)

            # Table for symbol references
            conn.execute("""
                CREATE TABLE IF NOT EXISTS symbol_references (
                    ref_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol_name TEXT NOT NULL,
                    file_id INTEGER NOT NULL,
                    line_number INTEGER NOT NULL,
                    column_number INTEGER,
                    reference_type TEXT,  -- 'call', 'usage', 'output', 'assignment'
                    context TEXT,  -- Line of code containing the reference
                    FOREIGN KEY (file_id) REFERENCES files(file_id)
                )
            """)

            # Table for function calls (call graph)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS function_calls (
                    call_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    caller_symbol_id INTEGER NOT NULL,
                    callee_name TEXT NOT NULL,
                    file_id INTEGER NOT NULL,
                    line_number INTEGER NOT NULL,
                    FOREIGN KEY (caller_symbol_id) REFERENCES symbols(symbol_id),
                    FOREIGN KEY (file_id) REFERENCES files(file_id)
                )
            """)

            # Table for message usage (CAPL-specific)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS message_usage (
                    usage_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    message_name TEXT NOT NULL,
                    usage_type TEXT NOT NULL,  -- 'handler', 'output', 'reference'
                    symbol_id INTEGER,  -- Which function/handler uses it
                    file_id INTEGER NOT NULL,
                    line_number INTEGER NOT NULL,
                    FOREIGN KEY (symbol_id) REFERENCES symbols(symbol_id),
                    FOREIGN KEY (file_id) REFERENCES files(file_id)
                )
            """)

            # Indexes for fast lookups
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_symbol_refs_name 
                ON symbol_references(symbol_name)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_symbol_refs_file 
                ON symbol_references(file_id)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_function_calls_caller
                ON function_calls(caller_symbol_id)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_function_calls_callee
                ON function_calls(callee_name)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_message_usage_name
                ON message_usage(message_name)
            """)

            conn.commit()

    def analyze_file_references(self, file_path: str) -> int:
        """
        Analyze a file and extract all symbol references

        Returns:
            Number of references found
        """
        file_path = str(Path(file_path).resolve())

        with open(file_path, "rb") as f:
            source_code = f.read()

        source_text = source_code.decode("utf8")
        tree = self.parser.parse(source_code)
        root = tree.root_node

        with sqlite3.connect(self.db_path) as conn:
            # Get or create file_id
            cursor = conn.execute(
                """
                INSERT INTO files (file_path, parse_success)
                VALUES (?, 1)
                ON CONFLICT(file_path) DO UPDATE SET
                    last_parsed = CURRENT_TIMESTAMP
                RETURNING file_id
            """,
                (file_path,),
            )

            file_id = cursor.fetchone()[0]

            # Clear old references for this file
            conn.execute("DELETE FROM symbol_references WHERE file_id = ?", (file_id,))
            conn.execute("DELETE FROM function_calls WHERE file_id = ?", (file_id,))
            conn.execute("DELETE FROM message_usage WHERE file_id = ?", (file_id,))

            # Extract different types of references
            refs_count = 0

            # 1. Function calls
            refs_count += self._extract_function_calls(root, source_text, file_id, conn)

            # 2. Variable usages
            refs_count += self._extract_variable_references(root, source_text, file_id, conn)

            # 3. CAPL-specific: output() calls with messages
            refs_count += self._extract_message_output(root, source_text, file_id, conn)

            # 4. CAPL-specific: setTimer() calls
            refs_count += self._extract_timer_usage(root, source_text, file_id, conn)

            conn.commit()

        return refs_count

    def _extract_function_calls(self, root: Node, source: str, file_id: int, conn) -> int:
        """Extract all function call expressions"""
        count = 0

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
                for func_node in captures_dict["func_name"]:
                    func_name = source[func_node.start_byte : func_node.end_byte]
                    line_num = func_node.start_point[0] + 1
                    col_num = func_node.start_point[1]

                    # Get context (the line of code)
                    lines = source.split("\n")
                    context = lines[line_num - 1].strip() if line_num <= len(lines) else ""

                    # Store reference
                    conn.execute(
                        """
                        INSERT INTO symbol_references
                        (symbol_name, file_id, line_number, column_number, 
                         reference_type, context)
                        VALUES (?, ?, ?, ?, 'call', ?)
                    """,
                        (func_name, file_id, line_num, col_num, context),
                    )

                    # Also store in function_calls table for call graph
                    # Find which function this call is inside
                    caller_id = self._find_containing_function(func_node, source, file_id, conn)
                    if caller_id:
                        conn.execute(
                            """
                            INSERT INTO function_calls
                            (caller_symbol_id, callee_name, file_id, line_number)
                            VALUES (?, ?, ?, ?)
                        """,
                            (caller_id, func_name, file_id, line_num),
                        )

                    count += 1

        return count

    def _find_containing_function(self, node: Node, source: str, file_id: int, conn) -> int | None:
        """Find the function/event handler that contains this node"""
        # Walk up the tree to find a function_definition
        parent = node.parent
        while parent:
            if parent.type == "function_definition":
                # Get the function name
                func_text = source[parent.start_byte : parent.end_byte]
                first_line = func_text.split("\n")[0].strip()

                # Extract function/event handler name
                if first_line.startswith("on "):
                    # Event handler
                    symbol_name = first_line.split("{")[0].strip()
                else:
                    # Regular function - find the identifier
                    for child in parent.children:
                        if child.type == "function_declarator":
                            for subchild in child.children:
                                if subchild.type == "identifier":
                                    symbol_name = source[subchild.start_byte : subchild.end_byte]
                                    break
                            break
                    else:
                        return None

                # Look up symbol_id
                cursor = conn.execute(
                    """
                    SELECT symbol_id FROM symbols s
                    JOIN files f ON s.file_id = f.file_id
                    WHERE f.file_id = ? AND s.symbol_name = ?
                    LIMIT 1
                """,
                    (file_id, symbol_name),
                )

                result = cursor.fetchone()
                return result[0] if result else None

            parent = parent.parent

        return None

    def _extract_variable_references(self, root: Node, source: str, file_id: int, conn) -> int:
        """Extract variable usage (not declarations)"""
        count = 0

        # Query for identifier usage
        query = Query(
            self.language,
            """
            (identifier) @var
        """,
        )

        cursor = QueryCursor(query)
        cursor.set_byte_range(0, len(source.encode("utf8")))
        matches = cursor.matches(root)

        for pattern_index, captures_dict in matches:
            if "var" in captures_dict:
                for var_node in captures_dict["var"]:
                    # Skip if this is a function declaration or definition
                    if self._is_declaration(var_node):
                        continue

                    # Skip if this is a function name in a call (already handled)
                    parent = var_node.parent
                    if parent and parent.type == "call_expression":
                        continue

                    var_name = source[var_node.start_byte : var_node.end_byte]
                    line_num = var_node.start_point[0] + 1
                    col_num = var_node.start_point[1]

                    # Get context
                    lines = source.split("\n")
                    context = lines[line_num - 1].strip() if line_num <= len(lines) else ""

                    # Determine reference type
                    ref_type = "usage"
                    if parent:
                        # Check if it's an assignment
                        if parent.type == "assignment_expression":
                            # Check if identifier is on the left side
                            if parent.children and parent.children[0] == var_node:
                                ref_type = "assignment"

                    conn.execute(
                        """
                        INSERT INTO symbol_references
                        (symbol_name, file_id, line_number, column_number,
                         reference_type, context)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """,
                        (var_name, file_id, line_num, col_num, ref_type, context),
                    )

                    count += 1

        return count

    def _is_declaration(self, node: Node) -> bool:
        """Check if an identifier node is part of a declaration"""
        parent = node.parent
        while parent:
            if parent.type in (
                "function_definition",
                "declaration",
                "parameter_declaration",
                "init_declarator",
            ):
                return True
            parent = parent.parent
        return False

    def _extract_message_output(self, root: Node, source: str, file_id: int, conn) -> int:
        """Extract CAPL output() calls with message variables"""
        count = 0

        # Look for output(msgName) patterns
        query = Query(
            self.language,
            """
            (call_expression
              function: (identifier) @func_name
              arguments: (argument_list
                (identifier) @arg)) @call
        """,
        )

        cursor = QueryCursor(query)
        cursor.set_byte_range(0, len(source.encode("utf8")))
        matches = cursor.matches(root)

        for pattern_index, captures_dict in matches:
            if "func_name" in captures_dict and "arg" in captures_dict:
                for i, func_node in enumerate(captures_dict["func_name"]):
                    func_name = source[func_node.start_byte : func_node.end_byte]

                    # Check if it's output() function
                    if func_name == "output":
                        if i < len(captures_dict["arg"]):
                            arg_node = captures_dict["arg"][i]
                            msg_name = source[arg_node.start_byte : arg_node.end_byte]
                            line_num = arg_node.start_point[0] + 1

                            # Store as message usage
                            caller_id = self._find_containing_function(
                                arg_node, source, file_id, conn
                            )

                            conn.execute(
                                """
                                INSERT INTO message_usage
                                (message_name, usage_type, symbol_id, file_id, line_number)
                                VALUES (?, 'output', ?, ?, ?)
                            """,
                                (msg_name, caller_id, file_id, line_num),
                            )

                            count += 1

        return count

    def _extract_timer_usage(self, root: Node, source: str, file_id: int, conn) -> int:
        """Extract setTimer() calls"""
        count = 0

        query = Query(
            self.language,
            """
            (call_expression
              function: (identifier) @func_name
              arguments: (argument_list
                (identifier) @timer_arg)) @call
        """,
        )

        cursor = QueryCursor(query)
        cursor.set_byte_range(0, len(source.encode("utf8")))
        matches = cursor.matches(root)

        for pattern_index, captures_dict in matches:
            if "func_name" in captures_dict and "timer_arg" in captures_dict:
                for i, func_node in enumerate(captures_dict["func_name"]):
                    func_name = source[func_node.start_byte : func_node.end_byte]

                    if func_name == "setTimer":
                        if i < len(captures_dict["timer_arg"]):
                            timer_node = captures_dict["timer_arg"][i]
                            timer_name = source[timer_node.start_byte : timer_node.end_byte]
                            line_num = timer_node.start_point[0] + 1
                            col_num = timer_node.start_point[1]

                            # Get context
                            lines = source.split("\n")
                            context = lines[line_num - 1].strip() if line_num <= len(lines) else ""

                            conn.execute(
                                """
                                INSERT INTO symbol_references
                                (symbol_name, file_id, line_number, column_number,
                                 reference_type, context)
                                VALUES (?, ?, ?, ?, 'usage', ?)
                            """,
                                (timer_name, file_id, line_num, col_num, context),
                            )

                            count += 1

        return count

    def find_all_references(self, symbol_name: str) -> list[Reference]:
        """Find all references to a symbol across the codebase"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                SELECT f.file_path, sr.line_number, sr.column_number,
                       sr.context, sr.reference_type
                FROM symbol_references sr
                JOIN files f ON sr.file_id = f.file_id
                WHERE sr.symbol_name = ?
                ORDER BY f.file_path, sr.line_number
            """,
                (symbol_name,),
            )

            references = []
            for file_path, line, col, context, ref_type in cursor.fetchall():
                references.append(
                    Reference(
                        file_path=file_path,
                        line_number=line,
                        column=col or 0,
                        context=context or "",
                        reference_type=ref_type or "usage",
                    )
                )

            return references

    def get_call_graph(self, function_name: str) -> dict[str, list[str]]:
        """
        Get the call graph for a function

        Returns:
            Dict with 'callers' and 'callees' lists
        """
        with sqlite3.connect(self.db_path) as conn:
            # Find who calls this function
            cursor = conn.execute(
                """
                SELECT DISTINCT s.symbol_name, f.file_path, fc.line_number
                FROM function_calls fc
                JOIN symbols s ON fc.caller_symbol_id = s.symbol_id
                JOIN files f ON fc.file_id = f.file_id
                WHERE fc.callee_name = ?
                ORDER BY s.symbol_name
            """,
                (function_name,),
            )

            callers = [(name, Path(fp).name, line) for name, fp, line in cursor.fetchall()]

            # Find what this function calls
            cursor = conn.execute(
                """
                SELECT DISTINCT fc.callee_name, f.file_path, fc.line_number
                FROM function_calls fc
                JOIN symbols s ON fc.caller_symbol_id = s.symbol_id
                JOIN files f ON fc.file_id = f.file_id
                WHERE s.symbol_name = ?
                ORDER BY fc.callee_name
            """,
                (function_name,),
            )

            callees = [(name, Path(fp).name, line) for name, fp, line in cursor.fetchall()]

            return {"callers": callers, "callees": callees}

    def get_message_handlers(self, message_name: str) -> list[tuple[str, str, int]]:
        """Find all event handlers for a specific message"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                SELECT f.file_path, s.symbol_name, s.line_number
                FROM symbols s
                JOIN files f ON s.file_id = f.file_id
                WHERE s.symbol_type = 'event_handler'
                  AND s.symbol_name LIKE ?
                ORDER BY f.file_path
            """,
                (f"%message {message_name}%",),
            )

            return [(Path(fp).name, name, line) for fp, name, line in cursor.fetchall()]

    def get_message_outputs(self, message_name: str) -> list[tuple[str, str, int]]:
        """Find all places where a message is output"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                SELECT f.file_path, s.symbol_name, mu.line_number
                FROM message_usage mu
                JOIN files f ON mu.file_id = f.file_id
                LEFT JOIN symbols s ON mu.symbol_id = s.symbol_id
                WHERE mu.message_name = ? AND mu.usage_type = 'output'
                ORDER BY f.file_path, mu.line_number
            """,
                (message_name,),
            )

            return [
                (Path(fp).name, func or "(global)", line) for fp, func, line in cursor.fetchall()
            ]

    def generate_call_graph_dot(self, output_file: str = "call_graph.dot"):
        """Generate a GraphViz call graph"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT DISTINCT s.symbol_name, fc.callee_name
                FROM function_calls fc
                JOIN symbols s ON fc.caller_symbol_id = s.symbol_id
            """)

            edges = cursor.fetchall()

        with open(output_file, "w") as f:
            f.write("digraph CallGraph {\n")
            f.write("  rankdir=LR;\n")
            f.write("  node [shape=box, style=rounded];\n\n")

            # Add edges
            for caller, callee in edges:
                f.write(f'  "{caller}" -> "{callee}";\n')

            f.write("}\n")

        print(f"Call graph written to {output_file}")
        print(f"Generate image: dot -Tpng {output_file} -o call_graph.png")


# Testing and example usage
if __name__ == "__main__":
    import sys

    xref = CAPLCrossReferenceBuilder()

    if len(sys.argv) > 1:
        file_path = sys.argv[1]

        print(f"Building cross-references for: {file_path}")
        print("=" * 70)

        ref_count = xref.analyze_file_references(file_path)
        print(f"✓ Found {ref_count} references")

        # Example queries
        print("\nExample: Find all references to 'msgEngine':")
        refs = xref.find_all_references("msgEngine")
        for ref in refs[:10]:  # Limit to 10
            print(
                f"  {Path(ref.file_path).name}:{ref.line_number} "
                f"[{ref.reference_type}] {ref.context[:50]}"
            )

        if len(refs) > 10:
            print(f"  ... and {len(refs) - 10} more")
    else:
        print("Usage: python script.py <capl_file.can>")
