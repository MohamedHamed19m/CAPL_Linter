# Specification: Comprehensive Comment Handling for CAPL Formatter

## 1. Overview
This track aims to implement a robust, AST-aware comment handling system within the `capl-formatter`. The goal is to ensure 100% comment preservation, stable placement/association with code nodes, automatic reflowing of long comments, and vertical alignment of inline comments.

## 2. Goals & Functional Requirements

### 2.1 Comment Preservation & Placement
*   **100% Preservation:** No comment (line `//` or block `/* ... */`) shall be lost during any formatting pass.
*   **AST-Based Attachment:** Comments must be associated with their nearest relevant AST nodes.
*   **Phase-Aware Preservation:** Structural rules (e.g., `BlockExpansionRule`) must explicitly handle comments.

### 2.2 Comment Reflowing
*   **Line Length Limit:** Automatically wrap comment lines exceeding `line_length` (default 100 characters).
*   **Wrapping Style:** "Match Start" alignment.
*   **Block Comment Handling:** Support reflowing for single and multi-line blocks.

### 2.3 Comment Alignment
*   **Inline Alignment:** Vertically align inline comments across consecutive lines.

## 3. Non-Functional Requirements
*   **Idempotency:** Formatting a file twice must result in the same output.
*   **Performance:** < 10% formatting speed degradation.

## 4. Special Cases & Constraints
*   **Doxygen/Documentation:** Do not reflow blocks with tags like `@param`.
*   **ASCII Art/Diagrams:** Detect and skip reflowing for comments containing diagram-like structures.
*   **Pragmas/Macros:** Leave comments on lines starting with `#` untouched.

## 5. Technical Architecture

### 5.1 Phase Integration
*   **Phase 0: Pre-Processing** (New): Build `comment_attachment_map` in `engine.py`.
*   **Phase 1: Structural Convergence** (Modified): `BlockExpansionRule` and `StatementSplitRule` check `context.metadata['comment_attachments']` to move comments with nodes.
*   **Phase 2: Whitespace Cleanup** (Modified): `_cleanup_vertical_whitespace` uses `comment_attachments` to preserve header comment proximity.
*   **Phase 3: Final Polish** (Modified): `CommentAlignmentRule` runs here. `CommentReflowRule` moved here.

## 6. Data Structures

### 6.1 `CommentAttachment` (models.py)
```python
@dataclass
class CommentAttachment:
    comment_node: Node              # Tree-sitter node
    attachment_type: Literal['header', 'inline', 'footer', 'standalone', 'section']
    target_node: Optional[Node]     # Associated code node
    comment_line: int               # Line number
    target_line: int                # Target's line number
    distance: int                   # Lines between comment and target
```

### 6.2 Enhanced `FormattingContext` (rules/base.py)
```python
@dataclass
class FormattingContext:
    # Existing fields...
    metadata: Dict[str, Any] = None  # For comment_attachments
```

### 6.3 Enhanced `FormatterConfig` (models.py)
```python
@dataclass
class FormatterConfig:
    # Existing fields...
    align_inline_comments: bool = True
    inline_comment_column: int = 40
    reflow_comments: bool = True
    preserve_comment_proximity: bool = True
```

## 7. Implementation Checklist

### 7.1 Files to Modify
*   **`engine.py`**: Add `_build_comment_attachment_map`, inject `metadata` into context, update `_cleanup_vertical_whitespace` to use map, add/move Phase 3 rules.
*   **`rules/base.py`**: Update `FormattingContext` to include `metadata`.
*   **`models.py`**: Add `CommentAttachment` dataclass, update `FormatterConfig`.
*   **`rules/block_expansion.py`**: Add comment-awareness to brace expansion logic.
*   **`rules/splitting.py`**: Add inline comment checks to splitting logic.
*   **`rules/comments.py`**: Implement `CommentAlignmentRule`, update `CommentReflowRule` with exclusions.

## 8. Test Strategy

### 8.1 Unit Tests (`tests/test_comments.py`)
*   `test_header_comment_proximity`: Verify no blank line between comment and function.
*   `test_inline_comment_preservation`: Verify comments stay on same line.
*   `test_inline_comment_alignment`: Verify alignment to column.
*   `test_block_expansion_with_inline_comment`: Verify expansion keeps comments.
*   `test_comment_reflow_long_line`: Verify wrapping.
*   `test_doxygen_preservation`: Verify `@param` ignored.
*   `test_ascii_art_preservation`: Verify diagrams ignored.
*   `test_section_divider_preservation`: Verify `//===` ignored.

### 8.2 Golden File Tests
*   Create `tests/fixtures/input/comments_comprehensive.can` and `expected/comments_comprehensive.can` covering all scenarios.

## 9. Edge Cases & Error Handling
*   **Malformed Comments:** Skip reflow for unclosed block comments.
*   **Mixed Styles:** Handle inline after block comments correctly.
*   **Very Long Lines:** Don't wrap single words > line_length. Move inline comments > line_length * 1.5 to header.
*   **Empty Comments:** Preserve `//` and `/**/`.
*   **International:** Support UTF-8/Emoji in length/alignment calculations.
*   **Error Recovery:** Skip processing on AST errors or overlapping transformations.

## 10. Configuration & Migration
*   **Defaults:** All new features enabled.
*   **Opt-Out:** Users can disable via config.
*   **Migration:** Existing golden files should pass; snapshots may need updates.
