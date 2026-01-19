from capl_formatter.rules.base import BaseFormattingRule, FormattingContext
from capl_formatter.models import FormatterConfig

class IndentationRule(BaseFormattingRule):
    def __init__(self, config: FormatterConfig):
        self.config = config

    def apply(self, context: FormattingContext) -> None:
        lines = context.source.splitlines()
        formatted_lines = []
        current_indent_level = 0
        indent_str = " " * self.config.indent_size
        
        for line in lines:
            stripped = line.strip()
            if not stripped:
                formatted_lines.append("")
                continue
            
            # Simple brace counting (ignoring strings/comments for now)
            open_braces = stripped.count('{')
            close_braces = stripped.count('}')
            
            # Determine indentation for THIS line
            if stripped.startswith('}'):
                print_level = max(0, current_indent_level - 1)
            else:
                print_level = current_indent_level
            
            formatted_lines.append((indent_str * print_level) + stripped)
            
            # Update indentation for NEXT line
            current_indent_level += (open_braces - close_braces)
            current_indent_level = max(0, current_indent_level)
            
        # Reconstruct source
        # Use simple \n join. WhitespaceRule handles EOF newline.
        context.source = "\n".join(formatted_lines)
