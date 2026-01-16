from tree_sitter import Node
from typing import Callable, Optional, List


class ASTWalker:
    """Utilities for traversing and searching the CAPL AST"""

    @staticmethod
    def walk(node: Node, callback: Callable[[Node], None]):
        """Perform a depth-first traversal of the AST"""
        callback(node)
        for child in node.children:
            ASTWalker.walk(child, callback)

    @staticmethod
    def find_parent_of_type(node: Node, type_name: str) -> Optional[Node]:
        """Find the first parent node of a specific type"""
        current = node.parent
        while current:
            if current.type == type_name:
                return current
            current = current.parent
        return None

    @staticmethod
    def get_child_of_type(node: Node, type_name: str) -> Optional[Node]:
        """Find the first direct child of a specific type"""
        for child in node.children:
            if child.type == type_name:
                return child
        return None

    @staticmethod
    def find_all_by_type(node: Node, type_name: str) -> List[Node]:
        """Find all descendant nodes of a specific type"""
        results = []

        def check(n):
            if n.type == type_name:
                results.append(n)

        ASTWalker.walk(node, check)
        return results
