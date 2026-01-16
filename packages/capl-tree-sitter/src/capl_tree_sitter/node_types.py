from dataclasses import dataclass
from typing import Any, List, Optional
from tree_sitter import Tree, Node

@dataclass
class ASTNode:
    """Represents a simplified AST node for CAPL analysis"""
    type: str
    start_line: int
    end_line: int
    text: str
    parent: Optional['ASTNode'] = None
    original_node: Optional[Node] = None

@dataclass
class ParseResult:
    """Result of a tree-sitter parse operation"""
    tree: Tree
    source: str
    errors: List[str]

@dataclass
class NodeMatch:
    """Result of a tree-sitter query match"""
    node: Node
    captures: dict[str, Node]
    pattern_index: int
