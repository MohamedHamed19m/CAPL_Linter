import re
from pathlib import Path

from capl_symbol_db.database import SymbolDatabase

from ..models import InternalIssue, Severity
from .base import BaseRule
from .db_helpers import RuleQueryHelper


class MissingEnumKeywordRule(BaseRule):
    """Detect enum types used without 'enum' keyword."""

    rule_id = "E004"
    name = "missing-enum-keyword"
    severity = Severity.ERROR
    auto_fixable = True
    description = "Enum types must be declared with 'enum' keyword."

    def check(self, file_path: Path, db: SymbolDatabase) -> list[InternalIssue]:
        helper = RuleQueryHelper(db, file_path)
        issues = []

        for var_name, line, context, signature in helper.get_type_usage_errors():
            if "enum" in context:
                type_name = signature.split()[0] if signature else "unknown"
                issues.append(
                    self._create_issue(
                        file_path=file_path,
                        line=line,
                        message=f"Type '{type_name}' used without 'enum' keyword in declaration of '{var_name}'",
                        context=context,
                    )
                )

        return issues

    def fix(self, file_path: Path, issues: list[InternalIssue]) -> str:
        lines = file_path.read_text(encoding="utf-8").split("\n")
        keyword = "enum" if self.rule_id == "E004" else "struct"
        for issue in sorted(issues, key=lambda x: x.line, reverse=True):
            idx = issue.line - 1
            if idx < len(lines):
                # Extraction of type name from message is a bit hacky but consistent with old logic
                match = re.search(r"Type '(\w+)'", issue.message)
                if match:
                    type_name = match.group(1)
                    pattern = rf"(?<!\b{keyword}\s)\b{type_name}\b"
                    lines[idx] = re.sub(pattern, f"{keyword} {type_name}", lines[idx], count=1)
        return "\n".join(lines)


class MissingStructKeywordRule(BaseRule):
    """Detect struct types used without 'struct' keyword."""

    rule_id = "E005"
    name = "missing-struct-keyword"
    severity = Severity.ERROR
    auto_fixable = True
    description = "Struct types must be declared with 'struct' keyword."

    def check(self, file_path: Path, db: SymbolDatabase) -> list[InternalIssue]:
        helper = RuleQueryHelper(db, file_path)
        issues = []

        for var_name, line, context, signature in helper.get_type_usage_errors():
            if "struct" in context:
                type_name = signature.split()[0] if signature else "unknown"
                issues.append(
                    self._create_issue(
                        file_path=file_path,
                        line=line,
                        message=f"Type '{type_name}' used without 'struct' keyword in declaration of '{var_name}'",
                        context=context,
                    )
                )

        return issues

    def fix(self, file_path: Path, issues: list[InternalIssue]) -> str:
        # Same logic as enum rule
        return MissingEnumKeywordRule.fix(self, file_path, issues)
