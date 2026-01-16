from pathlib import Path
from typing import Protocol

from capl_symbol_db.database import SymbolDatabase

from .models import InternalIssue


class LintRule(Protocol):
    """Protocol for a linting rule"""

    def check(self, file_path: Path, db: SymbolDatabase) -> list[InternalIssue]: ...


class RuleRegistry:
    """Registry for managing and loading linting rules"""

    def __init__(self):
        self._rules: list[LintRule] = []
        self._load_builtin_rules()

    def register(self, rule: LintRule):
        self._rules.append(rule)

    def get_all_rules(self) -> list[LintRule]:
        return self._rules

    def _load_builtin_rules(self):
        from .rules.syntax_rules import ForbiddenSyntaxRule, GlobalTypeDefinitionRule
        from .rules.type_rules import TypeUsageRule
        from .rules.variable_rules import VariablePlacementRule

        self.register(ForbiddenSyntaxRule())
        self.register(GlobalTypeDefinitionRule())
        self.register(VariablePlacementRule())
        self.register(TypeUsageRule())
