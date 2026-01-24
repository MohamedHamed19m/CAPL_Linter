import re
import sqlite3
from pathlib import Path

from capl_tree_sitter import ASTWalker, CAPLParser, CAPLPatterns

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
        parser = CAPLParser()
        result = parser.parse_file(file_path)
        issues = []

        for decl in ASTWalker.find_all_by_type(result.tree.root_node, "declaration"):
            if CAPLPatterns.has_extern_keyword(decl, result.source):
                issues.append(
                    self._create_issue(
                        file_path=file_path,
                        line=decl.start_point[0] + 1,
                        message="'extern' keyword is not supported in CAPL",
                        context="extern_keyword",
                        column=decl.start_point[1],
                    )
                )

        return issues

    def fix(self, file_path: Path, issues: list[InternalIssue]) -> str:
        lines = file_path.read_text(encoding="utf-8").split("\n")
        for issue in sorted(issues, key=lambda x: x.line, reverse=True):
            idx = issue.line - 1
            if idx < len(lines):
                lines[idx] = re.sub(r"\bextern\s+", "", lines[idx], count=1)
        return "\n".join(lines)


class FunctionDeclarationRule(BaseRule):
    """Detect function forward declarations (not allowed in CAPL)."""

    rule_id = "E002"
    name = "function-declaration"
    severity = Severity.ERROR
    auto_fixable = True
    description = "CAPL does not support function prototypes/forward declarations."

    def check(self, file_path: Path, db: SymbolDatabase) -> list[InternalIssue]:
        issues = []
        conn = sqlite3.connect(db.db_path)
        try:
            cursor = conn.execute(
                """
                SELECT s.symbol_name, s.line_number
                FROM symbols s
                JOIN files f ON s.file_id = f.file_id
                WHERE f.file_path = ?
                  AND s.symbol_type = 'function'
                  AND s.has_body = 0
                """,
                (str(file_path.resolve()),),
            )
            for name, line in cursor.fetchall():
                issues.append(
                    self._create_issue(
                        file_path=file_path,
                        line=line,
                        message=f"Function forward declaration '{name}' is not allowed in CAPL",
                        context="function_declaration",
                    )
                )
        finally:
            conn.close()

        return issues

    def fix(self, file_path: Path, issues: list[InternalIssue]) -> str:
        lines = file_path.read_text(encoding="utf-8").split("\n")
        for issue in sorted(issues, key=lambda x: x.line, reverse=True):
            line_idx = issue.line - 1
            if line_idx >= len(lines):
                continue

            if ";" in lines[line_idx]:
                lines.pop(line_idx)
            else:
                # Handle multi-line declaration (simple search for ;)
                for i in range(line_idx, min(line_idx + 5, len(lines))):
                    if ";" in lines[i]:
                        for _ in range(i - line_idx + 1):
                            lines.pop(line_idx)
                        break
        return "\n".join(lines)


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

    def fix(self, file_path: Path, issues: list[InternalIssue]) -> str:
        lines = file_path.read_text(encoding="utf-8").split("\n")
        # Use helper from VariableOutsideBlockRule for now
        from .variable_rules import VariableOutsideBlockRule

        v_rule = VariableOutsideBlockRule()
        var_block_start, var_block_end = v_rule._find_variables_block_range(lines)

        if var_block_start is None:
            # Create variables block after includes
            insert_pos = 0
            for i, line in enumerate(lines):
                if not line.strip().startswith("#include"):
                    insert_pos = i
                    break
            lines.insert(insert_pos, "variables {")
            lines.insert(insert_pos + 1, "}")
            var_block_start = insert_pos
            var_block_end = insert_pos + 1

        # Process each issue bottom-up
        for issue in sorted(issues, key=lambda x: x.line, reverse=True):
            start_line_idx = issue.line - 1
            if start_line_idx >= len(lines):
                continue

            # Find the end of the definition
            end_line_idx = None
            brace_count = 0
            found_open = False
            for i in range(start_line_idx, len(lines)):
                line = lines[i]
                if "{" in line:
                    brace_count += line.count("{")
                    found_open = True
                if "}" in line:
                    brace_count -= line.count("}")

                if found_open and brace_count == 0:
                    end_line_idx = i
                    break

            if end_line_idx is not None:
                # Extract the whole block
                def_lines = lines[start_line_idx : end_line_idx + 1]
                # Remove from lines
                for _ in range(len(def_lines)):
                    lines.pop(start_line_idx)

                # Adjust var_block_end
                if start_line_idx < var_block_end:
                    var_block_end -= len(def_lines)

                # Insert into variables block
                for i, def_line in enumerate(def_lines):
                    lines.insert(var_block_end, "  " + def_line.strip())
                    var_block_end += 1

        return "\n".join(lines)


class ArrowOperatorRule(BaseRule):
    """Detect and fix arrow operator '->' usage (not supported in CAPL)."""

    rule_id = "E008"
    name = "arrow-operator"
    severity = Severity.ERROR
    auto_fixable = True
    description = "Arrow operator '->' is not supported in CAPL. Use dot notation instead."

    def check(self, file_path: Path, db: SymbolDatabase) -> list[InternalIssue]:
        parser = CAPLParser()
        result = parser.parse_file(file_path)
        issues = []

        violations = CAPLPatterns.has_arrow_operator_usage(result.tree.root_node, result.source)
        for v in violations:
            issues.append(
                self._create_issue(
                    file_path=file_path,
                    line=v["line"],
                    message=v["message"],
                    context="arrow_operator",
                    column=v["column"],
                )
            )

        return issues

    def fix(self, file_path: Path, issues: list[InternalIssue]) -> str:
        lines = file_path.read_text(encoding="utf-8").split("\n")
        for issue in sorted(issues, key=lambda x: x.line, reverse=True):
            idx = issue.line - 1
            if idx < len(lines):
                lines[idx] = lines[idx].replace("->", ".")
        return "\n".join(lines)


class PointerParameterRule(BaseRule):
    """Detect forbidden struct pointer parameters."""

    rule_id = "E009"
    name = "pointer-parameter"
    severity = Severity.ERROR
    auto_fixable = False  # Keep as non-fixable for now
    description = "Struct pointers are not supported in CAPL parameters."

    def check(self, file_path: Path, db: SymbolDatabase) -> list[InternalIssue]:
        parser = CAPLParser()
        result = parser.parse_file(file_path)
        issues = []

        funcs = ASTWalker.find_all_by_type(result.tree.root_node, "function_definition")
        for func in funcs:
            violations = CAPLPatterns.has_forbidden_pointer_parameter(func, result.source)
            for v in violations:
                issues.append(
                    self._create_issue(
                        file_path=file_path,
                        line=v["line"],
                        message=v["message"],
                        context="pointer_parameter",
                        column=v["column"],
                    )
                )

        return issues
