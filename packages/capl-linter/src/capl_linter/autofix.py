import re
from pathlib import Path
from typing import List, Dict, Optional, Callable
from .models import InternalIssue, AutoFixAction


class AutoFixEngine:
    """Automatically fix linting issues using registered fixers"""

    def __init__(self):
        self._fixers: Dict[str, Callable[[str, List[InternalIssue]], str]] = {
            "variable-outside-block": self._fix_variable_outside_block,
            "variable-mid-block": self._fix_variable_mid_block,
            "missing-enum-keyword": self._fix_missing_type_keyword,
            "missing-struct-keyword": self._fix_missing_type_keyword,
            "function-declaration": self._fix_function_declaration,
            "global-enum-definition": self._fix_global_type_definition,
            "global-struct-definition": self._fix_global_type_definition,
            "extern-keyword": self._fix_extern_keyword,
        }

    def can_fix(self, rule_id: str) -> bool:
        return rule_id in self._fixers

    def apply_fixes(self, file_path: Path, issues: List[InternalIssue]) -> str:
        if not issues:
            return file_path.read_text(encoding="utf-8")

        content = file_path.read_text(encoding="utf-8")

        # Group issues by rule_id and apply one rule type at a time for safety
        rule_id = issues[0].rule_id
        if self.can_fix(rule_id):
            content = self._fixers[rule_id](content, issues)

        return content

    def _fix_global_type_definition(self, content: str, issues: List[InternalIssue]) -> str:
        lines = content.split("\n")
        var_block_start, var_block_end = self._find_variables_block_range(lines)

        if var_block_start is None:
            # Create variables block
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

            # Find the end of the definition (searching for };)
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

                if found_open and brace_count == 0 and "};" in line:
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

    def _fix_extern_keyword(self, content: str, issues: List[InternalIssue]) -> str:
        lines = content.split("\n")
        for issue in sorted(issues, key=lambda x: x.line, reverse=True):
            idx = issue.line - 1
            if idx < len(lines):
                lines[idx] = re.sub(r"\bextern\s+", "", lines[idx], count=1)
        return "\n".join(lines)

    def _fix_missing_type_keyword(self, content: str, issues: List[InternalIssue]) -> str:
        lines = content.split("\n")
        for issue in sorted(issues, key=lambda x: x.line, reverse=True):
            idx = issue.line - 1
            if idx < len(lines):
                keyword = "enum" if "enum" in issue.rule_id else "struct"
                # Extraction of type name from message is a bit hacky but consistent with old logic
                match = re.search(r"Type '(\w+)'", issue.message)
                if match:
                    type_name = match.group(1)
                    pattern = rf"(?<!\b{keyword}\s)\b{type_name}\b"
                    lines[idx] = re.sub(pattern, f"{keyword} {type_name}", lines[idx], count=1)
        return "\n".join(lines)

    def _fix_variable_outside_block(self, content: str, issues: List[InternalIssue]) -> str:
        lines = content.split("\n")
        var_block_start, var_block_end = self._find_variables_block_range(lines)

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

        # Collect variables to move (sort by line number descending)
        to_move = sorted(issues, key=lambda x: x.line, reverse=True)

        for issue in to_move:
            line_idx = issue.line - 1
            if line_idx >= len(lines):
                continue

            var_line = lines.pop(line_idx)
            if line_idx < var_block_end:
                var_block_end -= 1

            lines.insert(var_block_end, "  " + var_line.strip())
            var_block_end += 1

        return "\n".join(lines)

    def _fix_variable_mid_block(self, content: str, issues: List[InternalIssue]) -> str:
        lines = content.split("\n")

        # Group issues by parent function/testcase
        by_parent: Dict[str, List[InternalIssue]] = {}
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

    def _fix_function_declaration(self, content: str, issues: List[InternalIssue]) -> str:
        lines = content.split("\n")
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

    # Helpers
    def _find_variables_block_range(self, lines: List[str]):
        start = end = None
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

    def _find_function_start(self, lines: List[str], func_name: str) -> Optional[int]:
        if not func_name or func_name == "unknown":
            return None
        # Exact match for function name in signature
        for i, line in enumerate(lines):
            if func_name in line and ("(" in line or "{" in line):
                return i
        return None
