import re
from typing import List, Dict
from .base import ASTRule, FormattingContext, Transformation
from ..models import FormatterConfig

class IndentationRule(ASTRule):
    """AST-based indentation rule."""
    
    def __init__(self, config: FormatterConfig):
        self.config = config

    @property
    def rule_id(self) -> str: return "F002"
    @property
    def name(self) -> str: return "indentation"

    def analyze(self, context: FormattingContext) -> List[Transformation]:
        if not context.tree: return []
        transformations = []
        indent_size = self.config.indent_size
        line_depths: Dict[int, int] = {}
        
        for i in range(len(context.lines)):
            line_depths[i] = 0

        def traverse(node, current_depth):
            start_row = node.start_point[0]
            end_row = node.end_point[0]
            
            is_indenter = node.type in [
                "compound_statement", "variables_block", "struct_specifier", 
                "enum_specifier", "field_declaration_list", "enumerator_list"
            ]
            
            # Record depth for the node's start line
            # Overwrite if current_depth is deeper
            if start_row not in line_depths or current_depth > line_depths[start_row]:
                line_depths[start_row] = current_depth
            
            # Record depth for lines covered by children
            new_depth = current_depth + 1 if is_indenter else current_depth
            
            for child in node.children:
                # Braces themselves stay at current_depth
                if child.type in ["{", "}", "variables", "struct", "enum"]:
                    traverse(child, current_depth)
                else:
                    traverse(child, new_depth)
                    
            # Post-order: ensure closing brace is at outer depth
            if is_indenter:
                for child in node.children:
                    if child.type == "}":
                        line_depths[child.start_point[0]] = current_depth

        traverse(context.tree.root_node, 0)
        
        line_starts = [0]
        for i in range(len(context.lines)-1):
            line_starts.append(line_starts[i] + len(context.lines[i]))

        for i, line in enumerate(context.lines):
            if not line.strip(): continue
            depth = line_depths.get(i, 0)
            target_indent = " " * (depth * indent_size)
            match = re.match(r'^([ \t]*)', line)
            current_ws = match.group(1) if match else ""
            if current_ws != target_indent:
                start_char = line_starts[i]
                transformations.append(Transformation(
                    start_byte=start_char,
                    end_byte=start_char + len(current_ws),
                    new_content=target_indent
                ))
        return transformations
