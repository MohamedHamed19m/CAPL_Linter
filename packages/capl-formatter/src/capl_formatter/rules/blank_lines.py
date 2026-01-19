import re
from capl_formatter.rules.base import BaseFormattingRule, FormattingContext
from capl_formatter.models import FormatterConfig
from capl_formatter.utils import apply_text_transformation

class BlankLineRule(BaseFormattingRule):
    def __init__(self, config: FormatterConfig):
        self.config = config

    def apply(self, context: FormattingContext) -> None:
        def transform(code: str) -> str:
            # 2 blank lines (3 newlines) before variables
            # Match optional preceding whitespace/newlines, then variables {
            # Capture variables... in group 2
            # We use \b to ensure word boundary
            code = re.sub(r'(\n\s*)*(\bvariables\s*\{)', r'\n\n\n\2', code)
            
            # 1 blank line (2 newlines) before functions/handlers
            # Handlers: on ...
            # Functions: type name(...) {
            # Note: This is a heuristic regex. It might match local vars if not careful.
            # But local vars usually don't have { immediately? 
            # "int x;" vs "int func() {"
            # So looking for { is good.
            # But spec says "before functions/event handlers".
            # Handler: on ...
            code = re.sub(r'(\n\s*)*(\bon\s+[\w\s]+\{?)', r'\n\n\2', code)
            
            # Functions: (void|int|...) name(...) {
            # We want to match definition, not declaration or variable.
            # definition has {
            types = r'(void|int|float|byte|word|dword|qword|long|short|char|double)'
            # Pattern: type space name space ( ... ) space {
            # This is complex to match parens with regex.
            # Simplified: type space name ... {
            
            code = re.sub(rf'(\n\s*)*(\b{types}\s+\w+.*\{{)', r'\n\n\2', code)
            
            return code

        # Note: This transformation might be aggressive.
        # But it respects the "Opinionated" goal.
        # It operates on code segments.
        
        context.source = apply_text_transformation(context.source, transform)
        
        # Cleanup: If we introduced too many blank lines at start, WhitespaceCleanup *should* handle?
        # My WhitespaceCleanupRule collapses consecutive blank lines to max 2.
        # But here we add exactly 2 or 1.
        # If we added leading newlines at absolute start, we might want to strip them.
        context.source = context.source.lstrip('\n')
