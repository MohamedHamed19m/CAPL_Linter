from typing import List, Union
from pathlib import Path
import re
from .models import FormatterConfig, FormatResult, FormatResults
from .rules.base import FormattingRule, ASTRule, TextRule, FormattingContext, Transformation
from capl_tree_sitter.parser import CAPLParser

class FormatterEngine:
    """Core engine for formatting CAPL files using AST transformations."""
    def __init__(self, config: FormatterConfig):
        self.config = config
        self.rules: List[FormattingRule] = []
        self.parser = CAPLParser()

    def add_rule(self, rule: FormattingRule) -> None:
        """Register a new formatting rule."""
        self.rules.append(rule)

    def format_string(self, source: str, file_path: str = "") -> FormatResult:
        """Formats a CAPL string through iterative structural passes and final indentation."""
        source = source.replace('\r\n', '\n')
        current_source = source
        modified = False
        errors = []

        try:
            # Phase 1: Structural Convergence
            # We re-parse after each rule to ensure subsequent rules work on a valid AST.
            max_passes = 2
            for i in range(max_passes):
                pass_modified = False
                for rule in self.rules:
                    parse_result = self.parser.parse_string(current_source)
                    context = FormattingContext(source=current_source, file_path=file_path, tree=parse_result.tree)
                    transforms = rule.analyze(context)
                    if transforms:
                        new_source = self._apply_transformations(current_source, transforms)
                        if new_source != current_source:
                            current_source = new_source
                            pass_modified = True
                            modified = True
                if not pass_modified: break
            
            # Phase 2: Vertical Whitespace Normalization
            current_source = self._cleanup_vertical_whitespace(current_source)
            
            # Phase 3: Final Indentation Pass
            parse_result = self.parser.parse_string(current_source)
            context = FormattingContext(source=current_source, file_path=file_path, tree=parse_result.tree)
            from .rules.indentation import IndentationRule
            indent_rule = IndentationRule(self.config)
            indent_transforms = indent_rule.analyze(context)
            if indent_transforms:
                current_source = self._apply_transformations(current_source, indent_transforms)
                modified = True
                    
        except Exception as e:
            import traceback
            errors.append(f"{str(e)}\n{traceback.format_exc()}")

        return FormatResult(source=current_source, modified=modified, errors=errors)

    def _cleanup_vertical_whitespace(self, source: str) -> str:
        """Standardizes blank lines at block boundaries and between items."""
        # 1. Collapse multiple blank lines to max 1
        source = re.sub(r'\n{3,}', r'\n\n', source)
        # 2. Remove blank lines at start of blocks
        source = re.sub(r'\{\s*\n\s*\n+', r'{\n', source)
        # 3. Remove blank lines at end of blocks
        source = re.sub(r'\n\s*\n+\s*\}', r'\n}', source)
        # 4. Remove blank lines after case/default labels
        source = re.sub(r':\s*\n\s*\n+', r':\n', source)
        return source

    def _apply_transformations(self, source: str, transforms: List[Transformation]) -> str:
        """Applies non-overlapping character-based transformations in a single pass."""
        sorted_transforms = sorted(transforms, key=lambda t: (t.start_byte, t.end_byte, t.priority))
        result = []; last_offset = 0
        for t in sorted_transforms:
            if t.start_byte < last_offset: continue
            result.append(source[last_offset:t.start_byte])
            result.append(t.new_content)
            last_offset = t.end_byte
        result.append(source[last_offset:])
        return "".join(result)

    def format_files(self, files: List[Path]) -> FormatResults:
        """Batch format multiple files on disk."""
        results = []; modified_count = 0; error_count = 0
        for file_path in files:
            try:
                source = file_path.read_text(encoding="utf-8")
                result = self.format_string(source, str(file_path))
                results.append(result)
                if result.errors: error_count += 1
                elif result.modified:
                    modified_count += 1
                    file_path.write_text(result.source, encoding="utf-8")
            except Exception as e:
                results.append(FormatResult(source="", modified=False, errors=[str(e)]))
                error_count += 1
        return FormatResults(results=results, total_files=len(files), modified_files=modified_count, error_files=error_count)
