from abc import ABC, abstractmethod
from pathlib import Path

from capl_symbol_db.database import SymbolDatabase

from ..models import InternalIssue, Severity


class BaseRule(ABC):
    """Abstract base class for all linting rules."""

    @property
    @abstractmethod
    def rule_id(self) -> str:
        """Unique rule identifier (e.g., 'E001', 'W102', 'S201')."""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable rule name (e.g., 'extern-keyword')."""
        pass

    @property
    @abstractmethod
    def severity(self) -> Severity:
        """Default severity for this rule."""
        pass

    @property
    def auto_fixable(self) -> bool:
        """Can this rule automatically fix violations?"""
        return False

    @property
    def description(self) -> str:
        """Detailed description of what this rule checks."""
        return ""

    @abstractmethod
    def check(self, file_path: Path, db: SymbolDatabase) -> list[InternalIssue]:
        """Run the check and return found issues."""
        pass

    def fix(self, file_path: Path, issues: list[InternalIssue]) -> str:
        """Apply auto-fixes for the detected issues.

        Args:
            file_path: Path to the file to fix
            issues: List of issues to fix (all belonging to this rule)

        Returns:
            Modified file content as a string
        """
        return file_path.read_text(encoding="utf-8")

    # Helper method for consistent issue creation
    def _create_issue(
        self,
        file_path: Path,
        line: int,
        message: str,
        context: str | None = None,
        column: int = 0,
    ) -> InternalIssue:
        """Helper to create an issue with rule defaults."""
        return InternalIssue(
            file_path=file_path,
            line=line,
            rule_id=self.rule_id,
            message=message,
            severity=self.severity,
            auto_fixable=self.auto_fixable,
            context=context,
            column=column,
        )
