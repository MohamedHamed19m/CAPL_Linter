import re
from typing import List
from .base import ASTRule, FormattingContext, Transformation
from ..models import FormatterConfig

class BraceStyleRule(ASTRule):
    """Enforces K&R brace style."""
    
    def __init__(self, config: FormatterConfig):
        self.config = config

    @property
    def rule_id(self) -> str: return "F003"
    @property
    def name(self) -> str: return "brace-style"

    def analyze(self, context: FormattingContext) -> List[Transformation]:
        if not context.tree or self.config.brace_style != "k&r": return []
        transformations = []
        
        def traverse(node):
            if node.type in ["compound_statement", "variables_block", "struct_specifier", "enum_specifier", "field_declaration_list", "enumerator_list"]:
                open_brace = None
                for child in node.children:
                    if child.type == "{":
                        open_brace = child
                        break
                
                if open_brace:
                    row = open_brace.start_point[0]
                    if row > 0:
                        line_text = context.lines[row]
                        if line_text[:open_brace.start_point[1]].strip() == "":
                            prev_line = context.lines[row - 1].rstrip()
                            # Use char index for character-based engine
                            line_starts = [0]
                            for i in range(len(context.lines)-1):
                                line_starts.append(line_starts[i] + len(context.lines[i]))
                            
                            start_char = line_starts[row-1] + len(prev_line)
                            transformations.append(Transformation(
                                start_byte=start_char,
                                end_byte=open_brace.start_byte,
                                new_content=" "
                            ))
            for child in node.children: traverse(child)

        traverse(context.tree.root_node)
        return transformations

class SpacingRule(ASTRule):
    """AST-based spacing rule for operators, keywords, and cleanup."""
    
    def __init__(self, config: FormatterConfig):
        self.config = config

    @property
    def rule_id(self) -> str: return "F004"
    @property
    def name(self) -> str: return "spacing"

    def analyze(self, context: FormattingContext) -> List[Transformation]:
        if not context.tree: return []
        transformations = []
        
        def add_space(node_a, node_b):
            if node_a.end_byte == node_b.start_byte:
                transformations.append(Transformation(node_a.end_byte, node_a.end_byte, " "))

        def traverse(node):
            if node.type == "binary_expression" and len(node.children) >= 3:
                left, op, right = node.children[0], node.children[1], node.children[2]
                if op.type not in [".", "->"]:
                    add_space(left, op)
                    add_space(op, right)

            if node.type in ["assignment_expression", "init_declarator"]:
                eq = None
                for child in node.children:
                    if child.type == "=": eq = child; break
                if eq:
                    idx = node.children.index(eq)
                    if idx > 0: add_space(node.children[idx-1], eq)
                    if idx < len(node.children) - 1: add_space(eq, node.children[idx+1])

            if node.type in ["if_statement", "for_statement", "while_statement", "switch_statement"]:
                keyword = node.children[0]
                if len(node.children) > 1:
                    add_space(keyword, node.children[1])

            if node.type == "{":
                if node.start_byte > 0:
                    char_before = context.source[node.start_byte - 1]
                    if char_before not in [" ", "\t", "(", "{", "\n"]:
                        transformations.append(Transformation(node.start_byte, node.start_byte, " "))

            if node.type == "else":
                if node.start_byte > 0 and context.source[node.start_byte-1] == "}":
                    transformations.append(Transformation(node.start_byte, node.start_byte, " "))

            if node.type in [".", ",", ";"]:
                parent = node.parent
                if parent:
                    try:
                        idx = parent.children.index(node)
                        if idx < len(parent.children) - 1:
                            next_node = parent.children[idx+1]
                            if next_node.type not in [")", "}", ";", ","]:
                                add_space(node, next_node)
                    except ValueError: pass

            for child in node.children: traverse(child)

        traverse(context.tree.root_node)
        
        line_starts = [0]
        for i in range(len(context.lines)-1):
            line_starts.append(line_starts[i] + len(context.lines[i]))

        for i, line in enumerate(context.lines):
            stripped = line.lstrip()
            if not stripped: continue
            indent_len = len(line) - len(stripped)
            
            new_s = re.sub(r'\s*\.\s*', '.', stripped)
            new_s = re.sub(r'(\w+)\s*(\+\+|--)', r'\1\2', new_s)
            new_s = re.sub(r'[ \t]{2,}', ' ', new_s)
            
            if new_s != stripped.rstrip('\n\r'):
                transformations.append(Transformation(
                    line_starts[i] + indent_len, 
                    line_starts[i] + len(line.rstrip('\n\r')),
                    new_s
                ))

        return transformations
