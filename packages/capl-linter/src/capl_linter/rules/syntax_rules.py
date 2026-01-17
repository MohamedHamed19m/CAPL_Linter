from pathlib import Path

from capl_symbol_db.database import SymbolDatabase

from ..models import InternalIssue, Severity
from .base import BaseRule
from .db_helpers import RuleQueryHelper


class ExternKeywordRule(BaseRule):
    """Detect and remove 'extern' keyword (not supported in CAPL)."""

    rule_id = "E001"
    name = "extern-keyword"
    severity = Severity.ERROR
    auto_fixable = True
    description = "The 'extern' keyword is not supported in CAPL and must be removed."

    def check(self, file_path: Path, db: SymbolDatabase) -> list[InternalIssue]:
        helper = RuleQueryHelper(db, file_path)
        issues = []

        for name, line, context in helper.get_forbidden_syntax():
            if context == "extern_keyword":
                issues.append(
                    self._create_issue(
                        file_path=file_path,
                        line=line,
                        message="'extern' keyword is not supported in CAPL",
                        context=context,
                    )
                )

        return issues


class FunctionDeclarationRule(BaseRule):
    """Detect function forward declarations (not allowed in CAPL)."""

    rule_id = "E002"
    name = "function-declaration"
    severity = Severity.ERROR
    auto_fixable = True
    description = "CAPL does not support function prototypes/forward declarations."

    def check(self, file_path: Path, db: SymbolDatabase) -> list[InternalIssue]:
        helper = RuleQueryHelper(db, file_path)
        issues = []

        for name, line, context in helper.get_forbidden_syntax():
            if context == "function_declaration":
                issues.append(
                    self._create_issue(
                        file_path=file_path,
                        line=line,
                        message=f"Function forward declaration '{name}' is not allowed in CAPL",
                        context=context,
                    )
                )

        return issues


class GlobalTypeDefinitionRule(BaseRule):
    """Detect enum/struct defined outside variables{} block."""

    rule_id = "E003"
    name = "global-type-definition"
    severity = Severity.ERROR
    auto_fixable = True
    description = "Type definitions must be inside 'variables {}' block."

    def check(self, file_path: Path, db: SymbolDatabase) -> list[InternalIssue]:
        helper = RuleQueryHelper(db, file_path)
        issues = []

        results = helper.query_symbols(
            scope="global", contexts=["enum_definition", "struct_definition"]
        )

        for name, line, context, _, _, _ in results:
            type_kind = "enum" if context == "enum_definition" else "struct"
            issues.append(
                self._create_issue(
                    file_path=file_path,
                    line=line,
                    message=f"{type_kind.capitalize()} '{name}' must be defined inside 'variables {{}}' block",
                    context=context,
                )
            )

        return issues

class ArrowOperatorRule(BaseRule):
    """Detect and fix arrow operator '->' usage (not supported in CAPL)."""

    rule_id = "E008"
    name = "arrow-operator"
    severity = Severity.ERROR
    auto_fixable = True
    description = "Arrow operator '->' is not supported in CAPL. Use dot notation instead."

    def check(self, file_path: Path, db: SymbolDatabase) -> list[InternalIssue]:
        helper = RuleQueryHelper(db, file_path)
        issues = []

        # Query for arrow_operator context
        results = helper.query_symbols(symbol_type="forbidden_syntax", context="arrow_operator")

        for _, line, _, sig, _, _ in results:
            issues.append(
                self._create_issue(
                    file_path=file_path,
                    line=line,
                    message="Arrow operator '->' is not supported in CAPL. Use dot notation instead.",
                    context="arrow_operator",
                )
            )

        return issues


class PointerParameterRule(BaseRule):
    """Detect forbidden struct pointer parameters."""

    rule_id = "E009"
    name = "pointer-parameter"
    severity = Severity.ERROR
    auto_fixable = False  # Keep as non-fixable for now
    description = "Struct pointers are not supported in CAPL parameters."

    def check(self, file_path: Path, db: SymbolDatabase) -> list[InternalIssue]:
        helper = RuleQueryHelper(db, file_path)
        issues = []

        # Query for pointer_parameter context
        results = helper.query_symbols(symbol_type="forbidden_syntax", context="pointer_parameter")

        for _, line, _, sig, _, _ in results:
            issues.append(
                self._create_issue(
                    file_path=file_path,
                    line=line,
                    message=f"Pointer parameter '{sig}' is forbidden. CAPL passes structs by reference implicitly.",
                    context="pointer_parameter",
                )
            )

        return issues

