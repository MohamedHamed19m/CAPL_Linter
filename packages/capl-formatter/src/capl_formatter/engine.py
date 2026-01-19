from typing import List
from .models import FormatterConfig, FormatResult
from .rules.base import BaseFormattingRule, FormattingContext

class FormatterEngine:
    def __init__(self, config: FormatterConfig):
        self.config = config
        self.rules: List[BaseFormattingRule] = []

    def add_rule(self, rule: BaseFormattingRule) -> None:
        self.rules.append(rule)

    def format_string(self, source: str, file_path: str = "") -> FormatResult:
        context = FormattingContext(source=source, file_path=file_path)
        original_source = source
        
        for rule in self.rules:
            rule.apply(context)
            
        modified = context.source != original_source
        return FormatResult(
            source=context.source,
            modified=modified
        )
