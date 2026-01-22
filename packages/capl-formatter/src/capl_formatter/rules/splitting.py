from typing import List
from .base import ASTRule, FormattingContext, Transformation
from ..models import FormatterConfig

class StatementSplitRule(ASTRule):
    """AST-based statement splitting rule for semicolon-separated lines."""
    
    def __init__(self, config: FormatterConfig):
        self.config = config

    @property
    def rule_id(self) -> str: return "F006"
    @property
    def name(self) -> str: return "statement-splitting"

    def analyze(self, context: FormattingContext) -> List[Transformation]:
        if not context.tree: return []
        transformations = []
        
        def traverse(node):
            # Skip struct/enum member lists and specifiers entirely
            if node.type in ["field_declaration_list", "enumerator_list", "struct_specifier", "enum_specifier"]:
                return
            
            if node.type in ["compound_statement", "translation_unit", "variables_block", "case_statement", "default_statement"]:
                # Identify lines with errors to avoid mangling them
                error_lines = {c.start_point[0] for c in node.children if c.type == "ERROR"}
                error_lines.update({c.end_point[0] for c in node.children if c.type == "ERROR"})

                prev_child = None
                for child in node.children:
                    # Skip boundary tokens
                    if child.type in ["{", "}", "variables", ":", "case", "default", "else"]:
                        prev_child = child; continue
                    
                    # Skip struct/enum specifiers and their members as children
                    if child.type in ["struct_specifier", "enum_specifier", "field_declaration", "enumerator"]:
                        prev_child = child; continue
                    
                    if prev_child and prev_child.type not in ["{", "variables", ":", "else"]:
                        # Skip splitting if this line has errors
                        if child.start_point[0] in error_lines:
                            prev_child = child; continue

                        # If two nodes are on the same line
                        if child.start_point[0] == prev_child.end_point[0]:
                            # Don't split labels
                            if prev_child.type not in ["case", "default"]:
                                # Split if it's a new statement or declaration
                                is_stmt = child.type.endswith("statement") or child.type == "declaration"
                                prev_is_end = prev_child.type in [";", "}", "comment"] or prev_child.type.endswith("statement") or prev_child.type == "declaration"
                                
                                if is_stmt and prev_is_end:
                                    # Ensure we don't split } else
                                    if not (prev_child.type == "}" and child.type in ["else", "while"]):
                                        # Skip spaces/newlines before the new statement
                                        pos = child.start_byte - 1
                                        while pos >= 0 and context.source[pos] in [' ', '\t', '\n', '\r']:
                                            pos -= 1
                                        transformations.append(Transformation(
                                            start_byte=pos + 1, 
                                            end_byte=child.start_byte, 
                                            new_content="\n"
                                        ))
                    
                    prev_child = child

            for child in node.children: traverse(child)

        traverse(context.tree.root_node)
        return transformations