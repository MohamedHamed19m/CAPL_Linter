import re
from typing import List, Optional, Dict
from pathlib import Path
from tree_sitter import Node
from capl_tree_sitter.parser import CAPLParser
from capl_tree_sitter.queries import CAPLQueryHelper
from .models import SymbolInfo, TypeDefinition

class SymbolExtractor:
    """Extracts symbols and type definitions from CAPL AST"""

    def __init__(self):
        self.parser = CAPLParser()
        self.query_helper = CAPLQueryHelper()
        self.current_file_types = {}

    def extract_all(self, file_path: Path) -> List[SymbolInfo]:
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

    def _extract_enum_definitions(self, root: Node, source: str) -> List[SymbolInfo]:
        symbols = []
        query = """
            (enum_specifier
              name: (type_identifier) @enum_name
              body: (enumerator_list
                (enumerator
                  name: (identifier) @member_name) @member)*) @enum_def
        """
        matches = self.query_helper.query(query, root)
        for m in matches:
            if "enum_name" in m.captures:
                name_node = m.captures["enum_name"]
                name = source[name_node.start_byte : name_node.end_byte]
                self.current_file_types[name] = "enum"
                
                line = name_node.start_point[0] + 1
                symbols.append(SymbolInfo(
                    name=name,
                    symbol_type="constant",
                    line_number=line,
                    scope="global",
                    context="enum_definition"
                ))
        return symbols

    def _extract_struct_definitions(self, root: Node, source: str) -> List[SymbolInfo]:
        symbols = []
        query = """
            (struct_specifier
              name: (type_identifier) @struct_name
              body: (field_declaration_list)) @struct_def
        """
        matches = self.query_helper.query(query, root)
        for m in matches:
            if "struct_name" in m.captures:
                name_node = m.captures["struct_name"]
                name = source[name_node.start_byte : name_node.end_byte]
                self.current_file_types[name] = "struct"
                
                line = name_node.start_point[0] + 1
                symbols.append(SymbolInfo(
                    name=name,
                    symbol_type="constant",
                    line_number=line,
                    scope="global",
                    context="struct_definition"
                ))
        return symbols

    def _extract_event_handlers(self, root: Node, source: str) -> List[SymbolInfo]:
        symbols = []
        # Simplified query for common CAPL event handlers
        # In tree-sitter-c, these often appear as a labeled statement or similar
        # but CAPL uses keywords 'on message', 'on timer', etc.
        # Here we just look for identifiers following 'on' if we had a proper grammar.
        # Using the original logic based on C grammar:
        lines = source.split('\n')
        for i, line in enumerate(lines):
            match = re.search(r'^\s*on\s+(message|timer|key|signal|start|stop|preStart|preStop|errorFrame|busOff)\s+([^\s{]+)', line)
            if match:
                symbols.append(SymbolInfo(
                    name=match.group(2),
                    symbol_type="event_handler",
                    line_number=i + 1,
                    signature=line.strip(),
                    scope="global",
                    context=match.group(1)
                ))
        return symbols

    def _extract_functions(self, root: Node, source: str) -> List[SymbolInfo]:
        symbols = []
        query = "(function_definition) @func"
        matches = self.query_helper.query(query, root)
        for m in matches:
            func_node = m.node
            # Find the identifier in the declarator
            # This is simplified; real logic is more complex
            symbols.append(SymbolInfo(
                name="unknown_func", # Simplification for now
                symbol_type="function",
                line_number=func_node.start_point[0] + 1,
                signature=source[func_node.start_byte : func_node.end_byte].split('{')[0].strip(),
                scope="global"
            ))
        return symbols

    def _extract_variables_block(self, root: Node, source: str) -> List[SymbolInfo]:
        # Logic to find 'variables {' blocks and extract contents
        return []

    def _extract_global_variables(self, root: Node, source: str) -> List[SymbolInfo]:
        return []

    def _extract_all_local_variables(self, root: Node, source: str) -> List[SymbolInfo]:
        return []

    def _extract_type_usages(self, root: Node, source: str) -> List[SymbolInfo]:
        return []

    def _extract_forbidden_syntax(self, root: Node, source: str) -> List[SymbolInfo]:
        symbols = []
        # Detection for 'extern' and forward declarations
        lines = source.split('\n')
        for i, line in enumerate(lines):
            if 'extern' in line.split('//')[0]:
                symbols.append(SymbolInfo(
                    name="extern",
                    symbol_type="forbidden_syntax",
                    line_number=i+1,
                    signature=line.strip(),
                    scope="forbidden",
                    context="extern_keyword"
                ))
        return symbols