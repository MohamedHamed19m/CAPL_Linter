from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class Severity(Enum):
    ERROR = "error"
    WARNING = "warning"
    STYLE = "style"


@dataclass
class InternalIssue:
    """Internal representation of a linting issue."""

    file_path: Path
    line: int
    rule_id: str  # e.g., "E001", "W102"
    message: str
    severity: Severity
    auto_fixable: bool = False
    context: str | None = None  # Extra metadata
    column: int = 0  # Add column info

    @property
    def sort_key(self):
        """For sorting issues by location."""
        return (self.line, self.column)


@dataclass
class FixEdit:
    """Represents a single edit operation for auto-fix."""

    line_number: int
    old_text: str  # What to find/replace
    new_text: str  # What to replace with
    context: str | None = None  # Function name, block type, etc.
