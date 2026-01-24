from .rules.base import BaseRule
from .rules.semantic_rules import (
    UndefinedSymbolRule,
    DuplicateFunctionRule,
    CircularIncludeRule,
)
from .rules.syntax_rules import (
    ExternKeywordRule,
    FunctionDeclarationRule,
    GlobalTypeDefinitionRule,
    ArrowOperatorRule,
    PointerParameterRule,
)
from .rules.type_rules import (
    MissingEnumKeywordRule,
    MissingStructKeywordRule,
)
from .rules.variable_rules import (
    MidBlockVariableRule,
    VariableOutsideBlockRule,
)


class RuleRegistry:
    """Central registry for all linting rules."""

    def __init__(self):
        self._rules: dict[str, BaseRule] = {}
        self._register_builtin_rules()

    def _register_builtin_rules(self):
        """Auto-register all built-in rules."""
        builtin_rules = [
            # Syntax Rules (E001-E003)
            ExternKeywordRule(),
            FunctionDeclarationRule(),
            GlobalTypeDefinitionRule(),
            ArrowOperatorRule(),
            PointerParameterRule(),
            # Type Rules (E004-E005)
            MissingEnumKeywordRule(),
            MissingStructKeywordRule(),
            # Variable Rules (E006-E007)
            VariableOutsideBlockRule(),
            MidBlockVariableRule(),
            # Semantic Rules (E011-E012)
            UndefinedSymbolRule(),
            DuplicateFunctionRule(),
            # Warning Rules
            CircularIncludeRule(),  # W001
        ]

        for rule in builtin_rules:
            self._rules[rule.rule_id] = rule

    def get_rule(self, rule_id: str) -> BaseRule | None:
        """Get a specific rule by ID."""
        return self._rules.get(rule_id)

    def get_all_rules(self) -> list[BaseRule]:
        """Get all registered rules."""
        return list(self._rules.values())

    def get_enabled_rules(
        self, select: list[str] | None = None, ignore: list[str] | None = None
    ) -> list[BaseRule]:
        """Get rules based on selection/ignore filters.

        Args:
            select: List of rule categories ('E', 'W', 'S') or specific IDs ('E001')
            ignore: List of specific rule IDs to ignore
        """
        select = select or ["E", "W"]  # Default: errors and warnings
        ignore = ignore or []

        enabled = []
        for rule in self._rules.values():
            # Check if ignored
            if rule.rule_id in ignore:
                continue

            # Check if selected (by category or specific ID)
            category = rule.rule_id[0]  # 'E', 'W', or 'S'
            if category in select or rule.rule_id in select:
                enabled.append(rule)

        return enabled


# Global singleton
registry = RuleRegistry()
