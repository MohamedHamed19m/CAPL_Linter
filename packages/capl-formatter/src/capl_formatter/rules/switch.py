from typing import List
from .base import ASTRule, FormattingContext, Transformation
from ..models import FormatterConfig

class SwitchNormalizationRule(ASTRule):
    """Ensures content after case labels is on a new line."""
    
    def __init__(self, config: FormatterConfig):
        self.config = config

    @property
    def rule_id(self) -> str: return "F007"
    @property
    def name(self) -> str: return "switch-normalization"

    def analyze(self, context: FormattingContext) -> List[Transformation]:
        if not context.tree: return []
        transformations = []
        
        def traverse(node):
            if node.type in ["case_statement", "default_statement"]:
                # Find colon
                colon = None
                for child in node.children:
                    if child.type == ":": 
                        colon = child
                        break
                
                if colon:
                    all_children = node.children
                    try:
                        idx = all_children.index(colon)
                        if idx < len(all_children) - 1:
                            next_child = all_children[idx + 1]
                            
                            # Skip if next child is already on a new line
                            if next_child.start_point[0] == colon.end_point[0]:
                                # Content on same line as colon - need to split
                                # Exception: if next_child is a comment, keep it inline
                                if next_child.type not in ["comment", "line_comment"]:
                                    transformations.append(
                                        Transformation(
                                            start_byte=next_child.start_byte, 
                                            end_byte=next_child.start_byte, 
                                            new_content="\n"
                                        )
                                    )
                    except ValueError: 
                        pass
                        
            for child in node.children: 
                traverse(child)

        traverse(context.tree.root_node)
        return transformations