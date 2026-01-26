import re

from ..models import FormatterConfig
from .base import ASTRule, FormattingContext, Transformation


class BraceStyleRule(ASTRule):
    """Enforces K&R brace style."""

    def __init__(self, config: FormatterConfig):
        self.config = config

    @property
    def rule_id(self) -> str:
        return "F003"

    @property
    def name(self) -> str:
        return "brace-style"

    def analyze(self, context: FormattingContext) -> list[Transformation]:
        if not context.tree or self.config.brace_style != "k&r":
            return []
        transformations = []

        def traverse(node):
            if node.type in [
                "compound_statement",
                "variables_block",
                "struct_specifier",
                "enum_specifier",
                "field_declaration_list",
                "enumerator_list",
            ]:
                open_brace = None
                for child in node.children:
                    if child.type == "{":
                        open_brace = child
                        break

                if open_brace:
                    row = open_brace.start_point[0]
                    if row > 0:
                        line_text = context.lines[row]
                        if line_text[: open_brace.start_point[1]].strip() == "":
                            prev_line = context.lines[row - 1].rstrip()
                            line_starts = [0]
                            for i in range(len(context.lines) - 1):
                                line_starts.append(line_starts[i] + len(context.lines[i]))

                            start_char = line_starts[row - 1] + len(prev_line)
                            transformations.append(
                                Transformation(
                                    start_byte=start_char,
                                    end_byte=open_brace.start_byte,
                                    new_content=" ",
                                )
                            )
            for child in node.children:
                traverse(child)

        traverse(context.tree.root_node)
        return transformations


