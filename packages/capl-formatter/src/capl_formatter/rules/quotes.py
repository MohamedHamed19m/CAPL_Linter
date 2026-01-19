import re
from capl_formatter.rules.base import BaseFormattingRule, FormattingContext
from capl_formatter.models import FormatterConfig

class QuoteNormalizationRule(BaseFormattingRule):
    def __init__(self, config: FormatterConfig):
        self.config = config

    def apply(self, context: FormattingContext) -> None:
        if self.config.quote_style != "double":
            return

        # Pattern from utils.py (duplicated here to avoid circular/complex refactoring)
        pattern = r'''(\/\/.*|\/\*[\s\S]*?\*\/|"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*')'''
        
        parts = re.split(pattern, context.source)
        
        for i, part in enumerate(parts):
            # Check if it looks like a single quoted string
            if part.startswith("'" ) and part.endswith("'" ) and len(part) > 1:
                # Determine if it should be converted
                # Heuristic: If length > 4 ('abc' is 5), convert.
                # 'a' is 3. '\n' is 4. 'ab' is 4.
                # '\xFF' is 6.
                
                # If it looks like an escape sequence, keep it?
                # If it has spaces, convert it.
                
                content = part[1:-1]
                
                should_convert = False
                if " " in content:
                    should_convert = True
                elif len(part) > 4:
                     # Check for hex/octal escapes which might be valid char constants
                     if not part.startswith("'\\"):
                         should_convert = True
                
                if should_convert:
                    # Convert to double quotes
                    # Unescape ' -> '
                    # Escape " -> \"
                    new_content = content.replace("\'", "'").replace('"', '\"')
                    parts[i] = f'"{new_content}"'
                    
        context.source = "".join(parts)
