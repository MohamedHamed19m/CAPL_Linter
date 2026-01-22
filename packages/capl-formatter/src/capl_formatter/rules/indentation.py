import re
from typing import List, Dict
from .base import ASTRule, FormattingContext, Transformation
from ..models import FormatterConfig

class IndentationRule(ASTRule):
    """AST-based indentation rule with proper switch case handling."""
    
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
        ignored_lines = set()
        
        # Initialize with a value indicating "unset" (e.g., -1)
        # We want to find the MINIMUM depth for each line.
        for i in range(len(context.lines)):
            line_depths[i] = -1

        def traverse(node, current_depth):
            start_row = node.start_point[0]
            end_row = node.end_point[0]
            
            # Skip indentation for lines inside multi-line comments/strings (except start)
            if node.type in ['comment', 'string_literal']:
                if end_row > start_row:
                    for r in range(start_row + 1, end_row + 1):
                        ignored_lines.add(r)
            
            is_indenter = node.type in [
                "compound_statement", "variables_block", 
                "field_declaration_list", "enumerator_list"
            ]
            
            # Record depth for the node's start line
            # We want the shallowest node that starts on this line to dictate indentation
            if line_depths[start_row] == -1 or current_depth < line_depths[start_row]:
                line_depths[start_row] = current_depth
            
            # Special handling for switch statements
            if node.type == "switch_statement":
                # The switch body (compound_statement) children get processed normally
                # but we need to handle case/default statements specially
                for child in node.children:
                    if child.type == "compound_statement":
                        # Process the compound statement at current depth
                        traverse(child, current_depth)
                        # Now handle case/default statements inside
                        for case_child in child.children:
                            if case_child.type in ["case_statement", "default_statement"]:
                                # Case label at switch body depth + 1
                                case_depth = current_depth + 1
                                
                                # Find the colon and statements after it
                                colon_found = False
                                for stmt_child in case_child.children:
                                    if stmt_child.type == ":":
                                        colon_found = True
                                        # Colon line stays at case_depth
                                        if line_depths[stmt_child.start_point[0]] == -1 or case_depth < line_depths[stmt_child.start_point[0]]:
                                            line_depths[stmt_child.start_point[0]] = case_depth
                                    elif colon_found and stmt_child.type not in ["case", "default", "{", "}"]:
                                        # Statements after colon are indented one more level
                                        stmt_depth = case_depth + 1
                                        for row in range(stmt_child.start_point[0], stmt_child.end_point[0] + 1):
                                            if line_depths[row] == -1 or stmt_depth < line_depths[row]:
                                                line_depths[row] = stmt_depth
                    else:
                        traverse(child, current_depth)
                return  # Don't process children again below
            
            # Handle case/default statements when not inside switch context
            if node.type in ["case_statement", "default_statement"]:
                # Find colon and indent statements after it
                colon_idx = None
                for i, child in enumerate(node.children):
                    if child.type == ":":
                        colon_idx = i
                        break
                
                if colon_idx is not None:
                    # Case label itself at current depth
                    if line_depths[start_row] == -1 or current_depth < line_depths[start_row]:
                        line_depths[start_row] = current_depth
                    
                    # Statements after colon at current_depth + 1
                    for child in node.children[colon_idx + 1:]:
                        if child.type not in [":", "case", "default"]:
                            for row in range(child.start_point[0], child.end_point[0] + 1):
                                if line_depths[row] == -1 or (current_depth + 1) < line_depths[row]:
                                    line_depths[row] = current_depth + 1
                return  # Don't process children normally
            
            # Normal indentation logic for other nodes
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
                        if line_depths[child.start_point[0]] == -1 or current_depth < line_depths[child.start_point[0]]:
                            line_depths[child.start_point[0]] = current_depth

        traverse(context.tree.root_node, 0)
        
        line_starts = [0]
        for i in range(len(context.lines)-1):
            line_starts.append(line_starts[i] + len(context.lines[i]))

        for i, line in enumerate(context.lines):
            if i in ignored_lines: continue
            if not line.strip(): continue
            # If line_depths[i] is still -1, default to 0 (or keep existing? 0 is safer)
            depth = max(0, line_depths.get(i, 0))
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