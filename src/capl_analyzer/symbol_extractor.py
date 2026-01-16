"""
CAPL Symbol Extractor using Tree-sitter
Extracts functions, event handlers, variables, and CAPL-specific constructs
"""

import sqlite3
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Dict
import tree_sitter_c as tsc
from tree_sitter import Language, Node, Parser, Query, QueryCursor


@dataclass
class Symbol:
    """Represents a symbol found in CAPL code"""

    name: str
    symbol_type: str  # 'function', 'event_handler', 'variable', 'message', 'timer', 'type_usage_error', 'forbidden_syntax', 'constant'
    line_number: int
    signature: str | None = None
    scope: str | None = None  # 'global', 'variables_block', 'local', 'forbidden', 'type_error'
    declaration_position: str | None = None  # 'block_start', 'mid_block'
    parent_symbol: str | None = None  # Which function/handler/testcase contains it
    context: str | None = None  # Additional context (e.g., 'missing_enum_keyword')


class CAPLSymbolExtractor:
    """Extract symbols from CAPL files"""

    def __init__(self, db_path: str = "aic.db"):
        self.db_path = db_path
        self.language = Language(tsc.language())
        self.parser = Parser(self.language)
        self.current_file_types = {}  # In-memory cache for types in current file
        self._init_database()
        self._init_type_definitions_table()

    def _init_database(self):
        """Create required tables if they don't exist"""
        conn = sqlite3.connect(self.db_path)
        try:
            with conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS files (
                        file_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        file_path TEXT UNIQUE NOT NULL,
                        last_parsed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        parse_success BOOLEAN,
                        file_hash TEXT
                    )
                """)

                conn.execute("""
                    CREATE TABLE IF NOT EXISTS symbols (
                        symbol_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        file_id INTEGER NOT NULL,
                        symbol_name TEXT NOT NULL,
                        symbol_type TEXT,
                        line_number INTEGER,
                        signature TEXT,
                        scope TEXT,
                        declaration_position TEXT,
                        parent_symbol TEXT,
                        context TEXT,
                        FOREIGN KEY (file_id) REFERENCES files(file_id)
                    )
                """)
        finally:
            conn.close()

    def _init_type_definitions_table(self):
        """Create table for enum/struct definitions"""
        conn = sqlite3.connect(self.db_path)
        try:
            with conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS type_definitions (
                        type_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        file_id INTEGER NOT NULL,
                        type_name TEXT NOT NULL,
                        type_kind TEXT NOT NULL,  -- 'enum' or 'struct'
                        line_number INTEGER,
                        members TEXT,  -- JSON array of members
                        scope TEXT,
                        FOREIGN KEY (file_id) REFERENCES files(file_id)
                    )
                """)

                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_type_definitions_name 
                    ON type_definitions(type_name)
                """)
        finally:
            conn.close()

    def extract_symbols(self, file_path: str) -> List[Symbol]:
        """
        Extract all symbols from a CAPL file

        Args:
            file_path: Path to the CAPL file

        Returns:
            List of Symbol objects
        """
        self.current_file_types = {}  # Reset for new file

        with open(file_path, "rb") as f:
            source_code = f.read()

        source_text = source_code.decode("utf8")
        tree = self.parser.parse(source_code)
        root = tree.root_node

        symbols = []

        # Extract definitions FIRST to populate current_file_types
        symbols.extend(self._extract_enum_definitions(root, source_text))
        symbols.extend(self._extract_struct_definitions(root, source_text))

        # Extract different types of symbols
        symbols.extend(self._extract_event_handlers(root, source_text))
        symbols.extend(self._extract_functions(root, source_text))
        symbols.extend(self._extract_variables_block(root, source_text))
        symbols.extend(self._extract_global_variables(root, source_text))
        symbols.extend(self._extract_all_local_variables(root, source_text))

        # New extractions
        symbols.extend(self._extract_type_usages(root, source_text))
        symbols.extend(self._extract_forbidden_syntax(root, source_text))

        return symbols

    def _extract_enum_definitions(self, root: Node, source: str) -> List[Symbol]:
        """
        Extract enum definitions and their members:
        enum NAME { MEMBER1, MEMBER2 };
        """
        symbols = []
        query = Query(
            self.language,
            """
            (enum_specifier
              name: (type_identifier) @enum_name
              body: (enumerator_list
                (enumerator
                  name: (identifier) @member_name) @member)*) @enum_def
        """,
        )

        cursor = QueryCursor(query)
        cursor.set_byte_range(0, len(source.encode("utf8")))
        matches = cursor.matches(root)

        for pattern_index, captures_dict in matches:
            if "enum_name" in captures_dict:
                for enum_node in captures_dict["enum_name"]:
                    enum_name = source[enum_node.start_byte : enum_node.end_byte]
                    self.current_file_types[enum_name] = "enum"

            if "member_name" in captures_dict:
                for member_node in captures_dict["member_name"]:
                    member_name = source[member_node.start_byte : member_node.end_byte]
                    line_num = member_node.start_point[0] + 1

                    symbols.append(
                        Symbol(
                            name=member_name,
                            symbol_type="constant",
                            line_number=line_num,
                            scope="global",
                        )
                    )

        return symbols

    def _extract_struct_definitions(self, root: Node, source: str) -> List[Symbol]:
        """
        Extract struct definitions:
        struct NAME { ... };
        """
        symbols = []
        query = Query(
            self.language,
            """
            (struct_specifier
              name: (type_identifier) @struct_name
              body: (field_declaration_list) @members) @struct_def
        """,
        )

        cursor = QueryCursor(query)
        cursor.set_byte_range(0, len(source.encode("utf8")))
        matches = cursor.matches(root)

        for pattern_index, captures_dict in matches:
            if "struct_name" in captures_dict:
                for struct_node in captures_dict["struct_name"]:
                    struct_name = source[struct_node.start_byte : struct_node.end_byte]
                    self.current_file_types[struct_name] = "struct"

        return symbols

    def _get_type_kind(self, type_name: str) -> Optional[str]:
        """Check if a type name is a known enum/struct"""
        # Check local cache first
        if type_name in self.current_file_types:
            return self.current_file_types[type_name]

        conn = sqlite3.connect(self.db_path)
        try:
            # Check if table exists first to avoid crash on fresh start
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='type_definitions'"
            )
            if not cursor.fetchone():
                return None

            cursor = conn.execute(
                """
                SELECT type_kind FROM type_definitions
                WHERE type_name = ?
            """,
                (type_name,),
            )

            result = cursor.fetchone()
            return result[0] if result else None
        except sqlite3.Error:
            return None
        finally:
            conn.close()

    def _extract_forbidden_syntax(self, root: Node, source: str) -> List[Symbol]:
        """Detect function declarations and extern keywords"""
        forbidden = []

        # 1. Detect function declarations (no body)
        query = Query(
            self.language,
            """
            (declaration
              declarator: (function_declarator
                declarator: (identifier) @func_name)) @func_decl
        """,
        )

        cursor = QueryCursor(query)
        cursor.set_byte_range(0, len(source.encode("utf8")))
        matches = cursor.matches(root)

        for pattern_index, captures_dict in matches:
            if "func_decl" in captures_dict:
                for func_node in captures_dict["func_decl"]:
                    # A definition is a 'function_definition' node, not 'declaration'
                    func_name_nodes = captures_dict.get("func_name", [])
                    if func_name_nodes:
                        func_name = source[
                            func_name_nodes[0].start_byte : func_name_nodes[0].end_byte
                        ]
                        line_num = func_node.start_point[0] + 1

                        forbidden.append(
                            Symbol(
                                name=func_name,
                                symbol_type="forbidden_syntax",
                                line_number=line_num,
                                signature=source[func_node.start_byte : func_node.end_byte].strip(),
                                scope="forbidden",
                                context="function_declaration",
                            )
                        )

        # 2. Detect extern keyword
        lines = source.split('\n')
        for i, line in enumerate(lines):
            # Strip comments to avoid false positives in comments
            clean_line = line.split('//')[0]
            if re.search(r'\bextern\b', clean_line):
                # Found extern keyword
                forbidden.append(Symbol(
                    name='extern',
                    symbol_type='forbidden_syntax',
                    line_number=i + 1,
                    signature=line.strip(),
                    scope='forbidden',
                    context='extern_keyword'
                ))

        return forbidden

    def _extract_event_handlers(self, root: Node, source: str) -> List[Symbol]:
        """
        Extract CAPL event handlers like 'on message', 'on signal', 'on timer'
        """
        symbols = []
        query = Query(
            self.language,
            """
            (function_definition
              declarator: (function_declarator
                declarator: (identifier) @func_name
                parameters: (parameter_list) @params)?) @func
        """,
        )

        cursor = QueryCursor(query)
        cursor.set_byte_range(0, len(source.encode("utf8")))
        matches = cursor.matches(root)

        for pattern_index, captures_dict in matches:
            if "func" in captures_dict:
                for func_node in captures_dict["func"]:
                    func_text = source[func_node.start_byte : func_node.end_byte]
                    first_line = func_text.split("\n")[0].strip()
                    if first_line.startswith("on "):
                        event_info = self._parse_event_handler(first_line, func_node)
                        if event_info:
                            symbols.append(event_info)
        return symbols

    def _parse_event_handler(self, first_line: str, node: Node) -> Optional[Symbol]:
        line_num = node.start_point[0] + 1
        parts = first_line.split()
        if len(parts) < 2:
            return None
        event_type = parts[1]
        if event_type in ("start", "preStart", "stopMeasurement", "preStop"):
            name = f"on {event_type}"
        elif len(parts) >= 3:
            name = f"on {event_type} {parts[2]}"
        else:
            name = f"on {event_type}"
        return Symbol(
            name=name,
            symbol_type="event_handler",
            line_number=line_num,
            signature=first_line.split("{")[0].strip(),
            scope="global",
        )

    def _extract_functions(self, root: Node, source: str) -> List[Symbol]:
        symbols = []
        query = Query(
            self.language,
            """
            (function_definition
              type: (_) @return_type
              declarator: (function_declarator
                declarator: (identifier) @func_name
                parameters: (parameter_list) @params)) @func
        """,
        )
        cursor = QueryCursor(query)
        cursor.set_byte_range(0, len(source.encode("utf8")))
        matches = cursor.matches(root)
        for pattern_index, captures_dict in matches:
            if "func" in captures_dict and "func_name" in captures_dict:
                for i, func_node in enumerate(captures_dict["func"]):
                    func_text = source[func_node.start_byte : func_node.end_byte]
                    first_line = func_text.split("\n")[0].strip()
                    if first_line.startswith("on "):
                        continue
                    func_name_nodes = captures_dict.get("func_name", [])
                    if i < len(func_name_nodes):
                        name_node = func_name_nodes[i]
                        func_name = source[name_node.start_byte : name_node.end_byte]
                        signature = (
                            func_text.split("{")[0].strip() if "{" in func_text else first_line
                        )
                        symbols.append(
                            Symbol(
                                name=func_name,
                                symbol_type="function",
                                line_number=func_node.start_point[0] + 1,
                                signature=signature,
                                scope="global",
                            )
                        )
        return symbols

    def _extract_variables_block(self, root: Node, source: str) -> List[Symbol]:
        symbols = []
        # Find the compound_statement that follows the 'variables' ERROR/identifier
        variables_node = None
        for i, child in enumerate(root.children):
            node_text = source[child.start_byte:child.end_byte].strip()
            if "variables" in node_text and (child.type == "ERROR" or child.type == "identifier"):
                # The next node should be the block
                if i + 1 < len(root.children) and root.children[i+1].type == "compound_statement":
                    variables_node = root.children[i+1]
                    break
        
        if variables_node:
            for statement in variables_node.children:
                if statement.type == "declaration":
                    var_info = self._parse_variable_from_node(statement, source)
                    if var_info:
                        symbols.append(Symbol(
                            name=var_info["name"],
                            symbol_type=self._get_symbol_type_from_signature(var_info["signature"]),
                            line_number=statement.start_point[0] + 1,
                            signature=var_info["signature"],
                            scope="variables_block"
                        ))
                elif statement.type in ("enum_specifier", "struct_specifier"):
                    # Handle definitions inside variables block (might be nested)
                    pass # Handled by specialized extractors
        
        return symbols

    def _get_symbol_type_from_signature(self, signature: str) -> str:
        if signature.startswith("message "): return "message_variable"
        if signature.startswith("msTimer "): return "timer"
        if signature.startswith("signal "): return "signal_variable"
        return "variable"

    def _parse_variable_declaration(self, line: str, line_num: int) -> Optional[Symbol]:
        line = line.split(";")[0].strip()
        if "//" in line:
            line = line.split("//")[0].strip()
        parts = line.split()
        if len(parts) < 2:
            return None

        var_type = parts[0]
        # Ignore definitions
        if var_type in ("enum", "struct") and "{" in line:
            return None

        if var_type in ("message", "enum", "struct") and len(parts) >= 3:
            var_name = parts[2]
        else:
            var_name = parts[1]

        if "=" in var_name:
            var_name = var_name.split("=")[0].strip()

        symbol_type = "variable"
        if var_type == "message":
            symbol_type = "message_variable"
        elif var_type == "msTimer":
            symbol_type = "timer"
        elif var_type == "signal":
            symbol_type = "signal_variable"

        return Symbol(
            name=var_name, symbol_type=symbol_type, line_number=line_num, signature=line, scope=None
        )

    def _extract_global_variables(self, root: Node, source: str) -> List[Symbol]:
        symbols = []
        query = Query(self.language, """
            (declaration
              declarator: [
                (identifier) @var_name
                (init_declarator
                  declarator: (identifier) @var_name)
              ]) @decl
        """)
        cursor = QueryCursor(query)
        cursor.set_byte_range(0, len(source.encode('utf8')))
        matches = cursor.matches(root)
        for pattern_index, captures_dict in matches:
            if "decl" in captures_dict and "var_name" in captures_dict:
                for i, decl_node in enumerate(captures_dict["decl"]):
                    if self._is_global_scope(decl_node):
                        if not self._is_in_variables_block(decl_node, source):
                            # Get name and signature
                            var_name_nodes = captures_dict.get("var_name", [])
                            if i < len(var_name_nodes):
                                name_node = var_name_nodes[i]
                                var_name = source[name_node.start_byte:name_node.end_byte]
                                signature = source[decl_node.start_byte:decl_node.end_byte].split('\n')[0].strip()
                                symbols.append(Symbol(
                                    name=var_name,
                                    symbol_type='variable',
                                    line_number=decl_node.start_point[0] + 1,
                                    signature=signature,
                                    scope='global'
                                ))
        return symbols

    def _is_global_scope(self, node: Node) -> bool:
        parent = node.parent
        while parent:
            if parent.type == "function_definition":
                return False
            parent = parent.parent
        return True

    def _is_in_variables_block(self, node: Node, source: str) -> bool:
        # Check if any parent is a compound_statement preceded by 'variables'
        parent = node.parent
        while parent:
            if parent.type == "compound_statement":
                # Check sibling before this parent
                idx = -1
                if parent.parent:
                    for i, child in enumerate(parent.parent.children):
                        if child == parent:
                            idx = i
                            break
                    if idx > 0:
                        prev_sibling = parent.parent.children[idx-1]
                        prev_text = source[prev_sibling.start_byte:prev_sibling.end_byte].strip()
                        if "variables" in prev_text:
                            return True
            parent = parent.parent
        return False

    def _extract_all_local_variables(self, root: Node, source: str) -> List[Symbol]:
        all_locals = []
        query = Query(
            self.language,
            """
            (function_definition
              body: (compound_statement) @body) @func
        """,
        )
        cursor = QueryCursor(query)
        cursor.set_byte_range(0, len(source.encode("utf8")))
        matches = cursor.matches(root)
        for pattern_index, captures_dict in matches:
            if "func" in captures_dict and "body" in captures_dict:
                for i, func_node in enumerate(captures_dict["func"]):
                    block_info = self._get_block_info(func_node, source)
                    if i < len(captures_dict["body"]):
                        all_locals.extend(
                            self._analyze_block_body(
                                captures_dict["body"], source, block_info["name"]
                            )
                        )
        return all_locals

    def _get_block_info(self, func_node: Node, source: str) -> dict:
        func_text = source[func_node.start_byte : func_node.end_byte]
        first_line = func_text.split("\n")[0].strip()
        if first_line.startswith("testcase "):
            return {"type": "testcase", "name": first_line.split("{")[0].strip()}
        if first_line.startswith("on "):
            return {"type": "event_handler", "name": first_line.split("{")[0].strip()}
        for child in func_node.children:
            if child.type == "function_declarator":
                for subchild in child.children:
                    if subchild.type == "identifier":
                        return {
                            "type": "function",
                            "name": source[subchild.start_byte : subchild.end_byte],
                        }
        return {"type": "unknown", "name": "(unknown)"}

    def _analyze_block_body(self, block_node: Node, source: str, block_name: str) -> List[Symbol]:
        symbols = []
        first_executable_line = None
        for statement in block_node.children:
            if statement.type == "declaration":
                var_info = self._parse_variable_from_node(statement, source)
                if var_info:
                    position = "block_start" if first_executable_line is None else "mid_block"
                    symbols.append(
                        Symbol(
                            name=var_info["name"],
                            symbol_type="variable",
                            line_number=statement.start_point[0] + 1,
                            signature=var_info["signature"],
                            scope="local",
                            declaration_position=position,
                            parent_symbol=block_name,
                        )
                    )
            elif statement.type not in ("{", "}", "comment"):
                if first_executable_line is None:
                    first_executable_line = statement.start_point[0] + 1
        return symbols

    def _parse_variable_from_node(self, node: Node, source: str) -> Optional[dict]:
        text = source[node.start_byte : node.end_byte]
        for child in node.children:
            if child.type == "init_declarator":
                for subchild in child.children:
                    if subchild.type == "identifier":
                        return {
                            "name": source[subchild.start_byte : subchild.end_byte],
                            "signature": text.strip(),
                        }
            elif child.type == "identifier":
                return {
                    "name": source[child.start_byte : child.end_byte],
                    "signature": text.strip(),
                }
        return None

    def _extract_type_usages(self, root: Node, source: str) -> List[Symbol]:
        usages = []
        query = Query(
            self.language,
            """
            (declaration
              type: (type_identifier) @type_name
              declarator: (identifier) @var_name) @decl
        """,
        )
        cursor = QueryCursor(query)
        cursor.set_byte_range(0, len(source.encode("utf8")))
        matches = cursor.matches(root)
        for pattern_index, captures_dict in matches:
            if "type_name" in captures_dict and "var_name" in captures_dict:
                for i, type_node in enumerate(captures_dict["type_name"]):
                    type_name = source[type_node.start_byte : type_node.end_byte]
                    type_kind = self._get_type_kind(type_name)
                    if type_kind:
                        if not self._has_type_keyword(type_node, source, type_kind):
                            if i < len(captures_dict["var_name"]):
                                var_node = captures_dict["var_name"][i]
                                var_name = source[var_node.start_byte : var_node.end_byte]
                                usages.append(
                                    Symbol(
                                        name=var_name,
                                        symbol_type="type_usage_error",
                                        line_number=type_node.start_point[0] + 1,
                                        signature=f"{type_name} {var_name}",
                                        scope="type_error",
                                        context=f"missing_{type_kind}_keyword",
                                    )
                                )
        return usages

    def _has_type_keyword(self, type_node: Node, source: str, expected_keyword: str) -> bool:
        start_of_statement = type_node.parent.start_byte
        text_before = source[start_of_statement : type_node.start_byte]
        return expected_keyword in text_before.split()

    def store_symbols(self, file_path: str) -> int:
        file_path = str(Path(file_path).resolve())
        symbols = self.extract_symbols(file_path)
        
        with open(file_path, 'rb') as f:
            source_code = f.read()
        source_text = source_code.decode("utf8")
        tree = self.parser.parse(source_code)
        root = tree.root_node
        
        conn = sqlite3.connect(self.db_path)
        try:
            with conn:
                cursor = conn.execute(
                    """
                    INSERT INTO files (file_path, parse_success)
                    VALUES (?, 1)
                    ON CONFLICT(file_path) DO UPDATE SET last_parsed = CURRENT_TIMESTAMP
                    RETURNING file_id
                """,
                    (file_path,),
                )
                file_id = cursor.fetchone()[0]
                conn.execute("DELETE FROM symbols WHERE file_id = ?", (file_id,))
                conn.execute("DELETE FROM type_definitions WHERE file_id = ?", (file_id,))
                for symbol in symbols:
                    conn.execute(
                        """
                        INSERT INTO symbols (file_id, symbol_name, symbol_type, line_number, signature, scope, declaration_position, parent_symbol, context)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                        (
                            file_id,
                            symbol.name,
                            symbol.symbol_type,
                            symbol.line_number,
                            symbol.signature,
                            symbol.scope,
                            symbol.declaration_position,
                            symbol.parent_symbol,
                            symbol.context,
                        ),
                    )
                self._extract_and_store_type_definitions(file_id, root, source_text, conn)
        finally:
            conn.close()
        return len(symbols)

    def _extract_and_store_type_definitions(
        self,
        file_id: int,
        root: Node,
        source: str,
        conn: sqlite3.Connection,
    ):
        query_enum = Query(
            self.language,
            """(enum_specifier name: (type_identifier) @enum_name body: (enumerator_list) @members) @enum_def""",
        )
        cursor_enum = QueryCursor(query_enum)
        cursor_enum.set_byte_range(0, len(source.encode("utf8")))
        for match in cursor_enum.matches(root):
            if "enum_name" in match[1]:
                for enum_node in match[1]["enum_name"]:
                    scope = (
                        "variables_block"
                        if self._is_in_variables_block(enum_node, source)
                        else "global"
                    )
                    conn.execute(
                        """INSERT INTO type_definitions (file_id, type_name, type_kind, line_number, scope) VALUES (?, ?, 'enum', ?, ?)""",
                        (
                            file_id,
                            source[enum_node.start_byte : enum_node.end_byte],
                            enum_node.start_point[0] + 1,
                            scope,
                        ),
                    )

        query_struct = Query(
            self.language,
            """(struct_specifier name: (type_identifier) @struct_name body: (field_declaration_list) @members) @struct_def""",
        )
        cursor_struct = QueryCursor(query_struct)
        cursor_struct.set_byte_range(0, len(source.encode("utf8")))
        for match in cursor_struct.matches(root):
            if "struct_name" in match[1]:
                for struct_node in match[1]["struct_name"]:
                    scope = (
                        "variables_block"
                        if self._is_in_variables_block(struct_node, source)
                        else "global"
                    )
                    conn.execute(
                        """INSERT INTO type_definitions (file_id, type_name, type_kind, line_number, scope) VALUES (?, ?, 'struct', ?, ?)""",
                        (
                            file_id,
                            source[struct_node.start_byte : struct_node.end_byte],
                            struct_node.start_point[0] + 1,
                            scope,
                        ),
                    )

    def find_symbol(self, symbol_name: str, symbol_type: str | None = None) -> List[tuple]:
        conn = sqlite3.connect(self.db_path)
        try:
            if symbol_type:
                cursor = conn.execute(
                    "SELECT f.file_path, s.symbol_type, s.line_number, s.signature FROM symbols s JOIN files f ON s.file_id = f.file_id WHERE s.symbol_name = ? AND s.symbol_type = ? ORDER BY f.file_path, s.line_number",
                    (symbol_name, symbol_type),
                )
            else:
                cursor = conn.execute(
                    "SELECT f.file_path, s.symbol_type, s.line_number, s.signature FROM symbols s JOIN files f ON s.file_id = f.file_id WHERE s.symbol_name = ? ORDER BY f.file_path, s.line_number",
                    (symbol_name,),
                )
            return cursor.fetchall()
        finally:
            conn.close()

    def list_symbols_in_file(self, file_path: str) -> List[tuple]:
        file_path = str(Path(file_path).resolve())
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.execute(
                "SELECT s.symbol_name, s.symbol_type, s.line_number, s.signature FROM symbols s JOIN files f ON s.file_id = f.file_id WHERE f.file_path = ? ORDER BY s.line_number",
                (file_path,),
            )
            return cursor.fetchall()
        finally:
            conn.close()

    def get_event_handlers(self) -> List[tuple]:
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.execute(
                "SELECT f.file_path, s.symbol_name, s.line_number FROM symbols s JOIN files f ON s.file_id = f.file_id WHERE s.symbol_type = 'event_handler' ORDER BY s.symbol_name, f.file_path"
            )
            return cursor.fetchall()
        finally:
            conn.close()


