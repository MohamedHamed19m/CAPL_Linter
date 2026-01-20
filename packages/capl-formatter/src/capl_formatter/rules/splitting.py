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
            if node.type in ["compound_statement", "translation_unit", "variables_block", "case_statement", "default_statement"]:
                prev_child = None
                for child in node.children:
                    # Skip boundary tokens
                    if child.type in ["{", "}", "variables", ":", "case", "default", "else"]:
                        prev_child = child; continue
                    
                    if prev_child:
                        # If two nodes are on the same line
                        if child.start_point[0] == prev_child.end_point[0]:
                            # Don't split labels
                            if prev_child.type in ["case", "default"]:
                                prev_child = child; continue
                            
                            # Split if it's a new statement or declaration
                            is_stmt = child.type.endswith("statement") or child.type == "declaration"
                            prev_is_end = prev_child.type in [";", "}"] or prev_child.type.endswith("statement") or prev_child.type == "declaration"
                            
                            if is_stmt and prev_is_end:
                                # Ensure we don't split } else
                                if not (prev_child.type == "}" and child.type in ["else", "while"]):
                                    transformations.append(Transformation(child.start_byte, child.start_byte, "\n"))
                    
                    prev_child = child

            for child in node.children: traverse(child)

        traverse(context.tree.root_node)
        return transformations