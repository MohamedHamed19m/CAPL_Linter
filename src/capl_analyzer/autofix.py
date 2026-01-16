"""
Auto-fix system for CAPL linter
"""

import sqlite3
from pathlib import Path
from typing import Dict, List, Optional
import re
from .linter import LintIssue


class AutoFixer:
    """Automatically fix linting issues"""

    def __init__(self, db_path: str = "aic.db"):
        self.db_path = db_path
        self.fixes = {
            "variable-outside-block": self._fix_variable_outside_block,
            "variable-mid-block": self._fix_variable_mid_block,
            "missing-enum-keyword": self._fix_missing_type_keyword,
            "missing-struct-keyword": self._fix_missing_type_keyword,
            'function-declaration': self._fix_function_declaration,
            'global-enum-definition': self._fix_global_type_definition,
            'global-struct-definition': self._fix_global_type_definition,
            'extern-keyword': self._fix_extern_keyword,
        }
    
    def can_fix(self, rule_id: str) -> bool:
        """Check if a rule can be auto-fixed"""
        return rule_id in self.fixes 
    
    def apply_fixes(self, file_path: str, issues: List[LintIssue]) -> str:
        """
        Apply a batch of issues (usually of the same rule type) to a file
        """
        if not issues:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
                
        # We assume all issues are for the same file
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # All issues should be of the same rule_id for safety in this pass
        rule_id = issues[0].rule_id
        if self.can_fix(rule_id):
            fix_func = self.fixes[rule_id]
            content = fix_func(content, issues, file_path)
            
        return content
    
    def _fix_extern_keyword(self, content: str, issues: List[LintIssue],
                            file_path: str) -> str:
        """
        Remove 'extern' keyword from declaration lines
        """
        lines = content.split('\n')
        # Sort issues bottom-up to preserve line numbers if multiple on same line (unlikely for extern)
        for issue in sorted(issues, key=lambda x: x.line_number, reverse=True):
            line_idx = issue.line_number - 1
            if line_idx >= len(lines): continue
            
            # Use regex to remove 'extern' keyword and any leading space
            lines[line_idx] = re.sub(r'\bextern\s+', '', lines[line_idx], count=1)
            
        return '\n'.join(lines)

    def _fix_variable_outside_block(
        self, content: str, issues: list[LintIssue], file_path: str
    ) -> str:
        """
        Move variables declared outside variables {} block into it
        """
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
        to_move = sorted(issues, key=lambda x: x.line_number, reverse=True)

        for issue in to_move:
            line_idx = issue.line_number - 1
            if line_idx >= len(lines):
                continue

            # Verify it's a variable declaration (roughly)
            line_text = lines[line_idx].strip()
            if not line_text or line_text.startswith("//"):
                continue

            var_line = lines.pop(line_idx)
            if line_idx < var_block_end:
                var_block_end -= 1

            lines.insert(var_block_end, "  " + var_line.strip())
            var_block_end += 1

        return "\n".join(lines)

    def _fix_global_type_definition(
        self, content: str, issues: list[LintIssue], file_path: str
    ) -> str:
        """
        Move enum/struct definitions into variables {} block
        """
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
        for issue in sorted(issues, key=lambda x: x.line_number, reverse=True):
            start_line_idx = issue.line_number - 1
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

    def _fix_variable_mid_block(self, content: str, issues: list[LintIssue], file_path: str) -> str:
        """
        Move variables declared mid-block to the start of the block
        """
        lines = content.split("\n")

        # Group issues by parent function/testcase
        by_parent = {}
        for issue in issues:
            parent = self._get_parent_function(file_path, issue.line_number)
            if parent:
                if parent not in by_parent:
                    by_parent[parent] = []
                by_parent[parent].append(issue)

        # Process parents in descending order of their first issue to be safe-ish
        # but iterative passes are safer.
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
            for issue in sorted(parent_issues, key=lambda x: x.line_number, reverse=True):
                line_idx = issue.line_number - 1
                if line_idx >= len(lines):
                    continue

                # Verify it's a declaration? (Not strictly necessary if re-analyzed)
                to_move_lines.append(lines.pop(line_idx).strip())

            # Insert at body start
            for var_line in reversed(to_move_lines):
                lines.insert(body_start_idx, "  " + var_line)

        return "\n".join(lines)

    def _fix_missing_type_keyword(
        self, content: str, issues: list[LintIssue], file_path: str
    ) -> str:
        """Add missing enum/struct keyword"""
        lines = content.split("\n")
        for issue in sorted(issues, key=lambda x: x.line_number, reverse=True):
            line_idx = issue.line_number - 1
            if line_idx >= len(lines):
                continue

            keyword = "enum" if "enum" in issue.rule_id else "struct"
            match = re.search(r"Type '(\w+)'", issue.message)
            if match:
                type_name = match.group(1)
                pattern = rf"(?<!\b{keyword}\s)\b{type_name}\b"
                lines[line_idx] = re.sub(
                    pattern, f"{keyword} {type_name}", lines[line_idx], count=1
                )
        return "\n".join(lines)

    def _fix_function_declaration(
        self, content: str, issues: list[LintIssue], file_path: str
    ) -> str:
        """Remove function declarations"""
        lines = content.split("\n")
        for issue in sorted(issues, key=lambda x: x.line_number, reverse=True):
            line_idx = issue.line_number - 1
            if line_idx >= len(lines):
                continue

            if ";" in lines[line_idx]:
                lines.pop(line_idx)
            else:
                for i in range(line_idx, min(line_idx + 5, len(lines))):
                    if ";" in lines[i]:
                        for _ in range(i - line_idx + 1):
                            lines.pop(line_idx)
                        break
        return "\n".join(lines)

    # Helpers
    def _find_variables_block_range(self, lines: list[str]):
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

    def _get_parent_function(self, file_path: str, line_number: int) -> str | None:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    """
                    SELECT s.parent_symbol FROM symbols s
                    JOIN files f ON s.file_id = f.file_id
                    WHERE f.file_path = ? AND s.line_number = ?
                """,
                    (str(Path(file_path).resolve()), line_number),
                )
                result = cursor.fetchone()
                return result[0] if result else None
        except sqlite3.Error:
            return None

    def _find_function_start(self, lines: list[str], func_name: str) -> int | None:
        if not func_name:
            return None
        clean_name = func_name
        if clean_name.startswith("testcase "):
            clean_name = clean_name.replace("testcase ", "").strip()
        elif clean_name.startswith("on "):
            pass
        
        # Exact match for function name in signature
        for i, line in enumerate(lines):
            if clean_name in line and ("(" in line or "{" in line):
                return i
        return None
