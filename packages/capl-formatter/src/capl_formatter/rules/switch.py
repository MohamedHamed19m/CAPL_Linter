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
                    if child.type == ":": colon = child; break
                
                if colon:
                    all_children = node.children
                    try:
                        idx = all_children.index(colon)
                        if idx < len(all_children) - 1:
                            next_child = all_children[idx+1]
                            # If content starts on same line as label colon
                            if next_child.start_point[0] == colon.end_point[0]:
                                transformations.append(Transformation(next_child.start_byte, next_child.start_byte, "\n"))
                    except ValueError: pass
            for child in node.children: traverse(child)

        traverse(context.tree.root_node)
        return transformations
