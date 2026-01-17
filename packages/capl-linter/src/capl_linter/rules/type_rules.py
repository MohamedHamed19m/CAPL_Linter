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
