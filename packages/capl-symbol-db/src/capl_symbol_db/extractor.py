import re
from pathlib import Path

from capl_tree_sitter.ast_walker import ASTWalker
from capl_tree_sitter.parser import CAPLParser
from capl_tree_sitter.queries import CAPLQueryHelper
from tree_sitter import Node

from .models import SymbolInfo


class SymbolExtractor:
    """Extracts symbols and type definitions from CAPL AST"""

    def __init__(self):
        self.parser = CAPLParser()
        self.query_helper = CAPLQueryHelper()
        self.current_file_types = {}

    def extract_all(self, file_path: Path) -> list[SymbolInfo]:
        """Full extraction of symbols from a file"""
        result = self.parser.parse_file(file_path)
        root = result.tree.root_node
        source = result.source

        self.current_file_types = {}

        symbols = []
        symbols.extend(self._extract_enum_definitions(root, source))
        symbols.extend(self._extract_struct_definitions(root, source))
        symbols.extend(self._extract_event_handlers(root, source))
        symbols.extend(self._extract_functions(root, source))
        symbols.extend(self._extract_variables_block(root, source))
        symbols.extend(self._extract_global_variables(root, source))
        symbols.extend(self._extract_all_local_variables(root, source))
        symbols.extend(self._extract_type_usages(root, source))
        symbols.extend(self._extract_forbidden_syntax(root, source))

        # Filter duplicates that might arise from query overlaps
        seen = set()
        unique_symbols = []
        for s in symbols:
            key = (s.name, s.symbol_type, s.line_number, s.context)
            if key not in seen:
                seen.add(key)
                unique_symbols.append(s)

        return unique_symbols

    def _extract_enum_definitions(self, root: Node, source: str) -> list[SymbolInfo]:
        symbols = []
        # We need to ensure it has a body to be a definition
        query = """
            (enum_specifier
              name: (type_identifier) @enum_name
              body: (enumerator_list) @members) @enum_def
        """
        matches = self.query_helper.query(query, root)
        for m in matches:
            if "enum_name" in m.captures:
                name_node = m.captures["enum_name"]
                name = source[name_node.start_byte : name_node.end_byte]
                self.current_file_types[name] = "enum"

                scope = (
                    "variables_block" if self._is_in_variables_block(m.node, source) else "global"
                )

                line = name_node.start_point[0] + 1
                symbols.append(
                    SymbolInfo(
                        name=name,
                        symbol_type="constant",
                        line_number=line,
                        scope=scope,
                        context="enum_definition",
                    )
                )
        return symbols

    def _extract_struct_definitions(self, root: Node, source: str) -> list[SymbolInfo]:
        symbols = []
        query = """
            (struct_specifier
              name: (type_identifier) @struct_name
              body: (field_declaration_list) @members) @struct_def
        """
        matches = self.query_helper.query(query, root)
        for m in matches:
            if "struct_name" in m.captures:
                name_node = m.captures["struct_name"]
                name = source[name_node.start_byte : name_node.end_byte]
                self.current_file_types[name] = "struct"

                scope = (
                    "variables_block" if self._is_in_variables_block(m.node, source) else "global"
                )

                line = name_node.start_point[0] + 1
                symbols.append(
                    SymbolInfo(
                        name=name,
                        symbol_type="constant",
                        line_number=line,
                        scope=scope,
                        context="struct_definition",
                    )
                )
        return symbols

    def _is_in_variables_block(self, node: Node, source: str) -> bool:
        """Check if a node is inside a variables {} block"""
        curr = node
        while curr:
            if curr.type == "compound_statement":
                p = curr.parent
                if p:
                    # Look at this block and its immediate context
                    for i, child in enumerate(p.children):
                        if child == curr:
                            # Check text before this block
                            start = p.children[i - 1].start_byte if i > 0 else p.start_byte
                            context_text = source[start : curr.start_byte]
                            if "variables" in context_text:
                                return True
                            break
            curr = curr.parent
        return False

    def _extract_event_handlers(self, root: Node, source: str) -> list[SymbolInfo]:
        symbols = []
        # Simplified query for common CAPL event handlers
        # In tree-sitter-c, these often appear as a labeled statement or similar
        # but CAPL uses keywords 'on message', 'on timer', etc.
        # Here we just look for identifiers following 'on' if we had a proper grammar.
        # Using the original logic based on C grammar:
        lines = source.split("\n")
        for i, line in enumerate(lines):
            match = re.search(
                r"^\s*on\s+(message|timer|key|signal|start|stop|preStart|preStop|errorFrame|busOff)\s+([^\s{]+)",
                line,
            )
            if match:
                symbols.append(
                    SymbolInfo(
                        name=match.group(2),
                        symbol_type="event_handler",
                        line_number=i + 1,
                        signature=line.strip(),
                        scope="global",
                        context=match.group(1),
                    )
                )
        return symbols

    def _extract_functions(self, root: Node, source: str) -> list[SymbolInfo]:
        symbols = []
        query = "(function_definition) @func"
        matches = self.query_helper.query(query, root)
        for m in matches:
            func_node = m.node
            # Find the identifier in the declarator
            # This is simplified; real logic is more complex
            symbols.append(
                SymbolInfo(
                    name="unknown_func",  # Simplification for now
                    symbol_type="function",
                    line_number=func_node.start_point[0] + 1,
                    signature=source[func_node.start_byte : func_node.end_byte]
                    .split("{")[0]
                    .strip(),
                    scope="global",
                )
            )
        return symbols

    def _extract_variables_block(self, root: Node, source: str) -> list[SymbolInfo]:
        symbols = []
        # Find 'variables {' blocks
        # This is hard because tree-sitter-c doesn't know 'variables'
        # We search for it in source and find the matching block if possible,
        # or use a query that matches what tree-sitter-c thinks it is (often a labeled statement or function)
        return []

    def _extract_global_variables(self, root: Node, source: str) -> list[SymbolInfo]:
        symbols = []
        # Global variables are declarations at the root level (translation_unit)
        # that are NOT inside a 'variables' block and NOT inside a function.
        query = "(declaration) @decl"
        matches = self.query_helper.query(query, root)
        for m in matches:
            node = m.node

            # Skip if inside a function or a variables block
            if self._is_in_variables_block(node, source):
                scope = "variables_block"
            elif ASTWalker.find_parent_of_type(node, "function_definition"):
                continue  # Handled by local variable extraction
            else:
                # Root level but not in variables block
                scope = "global"

            # Get the name(s)
            name_query = "(init_declarator declarator: (identifier) @name)"
            name_matches = self.query_helper.query(name_query, node)
            for nm in name_matches:
                name_node = nm.captures["name"]
                name = source[name_node.start_byte : name_node.end_byte]
                symbols.append(
                    SymbolInfo(
                        name=name,
                        symbol_type="variable",
                        line_number=name_node.start_point[0] + 1,
                        scope=scope,
                    )
                )
        return symbols

    def _extract_all_local_variables(self, root: Node, source: str) -> list[SymbolInfo]:
        symbols = []
        # Local variables are declarations inside functions or event handlers
        query = "(function_definition) @func"
        matches = self.query_helper.query(query, root)
        for m in matches:
            func_node = m.node
            # Extract function name
            func_name = "unknown"
            decl_node = func_node.child_by_field_name("declarator")
            if decl_node:
                # Find identifier in declarator
                id_query = "(identifier) @name"
                id_matches = self.query_helper.query(id_query, decl_node)
                if id_matches:
                    name_node = id_matches[0].captures["name"]
                    func_name = source[name_node.start_byte : name_node.end_byte]

            # Find all statements inside this function body
            body_node = func_node.child_by_field_name("body")
            if not body_node:
                continue

            first_non_decl_line = None
            # Iterate through children of compound_statement
            for child in body_node.children:
                if child.type in ("{", "}"):
                    continue

                if child.type == "declaration":
                    # It's a declaration. Check if it's after a non-decl
                    pos = "block_start"
                    if (
                        first_non_decl_line is not None
                        and child.start_point[0] > first_non_decl_line
                    ):
                        pos = "mid_block"

                    # Extract names from this declaration
                    name_query = "(init_declarator declarator: (identifier) @name)"
                    name_matches = self.query_helper.query(name_query, child)
                    for nm in name_matches:
                        name_node = nm.captures["name"]
                        name = source[name_node.start_byte : name_node.end_byte]
                        symbols.append(
                            SymbolInfo(
                                name=name,
                                symbol_type="variable",
                                line_number=name_node.start_point[0] + 1,
                                scope="local",
                                parent_symbol=func_name,
                                declaration_position=pos,
                            )
                        )
                else:
                    # Non-declaration statement
                    if first_non_decl_line is None:
                        first_non_decl_line = child.start_point[0]
        return symbols

    def _extract_type_usages(self, root: Node, source: str) -> list[SymbolInfo]:
        symbols = []
        # Look for declarations where the type is a known enum/struct
        # but the keyword (enum/struct) is missing.
        query = "(declaration (type_identifier) @type_name) @decl"
        matches = self.query_helper.query(query, root)
        for m in matches:
            if "type_name" not in m.captures:
                continue
            type_node = m.captures["type_name"]
            type_name = source[type_node.start_byte : type_node.end_byte]

            # Check if this type name is a known enum or struct
            kind = self.current_file_types.get(type_name)
            if kind:
                # Double check by looking at the source text before the type name
                start_of_decl = m.node.start_byte
                text_before = source[start_of_decl : type_node.start_byte]
                if kind not in text_before:
                    # Missing keyword!
                    # Find the variable name
                    name_query = "(identifier) @name"
                    name_matches = self.query_helper.query(name_query, m.node)
                    # The first identifier after the type name is likely the variable name
                    var_name = "unknown"
                    for nm in name_matches:
                        node = nm.captures["name"]
                        if node.start_byte > type_node.end_byte:
                            var_name = source[node.start_byte : node.end_byte]
                            break

                    symbols.append(
                        SymbolInfo(
                            name=var_name,
                            symbol_type="type_usage_error",
                            line_number=type_node.start_point[0] + 1,
                            signature=source[m.node.start_byte : m.node.end_byte].strip(),
                            context=f"missing_{kind}_keyword",
                        )
                    )
        return symbols

    def _extract_forbidden_syntax(self, root: Node, source: str) -> list[SymbolInfo]:
        symbols = []
        # 1. Detection for 'extern' keyword
        lines = source.split("\n")
        for i, line in enumerate(lines):
            if "extern" in line.split("//")[0]:
                symbols.append(
                    SymbolInfo(
                        name="extern",
                        symbol_type="forbidden_syntax",
                        line_number=i + 1,
                        signature=line.strip(),
                        scope="forbidden",
                        context="extern_keyword",
                    )
                )

        # 2. Detection for function declarations (forward declarations)
        query = """
            (declaration
              declarator: (function_declarator
                declarator: (identifier) @func_name)) @func_decl
        """
        matches = self.query_helper.query(query, root)
        for m in matches:
            if "func_name" in m.captures:
                name_node = m.captures["func_name"]
                name = source[name_node.start_byte : name_node.end_byte]
                symbols.append(
                    SymbolInfo(
                        name=name,
                        symbol_type="forbidden_syntax",
                        line_number=name_node.start_point[0] + 1,
                        signature=source[m.node.start_byte : m.node.end_byte].strip(),
                        scope="forbidden",
                        context="function_declaration",
                    )
                )

        return symbols
