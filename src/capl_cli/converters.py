from capl_linter.models import InternalIssue

from .models import LintIssue


def internal_issue_to_lint_issue(issue: InternalIssue) -> LintIssue:
    """Convert an internal dataclass issue to an external Pydantic issue"""
    return LintIssue(
        severity=issue.severity.value.upper(),  # Enum to 'ERROR', 'WARNING', etc.
        file_path=str(issue.file_path),
        line_number=issue.line,
        column=issue.column,
        rule_id=issue.rule_id,
        message=issue.message,
        suggestion=None,  # To be implemented
        auto_fixable=issue.auto_fixable,
    )
