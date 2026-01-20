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
                    line_idx = open_brace.end_point[0]
                    line = context.lines[line_idx]
                    after = line[open_brace.end_point[1]:].strip()
                    if after != "" and not after.startswith(("//", "/*")):
                        transformations.append(Transformation(
                            start_byte=open_brace.end_byte,
                            end_byte=open_brace.end_byte,
                            new_content="\n"
                        ))
                
                # Expand closing brace
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
            
            # Special handling for struct and enum definitions
            # Expand: struct Point{int x;int y;} -> multi-line
            if node.type in ["struct_specifier", "enum_specifier"]:
                # Check if it's on a single line
                if node.start_point[0] == node.end_point[0]:
                    # Find the field_declaration_list or enumerator_list
                    for child in node.children:
                        if child.type in ["field_declaration_list", "enumerator_list"]:
                            # Expand children inside the list
                            self._expand_struct_enum_members(child, transformations, context)
                            break

            for child in node.children: 
                traverse(child)

        traverse(context.tree.root_node)
        return transformations
    
    def _expand_struct_enum_members(self, list_node, transformations, context):
        """Expand members of struct or enum onto separate lines."""
        # Find all field_declaration or enumerator nodes
        members = [child for child in list_node.children 
                   if child.type in ["field_declaration", "enumerator"]]
        
        if len(members) <= 1:
            return  # Don't expand single-member structs/enums
        
        # Check if ANY members are on the same line (indicates single-line definition)
        first_line = members[0].start_point[0]
        needs_expansion = any(m.start_point[0] == first_line for m in members[1:])
        
        if not needs_expansion:
            return  # Already multi-line, no changes needed
        
        # Add newlines between ALL members on the same line
        prev_member = None
        for member in members:
            if prev_member:
                # Check if this member is on same line as previous
                if member.start_point[0] == prev_member.end_point[0]:
                    # Insert newline before this member
                    transformations.append(Transformation(
                        start_byte=member.start_byte,
                        end_byte=member.start_byte,
                        new_content="\n"
                    ))
                # Also check if member is on same line as ANY previous member
                elif member.start_point[0] == first_line:
                    # Still on first line, needs splitting
                    transformations.append(Transformation(
                        start_byte=member.start_byte,
                        end_byte=member.start_byte,
                        new_content="\n"
                    ))
            prev_member = member