from pathlib import Path

from .models import InternalIssue
from .registry import registry


class AutoFixEngine:
    """Automatically fix linting issues by delegating to rules"""

    def apply_fixes(self, file_path: Path, issues: list[InternalIssue]) -> str:
        if not issues:
            return file_path.read_text(encoding="utf-8")

        # Group issues by rule_id and apply one rule type at a time for safety
        rule_id = issues[0].rule_id
        rule = registry.get_rule(rule_id)

        if rule and rule.auto_fixable:
            return rule.fix(file_path, issues)

        return file_path.read_text(encoding="utf-8")
