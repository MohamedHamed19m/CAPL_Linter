from collections.abc import Callable

from tree_sitter import Node


class ASTWalker:
    """Utilities for traversing and searching the CAPL AST"""

    @staticmethod
    def walk(node: Node, callback: Callable[[Node], None]):
        """Perform a depth-first traversal of the AST"""
        callback(node)
        for child in node.children:
            ASTWalker.walk(child, callback)

    @staticmethod
    def find_parent_of_type(node: Node, type_name: str) -> Node | None:
        """Find the first parent node of a specific type"""
        current = node.parent
        while current:
            if current.type == type_name:
                return current
            current = current.parent
        return None

    @staticmethod
    def get_child_of_type(node: Node, type_name: str) -> Node | None:
        """Find the first direct child of a specific type"""
        for child in node.children:
            if child.type == type_name:
                return child
        return None

    @staticmethod
    def find_all_by_type(node: Node, type_name: str) -> list[Node]:
        """Find all descendant nodes of a specific type"""
        results = []

        def check(n):
            if n.type == type_name:
                results.append(n)

        ASTWalker.walk(node, check)
        return results

    @staticmethod
    def get_text(node: Node, source: bytes | str) -> str:
        """Extract the source text for a node."""
        if isinstance(source, str):
            source = source.encode("utf8")
        return source[node.start_byte : node.end_byte].decode("utf8")

    @staticmethod
    def get_children_by_type(node: Node, type_name: str) -> list[Node]:
        """Get all direct children of a specific type."""
        return [child for child in node.children if child.type == type_name]

    @staticmethod
    def find_siblings_of_type(node: Node, type_name: str) -> list[Node]:
        """Find all sibling nodes of a specific type."""
        if not node.parent:
            return []
        return [
            child for child in node.parent.children if child != node and child.type == type_name
        ]

    @staticmethod
    def is_inside_type(node: Node, type_name: str) -> bool:
        """Check if node is inside (descendant of) a specific type."""
        return ASTWalker.find_parent_of_type(node, type_name) is not None

    @staticmethod
    def get_named_children(node: Node) -> list[Node]:
        """Get only named children (excludes punctuation/keywords)."""
        return [child for child in node.children if child.is_named]

    @staticmethod
    def get_node_path(node: Node) -> list[str]:
        """Get path from root to this node (list of node types)."""
        path = []
        current = node
        while current:
            path.append(current.type)
            current = current.parent
        return list(reversed(path))
