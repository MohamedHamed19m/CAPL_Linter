import re
from capl_formatter.rules.base import BaseFormattingRule, FormattingContext
from capl_formatter.models import FormatterConfig

class WhitespaceCleanupRule(BaseFormattingRule):
    def __init__(self, config: FormatterConfig):
        self.config = config

    def apply(self, context: FormattingContext) -> None:
        lines = context.source.splitlines()
        cleaned_lines = []
        blank_lines_count = 0
        
        for line in lines:
            stripped = line.rstrip()
            
            if not stripped:
                blank_lines_count += 1
                if blank_lines_count <= 2:
                    cleaned_lines.append("")
            else:
                blank_lines_count = 0
                cleaned_lines.append(stripped)
        
        # Ensure single newline at EOF
        result = "\n".join(cleaned_lines)
        if result and not result.endswith("\n"):
            result += "\n"
            
        context.source = result
