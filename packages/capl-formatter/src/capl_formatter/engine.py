from typing import List, Union, Dict, Any
from pathlib import Path
import re
from .models import FormatterConfig, FormatResult, FormatResults, CommentAttachment
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

    def add_default_rules(self) -> None:
        """Register all default formatting rules in the recommended order."""
        from .rules import (
            QuoteNormalizationRule,
            IncludeSortingRule,
            VariableOrderingRule,
            # CommentReflowRule,  # Moved to Phase 4
            IntelligentWrappingRule,
            BlockExpansionRule,
            StatementSplitRule,
            SwitchNormalizationRule,
            BraceStyleRule,
            SpacingRule,
            VerticalSpacingRule,
            IndentationRule,
            WhitespaceCleanupRule,
        )

        self.add_rule(QuoteNormalizationRule(self.config))
        self.add_rule(IncludeSortingRule(self.config))
        self.add_rule(VariableOrderingRule(self.config))
        # self.add_rule(CommentReflowRule(self.config))
        self.add_rule(IntelligentWrappingRule(self.config))
        self.add_rule(BlockExpansionRule(self.config))
        self.add_rule(StatementSplitRule(self.config))
        self.add_rule(SwitchNormalizationRule(self.config))
        self.add_rule(BraceStyleRule(self.config))
        self.add_rule(SpacingRule(self.config))
        self.add_rule(VerticalSpacingRule(self.config))
        # Note: IndentationRule and WhitespaceCleanupRule are handled
        # explicitly in Phases 2 and 3 of format_string.

    def format_string(self, source: str, file_path: str = "") -> FormatResult:
        """Formats a CAPL string through iterative structural passes and final indentation."""
        source = source.replace("\r\n", "\n")

        # Pre-process: Normalize top-level indentation to 0
        source = self._normalize_top_level_indentation(source)

        current_source = source
        modified = False
        errors = []

        try:
            # Phase 1: Structural Convergence
            max_passes = 5
            for i in range(max_passes):
                pass_modified = False
                for rule in self.rules:
                    parse_result = self.parser.parse_string(current_source)

                    # Phase 0: Build comment attachment map for this iteration
                    comment_map = self._build_comment_attachment_map(
                        current_source, parse_result.tree
                    )

                    context = FormattingContext(
                        source=current_source,
                        file_path=file_path,
                        tree=parse_result.tree,
                        metadata={"comment_attachments": comment_map},
                    )

                    transforms = rule.analyze(context)
                    if transforms:
                        new_source = self._apply_transformations(current_source, transforms)
                        if new_source != current_source:
                            current_source = new_source
                            pass_modified = True
                            modified = True
                if not pass_modified:
                    break

            # Phase 2: Vertical Whitespace Normalization
            from .rules.whitespace import WhitespaceCleanupRule

            # Build map for whitespace cleanup (requires fresh parse)
            parse_result_ws = self.parser.parse_string(current_source)
            comment_map_ws = self._build_comment_attachment_map(
                current_source, parse_result_ws.tree
            )

            current_source = self._cleanup_vertical_whitespace(current_source, comment_map_ws)

            ws_rule = WhitespaceCleanupRule(self.config)
            ws_transforms = ws_rule.analyze(
                FormattingContext(source=current_source, file_path=file_path, tree=None)
            )
            if ws_transforms:
                current_source = self._apply_transformations(current_source, ws_transforms)
                modified = True

            # Phase 3: Final Indentation Pass
            parse_result_final = self.parser.parse_string(current_source)
            context_indent = FormattingContext(
                source=current_source, file_path=file_path, tree=parse_result_final.tree
            )
            from .rules.indentation import IndentationRule

            indent_rule = IndentationRule(self.config)
            indent_transforms = indent_rule.analyze(context_indent)
            if indent_transforms:
                current_source = self._apply_transformations(current_source, indent_transforms)
                modified = True

            # Phase 4: Comment Polish (Alignment & Reflow)
            from .rules.comments import CommentAlignmentRule, CommentReflowRule

            rules_p4 = []
            if self.config.align_inline_comments:
                rules_p4.append(CommentAlignmentRule(self.config))
            if self.config.reflow_comments:
                rules_p4.append(CommentReflowRule(self.config))

            for rule in rules_p4:
                # Fresh parse for every polish rule
                parse_result_p4 = self.parser.parse_string(current_source)
                comment_map_p4 = self._build_comment_attachment_map(
                    current_source, parse_result_p4.tree
                )
                context_p4 = FormattingContext(
                    source=current_source,
                    file_path=file_path,
                    tree=parse_result_p4.tree,
                    metadata={"comment_attachments": comment_map_p4},
                )

                transforms = rule.analyze(context_p4)
                if transforms:
                    new_source = self._apply_transformations(current_source, transforms)
                    if new_source != current_source:
                        current_source = new_source
                        modified = True

        except Exception as e:
            import traceback

            errors.append(f"{str(e)}\n{traceback.format_exc()}")

        return FormatResult(source=current_source, modified=modified, errors=errors)

    def _build_comment_attachment_map(self, source: str, tree) -> Dict[int, CommentAttachment]:
        """Builds a map of comment attachments."""
        comments = self._find_all_comments(tree)
        attachment_map = {}
        lines = source.splitlines(keepends=True)

        for comment in comments:
            attachment = self._classify_comment(comment, lines)
            attachment_map[comment.start_byte] = attachment

        return attachment_map

    def _classify_comment(self, comment_node, source_lines: List[str]) -> CommentAttachment:
        """Determines the type of comment and its target node."""
        prev_sibling = comment_node.prev_sibling
        next_sibling = comment_node.next_sibling

        comment_line = comment_node.start_point[0]

        # Check for Section Divider
        text = comment_node.text.decode("utf-8", errors="ignore").strip()
        if text.startswith("//===") or text.startswith("//---"):
            return CommentAttachment(comment_node, "section", None, comment_line, -1, 0)

        # Check Inline: Previous sibling on same line
        # Note: We loop back to skip over other comments if necessary, but simple check first
        if prev_sibling and prev_sibling.end_point[0] == comment_line:
            return CommentAttachment(
                comment_node, "inline", prev_sibling, comment_line, prev_sibling.start_point[0], 0
            )

        # Check Header: Next sibling exists
        if next_sibling:
            target_line = next_sibling.start_point[0]
            return CommentAttachment(
                comment_node,
                "header",
                next_sibling,
                comment_line,
                target_line,
                target_line - comment_line,
            )

        # Check Footer: Previous sibling exists and is on previous line
        if prev_sibling:
            target_line = prev_sibling.end_point[0]
            return CommentAttachment(
                comment_node,
                "footer",
                prev_sibling,
                comment_line,
                target_line,
                comment_line - target_line,
            )

        # Standalone
        return CommentAttachment(comment_node, "standalone", None, comment_line, -1, 0)

    def _find_all_comments(self, tree) -> List[Any]:
        """Recursively finds all comment nodes in the tree."""
        comments = []
        if not tree:
            return comments

        # Iterative traversal to avoid recursion limits
        stack = [tree.root_node]
        while stack:
            node = stack.pop()
            if node.type == "comment":
                comments.append(node)

            # Push children in reverse order to process them in original order
            stack.extend(reversed(node.children))

        return comments

    def _normalize_top_level_indentation(self, source: str) -> str:
        """Ensure all top-level declarations start at column 0."""
        try:
            parse_result = self.parser.parse_string(source)
            if not parse_result.tree or not parse_result.tree.root_node:
                return source

            lines = source.splitlines(keepends=True)
            top_level_lines = set()

            # Find all direct children of translation_unit (top-level nodes)
            for child in parse_result.tree.root_node.children:
                if child.type in ("comment", "line_comment", "block_comment", "ERROR"):
                    continue

                top_level_lines.add(child.start_point[0])

            # Rebuild source with normalized indentation
            normalized = []
            for i, line in enumerate(lines):
                if i in top_level_lines and line.strip():
                    normalized.append(line.lstrip())
                else:
                    normalized.append(line)

            return "".join(normalized)

        except Exception:
            return source

    def _cleanup_vertical_whitespace(
        self, source: str, comment_map: Dict[int, CommentAttachment] = None
    ) -> str:
        """Aggressively removes excessive blank lines BEFORE indentation."""

        # PASS 0: Comment Proximity Preservation
        if comment_map and self.config.preserve_comment_proximity:
            lines = source.splitlines(keepends=True)
            lines_to_remove = set()

            for attachment in comment_map.values():
                if attachment.attachment_type == "header" and attachment.target_node:
                    start_row = attachment.comment_line
                    end_row = attachment.target_line

                    # Remove blank lines between header comment and target
                    if end_row > start_row + 1:
                        for i in range(start_row + 1, end_row):
                            if i < len(lines) and not lines[i].strip():
                                lines_to_remove.add(i)

            if lines_to_remove:
                source = "".join([line for i, line in enumerate(lines) if i not in lines_to_remove])

        # STEP 1: Normalize indented blank lines to truly empty
        lines = source.split("\n")
        normalized = [line if line.strip() else "" for line in lines]
        source = "\n".join(normalized)

        # PASS 1: Collapse multiple blank lines globally (Max 1 blank line)
        while "\n\n\n" in source:
            source = source.replace("\n\n\n", "\n\n")

        # PASS 2: Specific Label/Enum Cleanup
        source = re.sub(r"(case\s+[^:]+:)\s*\n\n+", r"\1\n", source)
        source = re.sub(r"(default\s*:)\s*\n\n+", r"\1\n", source)
        source = re.sub(r",\n\n+", r",\n", source)

        return source

    def _apply_transformations(self, source: str, transforms: List[Transformation]) -> str:
        """Applies non-overlapping character-based transformations in a single pass."""
        sorted_transforms = sorted(transforms, key=lambda t: (t.start_byte, t.end_byte, t.priority))
        result = []
        last_offset = 0
        for t in sorted_transforms:
            if t.start_byte < last_offset:
                continue
            result.append(source[last_offset : t.start_byte])
            result.append(t.new_content)
            last_offset = t.end_byte
        result.append(source[last_offset:])
        return "".join(result)

    def format_files(self, files: List[Path]) -> FormatResults:
        """Batch format multiple files on disk."""
        results = []
        modified_count = 0
        error_count = 0
        for file_path in files:
            try:
                source = file_path.read_text(encoding="utf-8")
                result = self.format_string(source, str(file_path))
                results.append(result)
                if result.errors:
                    error_count += 1
                elif result.modified:
                    modified_count += 1
                    file_path.write_text(result.source, encoding="utf-8")
            except Exception as e:
                results.append(FormatResult(source="", modified=False, errors=[str(e)]))
                error_count += 1
        return FormatResults(
            results=results,
            total_files=len(files),
            modified_files=modified_count,
            error_files=error_count,
        )
