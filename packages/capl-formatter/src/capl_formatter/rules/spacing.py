import re
from capl_formatter.rules.base import BaseFormattingRule, FormattingContext
from capl_formatter.models import FormatterConfig
from capl_formatter.utils import apply_text_transformation

class BraceStyleRule(BaseFormattingRule):
    def __init__(self, config: FormatterConfig):
        self.config = config

    def apply(self, context: FormattingContext) -> None:
        if self.config.brace_style != "k&r":
            return

        def transform(code: str) -> str:
            # Matches: ) OR else OR do OR try
            # Followed by: any whitespace (incl newlines)
            # Followed by: {
            # Replaces with: keyword/paren + " {"
            return re.sub(r'(\)|else|do|try)\s*\{', r'\1 {', code)

        context.source = apply_text_transformation(context.source, transform)

class SpacingRule(BaseFormattingRule):
    def __init__(self, config: FormatterConfig):
        self.config = config

    def apply(self, context: FormattingContext) -> None:
        def transform(code: str) -> str:
            # 1. Comma: Ensure space after comma
            code = re.sub(r',\s*', ', ', code)
            
            # 2. Before Open Brace: Ensure space before { if not preceded by space
            # Lookbehind is fixed width, so handled via grouping
            code = re.sub(r'([^\s])\{', r'\1 {', code)
            
            # 3. Assignment and Comparators: =, ==, !=, <=, >=, +=, -= 
            # Ensure spaces around them
            # Match: =, ==, !=, <=, >=, +=, -=, *=, /=
            # Avoid matching inside other things? Code separation helps.
            ops = r'(==|!=|<=|>=|\+=|-=|\*=|/=|=(?!=))'
            # (?!=) ensures = is not matched if it's == (captured by first group)
            # Actually standard regex matching checks order.
            
            # Pattern: \s* (OP) \s*
            # Replace: " \1 "
            # This handles =, ==, != etc.
            # But wait, what about <=>? No spaceship in CAPL?
            
            code = re.sub(r'\s*(==|!=|<=|>=|\+=|-=|\*=|/=|=(?!=))\s*', r' \1 ', code)
            
            # Cleanup multiple spaces (optional, but good)
            # code = re.sub(r'  +', ' ', code) # Might be too aggressive
            
            # 4. Keyword Spacing: if( -> if (
            # Keywords: if, while, for, switch
            code = re.sub(r'\b(if|while|for|switch)\(', r'\1 (', code)
            
            return code

        context.source = apply_text_transformation(context.source, transform)
