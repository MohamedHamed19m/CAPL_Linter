import tree_sitter_c as tsc
from tree_sitter import Language, Node, Query, QueryCursor

from .node_types import NodeMatch


class CAPLQueryHelper:
    """Helper for executing tree-sitter queries on CAPL AST"""

    def __init__(self):
        self.language = Language(tsc.language())

    def query(self, query_str: str, node: Node) -> list[NodeMatch]:
        """Execute a query and return matched nodes with captures"""
        query = Query(self.language, query_str)
        cursor = QueryCursor(query)

        matches = []
        # Note: In newer tree-sitter versions, captures() is preferred
        # but for compatibility we use the match structure
        for match in cursor.matches(node):
            pattern_index = match[0]
            captures = match[1]

            # Simple heuristic: use the first capture as the primary node
            primary_node = list(captures.values())[0][0] if captures else node

            # Flatten captures for easier consumption: {name: node}
            flattened_captures = {name: nodes[0] for name, nodes in captures.items()}

            matches.append(
                NodeMatch(
                    node=primary_node, captures=flattened_captures, pattern_index=pattern_index
                )
            )

        return matches
