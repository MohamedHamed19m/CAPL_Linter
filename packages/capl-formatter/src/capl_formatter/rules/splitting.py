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
                    if child.type in ["{", "}", "variables", ":", "case", "default", "else"]:
                        prev_child = child; continue
                    
                    if prev_child and prev_child.type not in ["{", "variables", ":", "else"]:
                        if child.start_point[0] == prev_child.end_point[0]:
                            if prev_child.type not in ["case", "default"]:
                                is_stmt = child.type.endswith("statement") or child.type == "declaration"
                                prev_is_end = prev_child.type in [";", "}"] or prev_child.type.endswith("statement") or prev_child.type == "declaration"
                                
                                if is_stmt and prev_is_end:
                                    if not (prev_child.type == "}" and child.type in ["else", "while"]):
                                        # Skip spaces before the new statement
                                        pos = child.start_byte - 1
                                        while pos >= 0 and context.source[pos] in [' ', '\t']:
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