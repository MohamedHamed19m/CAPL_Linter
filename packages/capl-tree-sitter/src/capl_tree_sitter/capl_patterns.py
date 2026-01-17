"""CAPL-specific AST pattern recognition."""

from tree_sitter import Node
from .ast_walker import ASTWalker


class CAPLPatterns:
    """Recognize CAPL-specific patterns in the AST."""

    @staticmethod
    def is_event_handler(node: Node, source: bytes | str) -> bool:
        """Check if a function is a CAPL event handler (starts with 'on').

        Examples: on start, on key, on timer, on message, etc.
        """
        if node.type != "function_definition":
            return False

        # Check if any direct child has text 'on' (covers many tree-sitter-c edge cases)
        for child in node.children:
            if ASTWalker.get_text(child, source) == "on":
                return True

        # Fallback 1: Get the function name via declarator
        declarator = ASTWalker.get_child_of_type(node, "function_declarator")
        if declarator:
            name_node = ASTWalker.get_child_of_type(declarator, "identifier")
            if name_node:
                name = ASTWalker.get_text(name_node, source)
                if name.startswith("on"):
                    return True

        # Fallback 2: Direct identifier (like on start { })
        name_node = ASTWalker.get_child_of_type(node, "identifier")
        if name_node:
            name = ASTWalker.get_text(name_node, source)
            if name.startswith("on"):
                return True

        return False

    @staticmethod
    def is_inside_variables_block(node: Node, source: bytes | str) -> bool:
        """Check if a node is inside a 'variables {}' block.

        CAPL uses variables {} as a keyword-like construct, but tree-sitter
        sees it as a compound statement with 'variables' identifier.
        """
        # Look for compound_statement
        block = ASTWalker.find_parent_of_type(node, "compound_statement")
        if not block or not block.parent:
            return False

        # Check siblings of the block for 'variables'
        siblings = block.parent.children
        try:
            block_index = siblings.index(block)
        except ValueError:
            return False

        # Check if there's 'variables' text in siblings before this block
        for i in range(max(0, block_index - 3), block_index):
            if "variables" in ASTWalker.get_text(siblings[i], source):
                return True

        return False

    @staticmethod
    def is_global_scope(node: Node) -> bool:
        """Check if a node is at global scope (not inside any function)."""
        return ASTWalker.find_parent_of_type(node, "function_definition") is None

    @staticmethod
    def is_timer_declaration(node: Node, source: bytes | str) -> bool:
        """Check if this is a timer declaration."""
        if node.type != "declaration":
            return False

        # Check type_specifier OR type_identifier
        type_node = ASTWalker.get_child_of_type(node, "type_specifier") or ASTWalker.get_child_of_type(
            node, "type_identifier"
        )

        if not type_node:
            return False

        type_text = ASTWalker.get_text(type_node, source)
        return type_text in ["timer", "msTimer"]

    @staticmethod
    def is_message_declaration(node: Node, source: bytes | str) -> bool:
        """Check if this is a message/frame declaration."""
        if node.type != "declaration":
            return False

        # Option 1: struct_specifier with name 'message' or 'frame'
        struct = ASTWalker.get_child_of_type(node, "struct_specifier")
        if struct:
            name_node = ASTWalker.get_child_of_type(struct, "type_identifier")
            if name_node:
                name = ASTWalker.get_text(name_node, source)
                if name in ["message", "frame"]:
                    return True

        # Option 2: direct type_identifier/specifier
        type_node = ASTWalker.get_child_of_type(node, "type_specifier") or ASTWalker.get_child_of_type(
            node, "type_identifier"
        )
        if type_node:
            name = ASTWalker.get_text(type_node, source)
            if name in ["message", "frame"]:
                return True

        return False

    @staticmethod
    def get_function_name(func_node: Node, source: bytes | str) -> str | None:
        """Extract function name from a function_definition node."""
        if func_node.type != "function_definition":
            return None

        # Try function_declarator
        declarator = ASTWalker.get_child_of_type(func_node, "function_declarator")
        if declarator:
            name_node = ASTWalker.get_child_of_type(declarator, "identifier")
            if name_node:
                return ASTWalker.get_text(name_node, source)

        # Try direct identifier
        name_node = ASTWalker.get_child_of_type(func_node, "identifier")
        if name_node:
            return ASTWalker.get_text(name_node, source)

        return None

    @staticmethod
    def get_variable_name(var_node: Node, source: bytes | str) -> str | None:
        """Extract variable name from a declaration node."""
        if var_node.type != "declaration":
            return None

        # Try init_declarator first
        declarator = ASTWalker.get_child_of_type(var_node, "init_declarator")
        if declarator:
            name_node = ASTWalker.get_child_of_type(declarator, "identifier")
        else:
            # Try direct identifier
            name_node = ASTWalker.get_child_of_type(var_node, "identifier")

        if not name_node:
            return None

        return ASTWalker.get_text(name_node, source)

    @staticmethod
    def has_extern_keyword(node: Node, source: bytes | str) -> bool:
        """Check if a declaration has 'extern' keyword."""
        storage_class = ASTWalker.get_child_of_type(node, "storage_class_specifier")
        if not storage_class:
            return False

        text = ASTWalker.get_text(storage_class, source)
        return text == "extern"

    @staticmethod
    def is_function_declaration(node: Node) -> bool:
        """Check if this is a function prototype (no body)."""
        if node.type != "declaration":
            return False

        # Has function_declarator but no compound_statement
        func_declarator = ASTWalker.get_child_of_type(node, "function_declarator")
        body = ASTWalker.get_child_of_type(node, "compound_statement")

        return func_declarator is not None and body is None

    @staticmethod
    def get_type_name(decl_node: Node, source: bytes | str) -> str | None:
        """Extract type name from a declaration."""
        if decl_node.type != "declaration":
            return None

        # Check for struct_specifier
        struct = ASTWalker.get_child_of_type(decl_node, "struct_specifier")
        if struct:
            name_node = ASTWalker.get_child_of_type(struct, "type_identifier")
            if name_node:
                return ASTWalker.get_text(name_node, source)

        # Check for enum_specifier
        enum = ASTWalker.get_child_of_type(decl_node, "enum_specifier")
        if enum:
            name_node = ASTWalker.get_child_of_type(enum, "identifier")
            if name_node:
                return ASTWalker.get_text(name_node, source)

        # Check for type_specifier OR type_identifier
        type_node = ASTWalker.get_child_of_type(decl_node, "type_specifier") or ASTWalker.get_child_of_type(
            decl_node, "type_identifier"
        )
        if type_node:
            return ASTWalker.get_text(type_node, source)

        return None

    @staticmethod
    def is_pointer_usage(node: Node, source: bytes | str) -> bool:
        """Check if node contains pointer syntax (* or ->)."""
        text = ASTWalker.get_text(node, source)
        return "->" in text or "*" in text