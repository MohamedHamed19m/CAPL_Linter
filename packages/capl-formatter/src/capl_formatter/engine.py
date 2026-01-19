from typing import List
from .models import FormatterConfig, FormatResult, FormatResults
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
        errors = []
        
        try:
            for rule in self.rules:
                rule.apply(context)
        except Exception as e:
            errors.append(str(e))
            # Restore original source on error
            context.source = original_source
            
        modified = context.source != original_source
        return FormatResult(
            source=context.source,
            modified=modified,
            errors=errors
        )

    def format_files(self, files: List[str]) -> FormatResults:
        results = []
        modified_count = 0
        error_count = 0
        
        for file_path in files:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    source = f.read()
                
                result = self.format_string(source, file_path)
                results.append(result)
                
                if result.errors:
                    error_count += 1
                elif result.modified:
                    modified_count += 1
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write(result.source)
            except Exception as e:
                results.append(FormatResult(source="", modified=False, errors=[str(e)]))
                error_count += 1
                
        return FormatResults(
            results=results,
            total_files=len(files),
            modified_files=modified_count,
            error_files=error_count
        )