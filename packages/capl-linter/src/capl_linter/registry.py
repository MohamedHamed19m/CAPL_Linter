from typing import List, Protocol
from pathlib import Path
from capl_symbol_db.database import SymbolDatabase
from .models import InternalIssue

class LintRule(Protocol):
    """Protocol for a linting rule"""
    def check(self, file_path: Path, db: SymbolDatabase) -> List[InternalIssue]:
        ...

class RuleRegistry:
    """Registry for managing and loading linting rules"""

    def __init__(self):
        self._rules: List[LintRule] = []
        self._load_builtin_rules()

    def register(self, rule: LintRule):
        self._rules.append(rule)

    def get_all_rules(self) -> List[LintRule]:
        return self._rules

    def _load_builtin_rules(self):
        from .rules.syntax_rules import ForbiddenSyntaxRule
        self.register(ForbiddenSyntaxRule())
