from pathlib import Path

from capl_symbol_db.database import SymbolDatabase

from ..models import InternalIssue, Severity
from .base import BaseRule
from .db_helpers import RuleQueryHelper


class VariableOutsideBlockRule(BaseRule):
    """Variables must be declared inside variables{} block."""

    rule_id = "E006"
    name = "variable-outside-block"
    severity = Severity.ERROR
    auto_fixable = True
    description = "Global variables must be declared inside 'variables {}' block."

    def check(self, file_path: Path, db: SymbolDatabase) -> list[InternalIssue]:
        helper = RuleQueryHelper(db, file_path)
        issues = []

        for name, line in helper.get_global_variables():
            issues.append(
                self._create_issue(
                    file_path=file_path,
                    line=line,
                    message=f"Variable '{name}' declared outside 'variables {{}}' block",
                )
            )

        return issues

    def fix(self, file_path: Path, issues: list[InternalIssue]) -> str:
        lines = file_path.read_text(encoding="utf-8").split("\n")
        
        # 1. Collect all variables to move (with their lines)
        # Sort by line number descending to avoid index shifting during removal
        sorted_issues = sorted(issues, key=lambda x: x.line, reverse=True)
        to_move = []
        for issue in sorted_issues:
            line_idx = issue.line - 1
            if line_idx < len(lines):
                # Save the content and remove the line
                to_move.append(lines.pop(line_idx).strip())

        # 2. Ensure block exists and find insertion point
        var_block_start, var_block_end = self._find_variables_block_range(lines)
        if var_block_start is None:
            # Create block
            insert_pos = 0
            for i, line in enumerate(lines):
                if not line.strip().startswith("#include"):
                    insert_pos = i
                    break
            lines.insert(insert_pos, "variables {")
            lines.insert(insert_pos + 1, "}")
            var_block_end = insert_pos + 1
        
        # 3. Insert all moved variables into the block
        # Use reversed(to_move) because we collected them bottom-up (reverse=True)
        # but we want to insert them at the END of the block in original order.
        for var_content in reversed(to_move):
            lines.insert(var_block_end, "  " + var_content)
            var_block_end += 1

        return "\n".join(lines)

    def _find_variables_block_range(self, lines: list[str]):
        start = None
        brace_count = 0
        for i, line in enumerate(lines):
            if "variables" in line and "{" in line:
                start = i
                brace_count = line.count("{") - line.count("}")
                if brace_count == 0:
                    return start, i
                continue
            if start is not None:
                brace_count += line.count("{") - line.count("}")
                if brace_count == 0:
                    return start, i
        return None, None


class MidBlockVariableRule(BaseRule):
    """Local variables must be declared at function start."""

    rule_id = "E007"
    name = "variable-mid-block"
    severity = Severity.ERROR
    auto_fixable = True
    description = "Local variables must be declared at the beginning of a function."

    def check(self, file_path: Path, db: SymbolDatabase) -> list[InternalIssue]:
        helper = RuleQueryHelper(db, file_path)
        issues = []

        for name, line, parent in helper.get_mid_block_variables():
            issues.append(
                self._create_issue(
                    file_path=file_path,
                    line=line,
                    message=f"Variable '{name}' declared after executable statements in '{parent}'",
                    context=parent,
                )
            )

        return issues

    def fix(self, file_path: Path, issues: list[InternalIssue]) -> str:
        lines = file_path.read_text(encoding="utf-8").split("\n")

        # Group issues by parent function/testcase
        by_parent: dict[str, list[InternalIssue]] = {}
        for issue in issues:
            parent = issue.context or "unknown"
            if parent not in by_parent:
                by_parent[parent] = []
            by_parent[parent].append(issue)

        for parent_name, parent_issues in by_parent.items():
            func_start_idx = self._find_function_start(lines, parent_name)
            if func_start_idx is None:
                continue

            # Find opening brace
            body_start_idx = None
            for i in range(func_start_idx, len(lines)):
                if "{" in lines[i]:
                    body_start_idx = i + 1
                    break
            if body_start_idx is None:
                continue

            # Extract and remove variable lines
            to_move_lines = []
            for issue in sorted(parent_issues, key=lambda x: x.line, reverse=True):
                line_idx = issue.line - 1
                if line_idx >= len(lines):
                    continue
                to_move_lines.append(lines.pop(line_idx).strip())

            # Insert at body start
            for var_line in reversed(to_move_lines):
                lines.insert(body_start_idx, "  " + var_line)

        return "\n".join(lines)

    def _find_function_start(self, lines: list[str], func_name: str) -> int | None:
        if not func_name or func_name == "unknown":
            return None
        # Exact match for function name in signature
        for i, line in enumerate(lines):
            if func_name in line and ("(" in line or "{" in line):
                return i
        return None
