import re
from pathlib import Path

from capl_tree_sitter import ASTWalker, CAPLPatterns, CAPLParser, CAPLQueryHelper
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
                name = ASTWalker.get_text(name_node, source)
                self.current_file_types[name] = "enum"

                scope = (
                    "variables_block" if CAPLPatterns.is_inside_variables_block(m.node, source) else "global"
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
                name = ASTWalker.get_text(name_node, source)
                self.current_file_types[name] = "struct"

                scope = (
                    "variables_block" if CAPLPatterns.is_inside_variables_block(m.node, source) else "global"
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

    def _extract_event_handlers(self, root: Node, source: str) -> list[SymbolInfo]:
        symbols = []
        # Use CAPLPatterns to find event handlers
        for func in ASTWalker.find_all_by_type(root, "function_definition"):
            if CAPLPatterns.is_event_handler(func, source):
                name = CAPLPatterns.get_function_name(func, source) or "unknown"
                signature = ASTWalker.get_text(func, source).split("{")[0].strip()
                
                # Heuristic to identify event type
                context = "event"
                if "message" in signature: context = "message"
                elif "timer" in signature: context = "timer"
                elif "key" in signature: context = "key"
                elif "start" in signature: context = "start"

                symbols.append(
                    SymbolInfo(
                        name=name,
                        symbol_type="event_handler",
                        line_number=func.start_point[0] + 1,
                        signature=signature,
                        scope="global",
                        context=context,
                    )
                )
        
        # Fallback for some regex cases if needed, but CAPLPatterns should handle most
        return symbols

    def _extract_functions(self, root: Node, source: str) -> list[SymbolInfo]:
        symbols = []
        query = "(function_definition) @func"
        matches = self.query_helper.query(query, root)
        for m in matches:
            func_node = m.node
            if CAPLPatterns.is_event_handler(func_node, source):
                continue

            name = CAPLPatterns.get_function_name(func_node, source) or "unknown_func"
            symbols.append(
                SymbolInfo(
                    name=name,
                    symbol_type="function",
                    line_number=func_node.start_point[0] + 1,
                    signature=ASTWalker.get_text(func_node, source).split("{")[0].strip(),
                    scope="global",
                )
            )
        return symbols

    def _extract_variables_block(self, root: Node, source: str) -> list[SymbolInfo]:
        # Variables block itself is not usually stored as a symbol, 
        # but its contents are marked as scope='variables_block'
        return []

    def _extract_global_variables(self, root: Node, source: str) -> list[SymbolInfo]:
        symbols = []
        query = "(declaration) @decl"
        matches = self.query_helper.query(query, root)
        for m in matches:
            node = m.node

            if CAPLPatterns.is_function_declaration(node):
                continue

            # Skip if inside a function
            if not CAPLPatterns.is_global_scope(node):
                continue
            
            scope = (
                "variables_block" if CAPLPatterns.is_inside_variables_block(node, source) else "global"
            )

            # Get the name(s)
            name = CAPLPatterns.get_variable_name(node, source)
            if name:
                symbols.append(
                    SymbolInfo(
                        name=name,
                        symbol_type="variable",
                        line_number=node.start_point[0] + 1,
                        scope=scope,
                    )
                )
        return symbols

    def _extract_all_local_variables(self, root: Node, source: str) -> list[SymbolInfo]:
        symbols = []
        query = "(function_definition) @func"
        matches = self.query_helper.query(query, root)
        for m in matches:
            func_node = m.node
            func_name = CAPLPatterns.get_function_name(func_node, source) or "unknown"

            # Find all statements inside this function body
            body_node = ASTWalker.get_child_of_type(func_node, "compound_statement")
            if not body_node:
                continue

            first_non_decl_line = None
            for child in body_node.children:
                if child.type in ("{", "}"):
                    continue

                if child.type == "declaration":
                    pos = "block_start"
                    if (
                        first_non_decl_line is not None
                        and child.start_point[0] > first_non_decl_line
                    ):
                        pos = "mid_block"

                    name = CAPLPatterns.get_variable_name(child, source)
                    if name:
                        symbols.append(
                            SymbolInfo(
                                name=name,
                                symbol_type="variable",
                                line_number=child.start_point[0] + 1,
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
            type_name = ASTWalker.get_text(type_node, source)

            # Check if this type name is a known enum or struct
            kind = self.current_file_types.get(type_name)
            if kind:
                # Double check by looking at the source text before the type name
                text_before = ASTWalker.get_text(m.node, source).split(type_name)[0]
                if kind not in text_before:
                    # Missing keyword!
                    var_name = CAPLPatterns.get_variable_name(m.node, source) or "unknown"

                    symbols.append(
                        SymbolInfo(
                            name=var_name,
                            symbol_type="type_usage_error",
                            line_number=type_node.start_point[0] + 1,
                            signature=ASTWalker.get_text(m.node, source).strip(),
                            context=f"missing_{kind}_keyword",
                        )
                    )
        return symbols

    def _extract_forbidden_syntax(self, root: Node, source: str) -> list[SymbolInfo]:
        symbols = []
        
        # 1. Detection for 'extern' keyword using AST
        for decl in ASTWalker.find_all_by_type(root, "declaration"):
            if CAPLPatterns.has_extern_keyword(decl, source):
                symbols.append(
                    SymbolInfo(
                        name="extern",
                        symbol_type="forbidden_syntax",
                        line_number=decl.start_point[0] + 1,
                        signature=ASTWalker.get_text(decl, source).strip(),
                        scope="forbidden",
                        context="extern_keyword",
                    )
                )

        # 2. Detection for function declarations (forward declarations) using CAPLPatterns
        for decl in ASTWalker.find_all_by_type(root, "declaration"):
            if CAPLPatterns.is_function_declaration(decl):
                name = CAPLPatterns.get_function_name(decl, source) or "unknown"
                symbols.append(
                    SymbolInfo(
                        name=name,
                        symbol_type="forbidden_syntax",
                        line_number=decl.start_point[0] + 1,
                        signature=ASTWalker.get_text(decl, source).strip(),
                        scope="forbidden",
                        context="function_declaration",
                    )
                )

        return symbols