def update_database_schema(db_path: str = "aic.db"):
    conn = sqlite3.connect(db_path)
    try:
        with conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='symbols'"
            )
            if not cursor.fetchone():
                return
            cursor = conn.execute("PRAGMA table_info(symbols)")
            columns = {row[1] for row in cursor.fetchall()}
            for col in ["signature", "scope", "declaration_position", "parent_symbol", "context"]:
                if col not in columns:
                    conn.execute(f"ALTER TABLE symbols ADD COLUMN {col} TEXT")

            # Check type_definitions table
            cursor = conn.execute("PRAGMA table_info(type_definitions)")
            type_cols = {row[1] for row in cursor.fetchall()}
            if "scope" not in type_cols:
                conn.execute("ALTER TABLE type_definitions ADD COLUMN scope TEXT")
    finally:
        conn.close()


if __name__ == "__main__":
    import sys

    update_database_schema()
    extractor = CAPLSymbolExtractor()
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        num_symbols = extractor.store_symbols(file_path)
        print(f"Extracted and stored {num_symbols} symbols from {file_path}")
        symbols = extractor.list_symbols_in_file(file_path)
        for name, sym_type, line, sig in symbols:
            print(f"Line {line:4d} | {sym_type:15s} | {name}")
    else:
        print("Usage: python script.py <capl_file.can>")