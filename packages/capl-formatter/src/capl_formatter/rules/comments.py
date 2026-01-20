import re
import textwrap
from typing import List
from .base import TextRule, FormattingContext, Transformation
from ..models import FormatterConfig

class CommentReflowRule(TextRule):
    """Reflows comments to stay within line length."""
    def __init__(self, config: FormatterConfig): self.config = config
    @property
    def rule_id(self) -> str: return "F012"
    @property
    def name(self) -> str: return "comment-reflow"

    def analyze(self, context: FormattingContext) -> List[Transformation]:
        transformations = []
        # Pattern for comments and strings
        pattern = r'''(\/\/.*|\/\*[\s\S]*?\*\/|"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*')'''
        
        for m in re.finditer(pattern, context.source):
            comment = m.group(0)
            if comment.startswith("//"):
                if len(comment) > self.config.line_length:
                    # Simple line wrap
                    content = comment[2:].strip()
                    wrapped = textwrap.wrap(content, width=self.config.line_length - 3)
                    new_comment = "// " + "\n// ".join(wrapped)
                    transformations.append(Transformation(m.start(), m.end(), new_comment))
            elif comment.startswith("/*"):
                # ASCII Art Check
                if not re.match(r'/\*[*=]{2,}', comment):
                    if len(comment) > self.config.line_length or "\n" in comment:
                        # Reflow block
                        lines = comment.splitlines()
                        content_lines = []
                        for line in lines:
                            s = line.strip()
                            if s.startswith("/*"): s = s[2:]
                            if s.endswith("*/"): s = s[:-2]
                            if s.startswith("*"): s = s[1:]
                            content_lines.append(s.strip())
                        
                        content = " ".join(content_lines).strip()
                        if content:
                            wrapped = textwrap.wrap(content, width=self.config.line_length - 3)
                            new_comment = "/*\n" + "\n".join([f" * {l}" for l in wrapped]) + "\n */"
                            transformations.append(Transformation(m.start(), m.end(), new_comment))
        return transformations
