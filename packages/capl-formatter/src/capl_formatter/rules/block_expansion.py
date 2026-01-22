from typing import List
from .base import ASTRule, FormattingContext, Transformation
from ..models import FormatterConfig

class BlockExpansionRule(ASTRule):
    """Ensures content inside blocks is moved to new lines. 
    Also expands single-line struct/enum definitions."""
    
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
            # Handle all block types
            if node.type in ["compound_statement", "variables_block", "field_declaration_list", "enumerator_list"]:
                open_brace = None
                close_brace = None
                for child in node.children:
                    if child.type == "{": open_brace = child
                    if child.type == "}": close_brace = child
                
                # Expand opening brace
                if open_brace:
                    ob_end = open_brace.end_byte
                    if ob_end < len(context.source) and context.source[ob_end] != '\n':
                        # Check what follows
                        line_idx = open_brace.end_point[0]
                        line = context.lines[line_idx]
                        # Text on this line after the brace
                        after = line[open_brace.end_point[1]:].strip()
                        
                        # Only expand if there's actual content (not just a trailing newline or comment)
                        # Actually, if it's not a newline, we WANT a newline.
                        if after != "" and not after.startswith(("//", "/*")):
                            # Skip leading spaces to minimize whitespace mess
                            pos = ob_end
                            while pos < len(context.source) and context.source[pos] in [' ', '\t']:
                                pos += 1
                            
                            transformations.append(Transformation(
                                start_byte=ob_end,
                                end_byte=pos,
                                new_content="\n"
                            ))
                
                # Expand closing brace
                if close_brace:
                    cb_start = close_brace.start_byte
                    if cb_start > 0 and cb_start <= len(context.source) and context.source[cb_start - 1] != '\n':
                        line_idx = close_brace.start_point[0]
                        line = context.lines[line_idx]
                        before = line[:close_brace.start_point[1]].strip()
                        
                        if before != "":
                            pos = cb_start - 1
                            while pos >= 0 and context.source[pos] in [' ', '\t']:
                                pos -= 1
                            
                            transformations.append(Transformation(
                                start_byte=pos + 1,
                                end_byte=cb_start,
                                new_content="\n"
                            ))
            
            # Special handling for struct and enum definitions
            if node.type in ["struct_specifier", "enum_specifier"]:
                for child in node.children:
                    if child.type in ["field_declaration_list", "enumerator_list"]:
                        self._expand_struct_enum_members(child, transformations, context)
                        break

            for child in node.children: 
                traverse(child)

        traverse(context.tree.root_node)
        return transformations
    
    def _expand_struct_enum_members(self, list_node, transformations, context):
        """Expand members of struct or enum onto separate lines."""
        members = [child for child in list_node.children 
                   if child.type in ["field_declaration", "enumerator"]]
        
        if len(members) <= 1:
            return
        
        prev_member = None
        for member in members:
            if prev_member:
                # If two members are on the same line, split them
                if member.start_point[0] == prev_member.end_point[0]:
                    pos = member.start_byte - 1
                    # Scan back past spaces
                    while pos >= 0 and context.source[pos] in [' ', '\t']:
                        pos -= 1
                    
                    # Insert newline if not already there
                    if pos >= 0 and context.source[pos] != '\n':
                        transformations.append(Transformation(
                            start_byte=pos + 1,
                            end_byte=member.start_byte,
                            new_content="\n"
                        ))
            prev_member = member
