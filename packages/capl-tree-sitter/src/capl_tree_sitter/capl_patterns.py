"""CAPL-specific AST pattern recognition."""

from tree_sitter import Node
from .ast_walker import ASTWalker


class CAPLPatterns:
    """Recognize CAPL-specific patterns in the AST."""

    # CAPL special types that REQUIRE pointer syntax
    POINTER_REQUIRED_TYPES = {
        "ethernetpacket",
        "someipmessage",
        "someiptpmessage",
        "doipmessage",
        "linmessage",
        "canmessage",
    }

    # CAPL types where '&' (reference) is allowed
    REFERENCE_ALLOWED_TYPES = {
        "byte",
        "word",
        "dword",
        "qword",
        "int",
        "long",
        "int64",
        "float",
        "double",
    }

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
        """Deprecated: Use analyze_pointer_usage() for better accuracy.

        This is a simplified check that may have false positives.
        """
        text = ASTWalker.get_text(node, source)

        # Check for arrow operator (always forbidden)
        if "->" in text:
            return True

        # Check for asterisk (might be pointer or multiplication)
        # This is not accurate - use has_forbidden_pointer_parameter instead
        if "*" in text:
            # Simple heuristic: if asterisk follows a type name, likely pointer
            if " *" in text or "*" in text.split()[0]:
                return True

        return False

    @staticmethod
    def get_parameter_type(param_node: Node, source: bytes | str) -> str | None:
        """Extract the type name from a parameter declaration.

        Examples:
            struct Data data_obj  -> "Data"
            byte &ref             -> "byte"
            ethernetpacket * pkt  -> "ethernetpacket"
        """
        if param_node.type != "parameter_declaration":
            return None

        # Check for struct specifier
        struct = ASTWalker.get_child_of_type(param_node, "struct_specifier")
        if struct:
            type_id = ASTWalker.get_child_of_type(struct, "type_identifier")
            if type_id:
                return ASTWalker.get_text(type_id, source)

        # Check for type specifier (primitives and special types)
        type_spec = ASTWalker.get_child_of_type(param_node, "type_specifier")
        if type_spec:
            return ASTWalker.get_text(type_spec, source)

        # Fallback: get first word from parameter text
        param_text = ASTWalker.get_text(param_node, source).strip()
        parts = param_text.split()
        if parts:
            # Skip 'struct' keyword if present
            if parts[0] == "struct" and len(parts) > 1:
                return parts[1].rstrip("*&")
            return parts[0].rstrip("*&")

        return None

    @staticmethod
    def is_pointer_required_type(type_name: str) -> bool:
        """Check if this type REQUIRES pointer syntax in CAPL.

        Types like ethernetpacket, someipMessage MUST use pointer syntax.
        """
        if not type_name:
            return False
        return type_name.lower() in CAPLPatterns.POINTER_REQUIRED_TYPES

    @staticmethod
    def is_reference_allowed_type(type_name: str) -> bool:
        """Check if this type allows '&' reference syntax."""
        if not type_name:
            return False
        return type_name.lower() in CAPLPatterns.REFERENCE_ALLOWED_TYPES

    @staticmethod
    def has_forbidden_pointer_parameter(func_node: Node, source: bytes | str) -> list[dict]:
        """Check if function has forbidden pointer parameters.

        Returns list of violations with details.

        Rules:
            ✅ struct Data data           - OK (implicit pass-by-reference)
            ✅ byte &ref                  - OK (explicit reference for primitives)
            ✅ ethernetpacket * pkt       - OK (required for special types)
            ❌ struct Data* ptr           - ERROR (forbidden pointer syntax)
        """
        violations = []

        if func_node.type != "function_definition":
            return violations

        # Get function declarator
        declarator = ASTWalker.get_child_of_type(func_node, "function_declarator")
        if not declarator:
            return violations

        # Get parameter list
        params = ASTWalker.get_child_of_type(declarator, "parameter_list")
        if not params:
            return violations

        # Check each parameter
        for param in ASTWalker.get_named_children(params):
            if param.type != "parameter_declaration":
                continue

            param_text = ASTWalker.get_text(param, source).strip()
            type_name = CAPLPatterns.get_parameter_type(param, source)

            # Check for pointer declarator (has asterisk)
            has_pointer = ASTWalker.get_child_of_type(param, "pointer_declarator") is not None
            has_asterisk = "*" in param_text

            # Check for reference (has ampersand)
            has_reference = "&" in param_text

            if has_pointer or has_asterisk:
                # Pointer syntax detected
                if CAPLPatterns.is_pointer_required_type(type_name):
                    # This type REQUIRES pointer syntax - OK
                    continue
                else:
                    # Regular struct/type with pointer syntax - FORBIDDEN
                    violations.append(
                        {
                            "type": "forbidden_pointer_param",
                            "param_text": param_text,
                            "type_name": type_name,
                            "line": param.start_point[0] + 1,
                            "column": param.start_point[1],
                            "message": f"Pointer parameter '{param_text}' is forbidden. "
                            f"CAPL passes structs by reference implicitly.",
                        }
                    )

            if has_reference:
                # Reference syntax detected
                if not CAPLPatterns.is_reference_allowed_type(type_name):
                    # Reference on non-primitive type - might be error
                    # (Generally only primitives use '&' in CAPL)
                    violations.append(
                        {
                            "type": "invalid_reference_param",
                            "param_text": param_text,
                            "type_name": type_name,
                            "line": param.start_point[0] + 1,
                            "column": param.start_point[1],
                            "message": f"Reference parameter '&' should only be used with primitive types, not '{type_name}'.",
                        }
                    )

        return violations

    @staticmethod
    def has_arrow_operator_usage(node: Node, source: bytes | str) -> list[dict]:
        """Detect arrow operator (->) usage in code.

        Rules:
            ✅ struct Data obj; obj.field     - OK (dot operator for structs)
            ✅ ethernetpacket * p; p.field    - OK (even though pointer, use dot)
            ❌ data_ptr->field                - ERROR (arrow not supported in CAPL)

        Note: CAPL does NOT support arrow operator, even for pointer types.
        Even ethernetpacket* uses DOT notation (p.udp.IsAvailable()).
        """
        violations = []

        # Find all field_expression nodes (these represent a.b or a->b)
        field_exprs = ASTWalker.find_all_by_type(node, "field_expression")

        for expr in field_exprs:
            expr_text = ASTWalker.get_text(expr, source)

            if "->" in expr_text:
                violations.append(
                    {
                        "type": "arrow_operator_usage",
                        "expression": expr_text,
                        "line": expr.start_point[0] + 1,
                        "column": expr.start_point[1],
                        "message": f"Arrow operator '->' is not supported in CAPL. Use dot notation instead.",
                    }
                )

        return violations

    @staticmethod
    def analyze_pointer_usage(func_node: Node, source: bytes | str) -> dict:
        """Comprehensive pointer usage analysis for a function.

        Returns dict with:
            - forbidden_pointers: list of forbidden pointer parameters
            - arrow_operators: list of arrow operator usages
            - has_errors: bool
        """
        result = {
            "forbidden_pointers": [],
            "arrow_operators": [],
            "has_errors": False,
        }

        # Check parameters
        result["forbidden_pointers"] = CAPLPatterns.has_forbidden_pointer_parameter(
            func_node, source
        )

        # Check arrow operators in function body
        body = ASTWalker.get_child_of_type(func_node, "compound_statement")
        if body:
            result["arrow_operators"] = CAPLPatterns.has_arrow_operator_usage(body, source)

        result["has_errors"] = (
            len(result["forbidden_pointers"]) > 0 or len(result["arrow_operators"]) > 0
        )

        return result