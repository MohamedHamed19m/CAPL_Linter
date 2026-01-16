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

    def _fix_extern_keyword(self, content: str, issues: List[InternalIssue]) -> str:
        lines = content.split('\n')
        for issue in sorted(issues, key=lambda x: x.line, reverse=True):
            idx = issue.line - 1
            if idx < len(lines):
                lines[idx] = re.sub(r'\bextern\s+', '', lines[idx], count=1)
        return '\n'.join(lines)

    def _fix_missing_type_keyword(self, content: str, issues: List[InternalIssue]) -> str:
        lines = content.split('\n')
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
        return '\n'.join(lines)

    def _fix_variable_outside_block(self, content: str, issues: List[InternalIssue]) -> str:
        # Complex logic to be migrated fully
        return content

    def _fix_variable_mid_block(self, content: str, issues: List[InternalIssue]) -> str:
        return content

    def _fix_function_declaration(self, content: str, issues: List[InternalIssue]) -> str:
        return content
