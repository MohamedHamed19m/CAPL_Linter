import re
from capl_formatter.rules.base import BaseFormattingRule, FormattingContext
from capl_formatter.models import FormatterConfig
from capl_formatter.utils import apply_text_transformation

class BlockExpansionRule(BaseFormattingRule):
    def __init__(self, config: FormatterConfig):
        self.config = config

    def apply(self, context: FormattingContext) -> None:
        def transform(code: str) -> str:
            # 1. Expand Open Brace
            # Match any non-whitespace char, followed by whitespace, then {
            # Replace with char + " {\n"
            # This expands initializers too, ensuring consistent multi-line structure.
            code = re.sub(r'(\S)\s*\{', r'\1 {\n', code)
            
            # 2. Expand Close Brace (Preceding newline)
            # If } is not preceded by \n, insert \n
            # e.g. "return; }" -> "return;\n}"
            code = re.sub(r'([^\n])\}', r'\1\n}', code)
            
            # 3. Expand Close Brace (Trailing newline)
            # If } is not followed by \n, insert \n
            # e.g. "} void" -> "}\nvoid"
            # Exception: } followed by ; (struct definition ends with };)
            # Exception: } else
            # We don't want "}\nelse" if we want "some style"?
            # Spec says "K&R ... opening brace on same line". 
            # K&R: } else {
            # Allman: } \n else {
            # If we enforce K&R, we might want "} else" on same line?
            # BraceStyleRule logic: `) \n {` -> `) {`.
            # But what about `} else`?
            # `BraceStyleRule` matches `(\)|else...)\s*\{`. Handles opening `{` of else.
            # But `} else` relationship?
            # Standard K&R: `} else` on same line.
            # So `BlockExpansionRule` should NOT insert newline before `else`.
            # And `while` (do-while)? `} while`.
            
            # So: Insert newline after } UNLESS followed by else, while, ;
            # Regex lookahead?
            # `\}(?!\s*(else|while|;))`
            
            code = re.sub(r'\}(?!\s*(else|while|;))([^\n])', r'}\n\2', code)
            
            return code

        context.source = apply_text_transformation(context.source, transform)
