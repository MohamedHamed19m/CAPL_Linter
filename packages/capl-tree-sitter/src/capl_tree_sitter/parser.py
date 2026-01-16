import tree_sitter_c as tsc
from tree_sitter import Language, Parser, Tree
from pathlib import Path
from typing import Union, Optional
from .node_types import ParseResult


class CAPLParser:
    """Core CAPL parser using tree-sitter-c"""

    def __init__(self):
        self.language = Language(tsc.language())
        self.parser = Parser(self.language)

    def parse_file(self, path: Union[str, Path]) -> ParseResult:
        """Parse a CAPL file from disk"""
        path = Path(path)
        with open(path, "rb") as f:
            source_code = f.read()

        return self.parse_string(source_code)

    def parse_string(self, source: Union[str, bytes]) -> ParseResult:
        """Parse CAPL source code from a string or bytes"""
        if isinstance(source, str):
            source_bytes = source.encode("utf8")
        else:
            source_bytes = source
            source = source.decode("utf8")

        tree = self.parser.parse(source_bytes)
        errors = self._check_for_errors(tree.root_node)

        return ParseResult(tree=tree, source=source, errors=errors)

    def _check_for_errors(self, node) -> list[str]:
        """Check for syntax errors in the AST"""
        errors = []
        if node.type == "ERROR":
            errors.append(f"Syntax error at line {node.start_point[0] + 1}")

        for child in node.children:
            errors.extend(self._check_for_errors(child))

        return errors
