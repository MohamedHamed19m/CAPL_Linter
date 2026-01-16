from capl_linter.models import InternalIssue
from .models import LintIssue


def internal_issue_to_lint_issue(issue: InternalIssue) -> LintIssue:
    """Convert an internal dataclass issue to an external Pydantic issue"""
    return LintIssue(
        severity=issue.severity.upper(),  # dataclass uses 'error', Pydantic uses 'ERROR'
        file_path=str(issue.file_path),
        line_number=issue.line,
        column=0,  # InternalIssue currently doesn't track column
        rule_id=issue.rule_id,
        message=issue.message,
        suggestion=None,  # To be implemented
        auto_fixable=issue.auto_fixable,
    )
