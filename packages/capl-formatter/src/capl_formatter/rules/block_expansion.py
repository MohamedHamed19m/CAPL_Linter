from typing import List
from .base import ASTRule, FormattingContext, Transformation
from ..models import FormatterConfig

class BlockExpansionRule(ASTRule):
    """Ensures content inside blocks is moved to new lines."""
    
    def __init__(self, config: FormatterConfig):
        self.config = config

    @property
    def rule_id(self) -> str: return "F005"
    @property
    def name(self) -> str: return "block-expansion"

    def analyze(self, context: FormattingContext) -> List[Transformation]:
        if not context.tree: return []
        transformations = []
        
        def traverse(node):
            if node.type in ["compound_statement", "variables_block", "field_declaration_list", "enumerator_list"]:
                open_brace = None
                close_brace = None
                for child in node.children:
                    if child.type == "{": open_brace = child
                    if child.type == "}": close_brace = child
                
                if open_brace:
                    line_idx = open_brace.end_point[0]
                    line = context.lines[line_idx]
                    after = line[open_brace.end_point[1]:].strip()
                    if after != "" and not after.startswith(("//", "/*")):
                        # Check if next line is already a newline? 
                        # No, if it's on the same line, we insert ONE newline.
                        transformations.append(Transformation(
                            start_byte=open_brace.end_byte,
                            end_byte=open_brace.end_byte,
                            new_content="\n"
                        ))
                
                if close_brace:
                    line_idx = close_brace.start_point[0]
                    line = context.lines[line_idx]
                    before = line[:close_brace.start_point[1]].strip()
                    if before != "":
                        transformations.append(Transformation(
                            start_byte=close_brace.start_byte,
                            end_byte=close_brace.start_byte,
                            new_content="\n"
                        ))

            for child in node.children: traverse(child)

        traverse(context.tree.root_node)
        return transformations