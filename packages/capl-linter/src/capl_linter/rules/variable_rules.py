from pathlib import Path

from capl_symbol_db.database import SymbolDatabase

from ..models import InternalIssue, Severity
from .base import BaseRule
from .db_helpers import RuleQueryHelper


class VariableOutsideBlockRule(BaseRule):
    """Variables must be declared inside variables{} block."""

    rule_id = "E006"
    name = "variable-outside-block"
    severity = Severity.ERROR
    auto_fixable = True
    description = "Global variables must be declared inside 'variables {}' block."

    def check(self, file_path: Path, db: SymbolDatabase) -> list[InternalIssue]:
        helper = RuleQueryHelper(db, file_path)
        issues = []

        for name, line in helper.get_global_variables():
            issues.append(
                self._create_issue(
                    file_path=file_path,
                    line=line,
                    message=f"Variable '{name}' declared outside 'variables {{}}' block",
                )
            )

        return issues


class MidBlockVariableRule(BaseRule):
    """Local variables must be declared at function start."""

    rule_id = "E007"
    name = "variable-mid-block"
    severity = Severity.ERROR
    auto_fixable = True
    description = "Local variables must be declared at the beginning of a function."

    def check(self, file_path: Path, db: SymbolDatabase) -> list[InternalIssue]:
        helper = RuleQueryHelper(db, file_path)
        issues = []

        for name, line, parent in helper.get_mid_block_variables():
            issues.append(
                self._create_issue(
                    file_path=file_path,
                    line=line,
                    message=f"Variable '{name}' declared after executable statements in '{parent}'",
                    context=parent,
                )
            )

        return issues
