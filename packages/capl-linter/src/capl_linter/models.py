from dataclasses import dataclass
from pathlib import Path


@dataclass
class InternalIssue:
    """Internal representation of a linting issue"""

    file_path: Path
    line: int
    rule_id: str
    message: str
    severity: str  # 'error', 'warning', 'style', 'info'
    auto_fixable: bool
    context: str | None = None


@dataclass
class AutoFixAction:
    """Action to take for an auto-fix"""

    action_type: str  # 'insert', 'replace', 'delete'
    line_number: int
    old_text: str | None = None
    new_text: str | None = None
