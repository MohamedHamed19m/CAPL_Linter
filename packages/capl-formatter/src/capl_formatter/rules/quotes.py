import re
from typing import List
from .base import TextRule, FormattingContext, Transformation
from ..models import FormatterConfig

class QuoteNormalizationRule(TextRule):
    """Enforces double quotes for strings."""
    def __init__(self, config: FormatterConfig): self.config = config
    @property
    def rule_id(self) -> str: return "F008"
    @property
    def name(self) -> str: return "quote-normalization"

    def analyze(self, context: FormattingContext) -> List[Transformation]:
        if self.config.quote_style != "double": return []
        transformations = []
        pattern = r'''("(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*')'''
        for m in re.finditer(pattern, context.source):
            s = m.group(0)
            if s.startswith("'" ) and len(s) > 3:
                # heuristic: convert to double quotes
                content = s[1:-1]
                new_s = '"' + content.replace("\'", "'").replace('"', '\"') + '"'
                transformations.append(Transformation(m.start(), m.end(), new_s))
        return transformations
