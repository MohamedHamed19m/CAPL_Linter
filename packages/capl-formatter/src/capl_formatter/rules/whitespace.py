import re
from typing import List
from .base import TextRule, FormattingContext, Transformation
from ..models import FormatterConfig

class WhitespaceCleanupRule(TextRule):
    """Refined whitespace cleanup for professional formatting."""
    
    def __init__(self, config: FormatterConfig):
        self.config = config

    @property
    def rule_id(self) -> str: return "F001"
    @property
    def name(self) -> str: return "whitespace-cleanup"

    def analyze(self, context: FormattingContext) -> List[Transformation]:
        transformations = []
        
        # 1. Trailing Whitespace
        for m in re.finditer(r'[ \t]+$', context.source, re.MULTILINE):
            transformations.append(Transformation(m.start(), m.end(), ""))

        # 2. EOF Newline
        if context.source and not context.source.endswith('\n'):
            transformations.append(Transformation(len(context.source), len(context.source), "\n"))
        
        # 3. Collapse excessive blank lines globally (max 1 blank line between top-level items)
        for m in re.finditer(r'\n{3,}', context.source):
            transformations.append(Transformation(m.start(), m.end(), "\n\n"))

        # 4. Remove blank lines at the VERY start of a block
        # Look for { followed by \n and then more whitespace/newlines
        for m in re.finditer(r'\{\s*\n\s*\n+', context.source):
            # Replace the entire sequence between { and the first content with just {\n + indent
            # But wait, IndentationRule handles the indent. We just want to remove the blank lines.
            # Match: { then any number of \n and spaces, ending in at least two \n
            # Simpler: replace \n\n after { with \n
            pass

        return transformations