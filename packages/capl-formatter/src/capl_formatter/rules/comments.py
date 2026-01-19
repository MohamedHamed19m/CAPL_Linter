import re
import textwrap
from capl_formatter.rules.base import BaseFormattingRule, FormattingContext
from capl_formatter.models import FormatterConfig

class CommentReflowRule(BaseFormattingRule):
    def __init__(self, config: FormatterConfig):
        self.config = config

    def apply(self, context: FormattingContext) -> None:
        # Pattern from utils.py (duplicated)
        pattern = r'''(\/\/.*|\/\*[\s\S]*?\*\/|"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*')'''
        
        parts = re.split(pattern, context.source)
        
        for i, part in enumerate(parts):
            if part.startswith("//"):
                parts[i] = self._reflow_line_comment(part)
            elif part.startswith("/*"):
                parts[i] = self._reflow_block_comment(part)
                
        context.source = "".join(parts)

    def _reflow_line_comment(self, comment: str) -> str:
        if len(comment) <= self.config.line_length:
            return comment
            
        content = comment[2:].strip()
        wrapped = textwrap.wrap(content, width=self.config.line_length - 3)
        return "// " + "\n// ".join(wrapped)

    def _reflow_block_comment(self, comment: str) -> str:
        if re.match(r'\/\*[*=]{2,}', comment):
            return comment
            
        lines = comment.splitlines()
        cleaned_lines = []
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("/*"): stripped = stripped[2:]
            if stripped.endswith("*/"): stripped = stripped[:-2]
            if stripped.startswith("*"): stripped = stripped[1:]
            cleaned_lines.append(stripped.strip())
            
        content = " ".join(cleaned_lines).strip()
        
        if not content:
            return comment
            
        wrapped = textwrap.wrap(content, width=self.config.line_length - 3)
        
        result = "/*\n"
        for line in wrapped:
            result += " * " + line + "\n"
        result += " */"
        
        return result