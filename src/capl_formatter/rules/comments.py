import re
import textwrap

from ..models import FormatterConfig
from .base import FormattingContext, TextRule, Transformation


class CommentAlignmentRule(TextRule):
    """Aligns inline comments vertically."""

    def __init__(self, config: FormatterConfig):
        self.config = config

    @property
    def rule_id(self) -> str:
        return "F013"

    @property
    def name(self) -> str:
        return "comment-alignment"

    def analyze(self, context: FormattingContext) -> list[Transformation]:
        if not self.config.align_inline_comments:
            return []
        if not context.metadata or "comment_attachments" not in context.metadata:
            return []

        transformations = []
        comment_map = context.metadata["comment_attachments"]

        inline_comments = [c for c in comment_map.values() if c.attachment_type == "inline"]
        if not inline_comments:
            return []

        inline_comments.sort(key=lambda x: x.comment_line)

        groups = []
        if inline_comments:
            current_group = [inline_comments[0]]
            for i in range(1, len(inline_comments)):
                c = inline_comments[i]
                last = current_group[-1]
                if c.comment_line == last.comment_line + 1:
                    current_group.append(c)
                else:
                    groups.append(current_group)
                    current_group = [c]
            if current_group:
                groups.append(current_group)

        for group in groups:
            if len(group) < 2:
                continue

            max_code_end = 0
            for c in group:
                line = context.lines[c.comment_line]
                col = c.comment_node.start_point[1]
                text_before = line[:col].rstrip()
                code_end = len(text_before.expandtabs(self.config.indent_size))
                max_code_end = max(max_code_end, code_end)

            target_col = max(self.config.inline_comment_column, max_code_end + 2)

            for c in group:
                start_byte = c.comment_node.start_byte

                pos = start_byte - 1
                while pos >= 0 and context.source[pos] in [" ", "\t"]:
                    pos -= 1

                line_start = context.source.rfind("\n", 0, pos + 1) + 1
                text_before = context.source[line_start : pos + 1].expandtabs(
                    self.config.indent_size
                )

                spaces_needed = target_col - len(text_before)
                if spaces_needed < 1:
                    spaces_needed = 1

                new_spaces = " " * spaces_needed
                if context.source[pos + 1 : start_byte] != new_spaces:
                    transformations.append(
                        Transformation(
                            start_byte=pos + 1, end_byte=start_byte, new_content=new_spaces
                        )
                    )

        return transformations


class CommentReflowRule(TextRule):
    """Reflows prose-like comments to stay within line length."""

    def __init__(self, config: FormatterConfig):
        self.config = config

    @property
    def rule_id(self) -> str:
        return "F012"

    @property
    def name(self) -> str:
        return "comment-reflow"

    def analyze(self, context: FormattingContext) -> list[Transformation]:
        if not self.config.reflow_comments:
            return []

        transformations = []
        pattern = r"(\/\/.*)|(\/\*[\s\S]*?\*\/)"

        for m in re.finditer(pattern, context.source):
            comment = m.group(0)
            start_offset = m.start()

            if self._should_exclude(comment):
                continue

            line_start = context.source.rfind("\n", 0, start_offset) + 1
            visual_col = len(
                context.source[line_start:start_offset].expandtabs(self.config.indent_size)
            )

            if comment.startswith("//"):
                # Check if it's an inline comment
                is_inline = (
                    start_offset > line_start and context.source[start_offset - 1] not in "\n\r"
                )

                # Only reflow if it exceeds line length
                if len(comment) + visual_col > self.config.line_length:
                    content = comment[2:].strip()
                    prefix_str = " " * visual_col + "// "
                    width = self.config.line_length - len(prefix_str)
                    if width < 20:
                        width = 20

                    wrapped = textwrap.wrap(content, width=width, break_long_words=False)
                    if not wrapped:
                        continue

                    new_comment = "// " + wrapped[0]
                    if len(wrapped) > 1:
                        sep = "\n" + " " * visual_col + "// "
                        new_comment += sep + sep.join(wrapped[1:])

                    if new_comment != comment:
                        transformations.append(Transformation(m.start(), m.end(), new_comment))

            elif comment.startswith("/*"):
                # Only reflow single-line blocks that are too long
                if "\n" not in comment and len(comment) + visual_col > self.config.line_length:
                    content = self._get_block_content(comment)
                    if not content:
                        continue

                    indent_str = ""
                    for char in context.source[line_start:start_offset]:
                        if char in " \t":
                            indent_str += char
                        else:
                            break

                    prefix = indent_str + " * "
                    width = self.config.line_length - len(prefix)
                    if width < 20:
                        width = 20

                    wrapped = textwrap.wrap(content, width=width, break_long_words=False)
                    if not wrapped:
                        continue

                    new_comment = "/*\n"
                    for line in wrapped:
                        new_comment += prefix + line + "\n"
                    new_comment += indent_str + " */"

                    if new_comment != comment:
                        transformations.append(Transformation(m.start(), m.end(), new_comment))

        return transformations

    def _get_block_content(self, comment: str) -> str:
        lines = comment.splitlines()
        content_parts = []
        for line in lines:
            s = line.strip()
            if s.startswith("/*"):
                s = s[2:]
            if s.endswith("*/"):
                s = s[:-2]
            if s.startswith("*"):
                s = s[1:]
            part = s.strip()
            if part:
                content_parts.append(part)
        return " ".join(content_parts)

    def _should_exclude(self, comment: str) -> bool:
        """Determine if a comment should be excluded from reflowing."""

        # 1. check for standard Doxygen/doc markers
        if comment.startswith("//!") or comment.startswith("///") or comment.startswith("/**"):
            return True

        # 2. check for Doxygen tags (both @ and \ syntax) , this protects header style
        doxygen_tags = [
            r"@param",
            r"@return",
            r"@brief",
            r"@details",
            r"@see",
            r"@note",
            r"\param",
            r"\return",
            r"\brief",
            r"\details",
            r"\see",
            r"\note",
        ]

        if any(tag in comment for tag in doxygen_tags):
            return True

        # 3. check for vector/special file headers
        if "Encoding:" in comment:
            return True

        # 4. Check for Banner style comments (e.g., lines of asterisks or slashes)
        lines = comment.splitlines()
        for line in lines:
            stripped = line.strip()
            if len(stripped) > 5 and set(stripped).issubset({"*", "/", "-", "=", " "}):
                return True

        # 5. Check for ASCII Art/Diagrams
        diagram_symbols = "+-|<>=-"
        for line in lines:
            symbol_count = sum(line.count(s) for s in diagram_symbols)
            if symbol_count > 2 or "-->" in line or "<--" in line or "->" in line or "<-" in line:
                return True
        return False
