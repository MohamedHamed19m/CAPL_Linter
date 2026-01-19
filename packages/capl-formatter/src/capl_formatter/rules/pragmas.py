import re
from capl_formatter.rules.base import BaseFormattingRule, FormattingContext
from capl_formatter.models import FormatterConfig

class PragmaHandlingRule(BaseFormattingRule):
    def __init__(self, config: FormatterConfig):
        self.config = config

    def apply(self, context: FormattingContext) -> None:
        # Extract pragmas
        pragma_pattern = r'^\s*#pragma\s+library\s+.*$'
        pragmas = re.findall(pragma_pattern, context.source, re.MULTILINE)
        
        if not pragmas:
            return
            
        # Remove pragmas from their current positions
        # Use re.sub to remove entire lines
        context.source = re.sub(pragma_pattern, '', context.source, flags=re.MULTILINE)
        
        # Clean up empty lines left behind? WhitespaceCleanupRule handles it.
        # But for now we might leave gaps.
        
        # Prepare pragma block
        # Ensure pragmas are clean (strip whitespace)
        cleaned_pragmas = [p.strip() for p in pragmas]
        pragma_block = "\n".join(cleaned_pragmas)
        
        # Prepend to source
        # Add a newline after pragmas
        context.source = pragma_block + "\n" + context.source