class SpacingRule(ASTRule):
    """AST-based spacing rule for operators, keywords, parentheses cleanup."""

    def __init__(self, config: FormatterConfig):
        self.config = config

    @property
    def rule_id(self) -> str:
        return "F004"

    @property
    def name(self) -> str:
        return "spacing"

    def analyze(self, context: FormattingContext) -> list[Transformation]:
        if not context.tree:
            return []
        transformations = []

        # Part 1: AST-based Logic
        def add_space(node_a, node_b):
            if node_a.end_byte == node_b.start_byte:
                transformations.append(Transformation(node_a.end_byte, node_a.end_byte, " "))

        def traverse(node):
            if node.type == "ERROR":
                return

            # Binary operators
            if node.type == "binary_expression" and len(node.children) >= 3:
                left, op, right = node.children[0], node.children[1], node.children[2]
                if op.type not in [".", "->"]:
                    add_space(left, op)
                    add_space(op, right)

            # Assignment operators
            if node.type in ["assignment_expression", "init_declarator"]:
                eq = None
                for child in node.children:
                    if child.type == "=":
                        eq = child
                        break
                if eq:
                    idx = node.children.index(eq)
                    if idx > 0:
                        add_space(node.children[idx - 1], eq)
                    if idx < len(node.children) - 1:
                        add_space(eq, node.children[idx + 1])

            # Keywords before parentheses
            if node.type in [
                "if_statement",
                "for_statement",
                "while_statement",
                "switch_statement",
            ]:
                keyword = node.children[0]
                if len(node.children) > 1:
                    add_space(keyword, node.children[1])

            # Space before opening brace
            if node.type == "{":
                if node.start_byte > 0:
                    char_before = context.source[node.start_byte - 1]
                    if char_before not in [" ", "\t", "(", "{", "\n"]:
                        transformations.append(
                            Transformation(node.start_byte, node.start_byte, " ")
                        )

            # Space before else
            if node.type == "else":
                if node.start_byte > 0 and context.source[node.start_byte - 1] == "}":
                    transformations.append(Transformation(node.start_byte, node.start_byte, " "))

            # Comma/semicolon spacing
            if node.type in [",", ";"]:
                parent = node.parent
                if parent:
                    try:
                        idx = parent.children.index(node)
                        if idx < len(parent.children) - 1:
                            next_node = parent.children[idx + 1]
                            if next_node.type not in [")", "}", ";", ","]:
                                add_space(node, next_node)
                    except ValueError:
                        pass

            for child in node.children:
                traverse(child)

        traverse(context.tree.root_node)

        # Part 2: Safe Text Cleanup
        # We use a regex To split source into code, comments, and strings
        # we only apply cleanup to code segments

        # Regex patterns: //comments, /*blocks*/ , "strings", 'chars'
        split_pattern = r"(//.*|/\*[\s\S]*?\*/|\"(?:\\.|[^\"\\])*\"|'(?:\\.|[^'\\])*')"

        last_pos = 0
        for match in re.finditer(split_pattern, context.source):
            # proccess the code segment before this match
            code_chunk_end = match.start()
            if code_chunk_end > last_pos:
                self._process_code_chunk(
                    context.source[last_pos:code_chunk_end], last_pos, transformations
                )

            last_pos = match.end()

        # process any remaining code after the last match
        if last_pos < len(context.source):
            self._process_code_chunk(context.source[last_pos:], last_pos, transformations)

        return transformations

    def _process_code_chunk(self, chunk: str, offset: int, transformations: list[Transformation]):
        """Applies Regex Cleanup to a chunk of raw code"""

        if not chunk.strip():
            return

        # 1. Remove Spaces around dot operator (struct access)
        # Note: we Capture newline to preserve them
        # this replaces " . " with "." but leaves "\n." intact
        # simple approach: chunk based replacementmight be tricky with mapping back to original offsets
        # Ideally, we find matches in the chunk and create transformations.

        # A. Cleanup for spaces around dot operator
        for m in re.finditer(r"(\S)\s+\.\s+(\S)", chunk):
            # Ensure we are not mergin accross lines inappropriately, though \s includes \n
            # but "struct \n . member" is valid C.
            # lets restrict to same-line for safety
            pass

        # we will use the original logic but applied carefully
        # Original: new_s = re.sub(r"\s*\.\s*", ".", stripped)
        # that was too aggressive. Lets do: "name . member" -> "name.member"

        # Find "word . word" patterns
        for m in re.finditer(r"(\w)\s*\.\s*(\w)", chunk):
            start, end = m.span()
            original = m.group(0)
            replacement = f"{m.group(1)}.{m.group(2)}"
            if original != replacement:
                transformations.append(
                    Transformation(
                        start_byte=offset + start,
                        end_byte=offset + end,
                        new_content=replacement,
                    )
                )

        # 2. Remove spaces before ++ and --
        for m in re.finditer(r"(\w+)\s+(\+\+|--)", chunk):
            start, end = m.span()
            replacement = f"{m.group(1)}.{m.group(2)}"
            transformations.append(
                Transformation(
                    start_byte=offset + start,
                    end_byte=offset + end,
                    new_content=replacement,
                )
            )

        # 3. Collapse multiple spaces into one (exculding newlines)
        for m in re.finditer(r"[ \t]{2,}", chunk):
            start, end = m.span()
            # if this is indentation (at start of line), we generally want to leave it
            # (IdentationRule should handle that) but it runs later
            # If we collapse Indentation, IdentationRule will just put it back
            # So Safe to Collapse to 1 space?
            # No: IdentationRule expects clean lines.
            is_start_of_line = (start == 0) or (chunk[start - 1] == "\n")
            if not is_start_of_line:
                transformations.append(
                    Transformation(
                        start_byte=offset + start,
                        end_byte=offset + end,
                        new_content=" ",
                    )
                )

        # 4. Normalize Function Declaration Spacing " ( " -> "("
        for m in re.finditer(r"\(\s+", chunk):
            if "\n" not in m.group(0):
                transformations.append(
                    Transformation(
                        start_byte=offset + m.start(),
                        end_byte=offset + m.end(),
                        new_content="(",
                    )
                )

        for m in re.finditer(r"\s+\)", chunk):
            if "\n" not in m.group(0):
                transformations.append(
                    Transformation(
                        start_byte=offset + m.start(),
                        end_byte=offset + m.end(),
                        new_content=")",
                    )
                )
