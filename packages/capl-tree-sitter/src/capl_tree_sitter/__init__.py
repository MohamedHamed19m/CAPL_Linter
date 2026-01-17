"""CAPL parser using tree-sitter."""

from .ast_walker import ASTWalker
from .capl_patterns import CAPLPatterns
from .node_types import ASTNode, NodeMatch, ParseResult
from .parser import CAPLParser
from .queries import CAPLQueryHelper

__all__ = [
    "CAPLParser",
    "CAPLQueryHelper",
    "ASTWalker",
    "CAPLPatterns",
    "ASTNode",
    "NodeMatch",
    "ParseResult",
]


def hello() -> str:
    return "Hello from capl-tree-sitter!"