# CAPL Formatter Package Context

## Overview
The `capl-formatter` package is a robust, AST-based code formatting engine for CAPL. It leverages `tree-sitter-c` for structural analysis and employs atomic, character-based transformations to ensure high stability and idempotency.

## Architecture: Three-Phase "Artisan" Strategy
To achieve "Ruff/Black" level quality, the engine executes formatting in a specific sequence:

1.  **Pre-processing (Normalization)**:
    *   **Goal**: Ensure a clean starting state.
    *   **Logic**: `_normalize_top_level_indentation` identifies true top-level nodes (declarations, functions) using the AST and forces them to column 0.
2.  **Phase 1: Structural Convergence (Iterative)**:
    *   **Goal**: Resolve changes that modify the AST structure.
    *   **Rules**: Spacing, Splitting, Expansion, Switch Normalization.
    *   **Stability**: The engine re-parses the source after each rule application to maintain AST accuracy.
3.  **Phase 2: Vertical Whitespace Normalization**:
    *   **Goal**: Eliminate redundant blank lines.
    *   **Logic**: `_cleanup_vertical_whitespace` uses whitespace-aware regexes (e.g., `\n\s*\n+`) to catch blank lines even if they contain indentation spaces left by previous passes.
4.  **Phase 3: Final Indentation Pass**:
    *   **Goal**: Precise alignment.
    *   **Rule**: `IndentationRule` calculates the **minimum** depth of any token starting on a line to determine that line's indentation. This prevents inner tokens (like a struct name) from incorrectly pushing the outer declaration (the `struct` keyword) inward.

## Core Rules Reference
*   **`F001: WhitespaceCleanupRule`** (`rules/whitespace.py`): Cleans trailing whitespace and collapses global blank lines.
*   **`F002: IndentationRule`** (`rules/indentation.py`): AST-depth based alignment with special handling for switch/case.
*   **`F003: BraceStyleRule`** (`rules/structure.py`): Enforces K&R brace style (opening brace on same line).
*   **`F004: SpacingRule`** (`rules/spacing.py`): Normalizes spaces around operators, keywords, and parentheses.
*   **`F005: BlockExpansionRule`** (`rules/block_expansion.py`): Expands single-line blocks, structs, and enums into multi-line.
*   **`F006: StatementSplitRule`** (`rules/splitting.py`): Splits consecutive statements on the same line (skips structs/enums). Treat comments as statement delimiters.
*   **`F007: SwitchNormalizationRule`** (`rules/switch.py`): Ensures case labels and bodies are correctly separated.
*   **`F012: CommentReflowRule`** (`rules/comments.py`): Wraps long comments to fit `line_length`. Excludes Doxygen and ASCII art.
*   **`F013: CommentAlignmentRule`** (`rules/comments.py`): Vertically aligns consecutive inline comments.

## Common Anti-patterns to Avoid
*   **Regex for Structural Changes**: Do not use regex to find where to add braces or split lines; use the AST to find the exact node boundaries.
*   **Hardcoded Indentation Strings**: Never use `"\t"` or `"    "` directly in rules. Use `context.config.indent_size` or helper methods from `base.py`.
*   **Overlapping Transformations**: Avoid creating two transformations that touch the same byte range in one rule pass. This causes the engine to fail or produce corrupted text.
*   **Ignoring `ERROR` Nodes**: If a rule encounters an `ERROR` node in the AST, it should generally bail out or be extremely conservative to avoid corrupting invalid code.
*   **Manual Comment Alignment**: Do not manually align comments with spaces; the formatter handles vertical alignment automatically.
*   **Manual Doxygen Wrapping**: Avoid wrapping Doxygen blocks manually as the formatter specifically excludes them to preserve documentation structure.

## Design Principles & Invariants
To maintain high quality, every rule and modification must adhere to these invariants:
1.  **AST Neutrality**: Formatting MUST NOT change the semantic meaning of the code. The AST of the formatted code (excluding whitespace/comments) should be identical to the original.
2.  **Idempotency**: `format(format(code)) == format(code)`. If the second pass makes changes, the rules are unstable.
3.  **Atomic Transformations**: Rules should return a list of `Transformation` objects rather than modifying strings directly. This prevents offset drift during a single pass.
4.  **Minimalism**: Only touch what is necessary. If a line already matches the target style, do not generate a transformation for it.

## Measurable Outcomes
Success is defined by the following metrics:
*   **Zero ERROR Nodes**: The formatted output must still be valid CAPL and parse without `ERROR` nodes in `tree-sitter`.
*   **Convergence Rate**: 95% of files should reach a stable state (idempotency) within 2 passes. Maximum allowed passes is 10.
*   **No Regression**: Existing test cases in `src/capl_formatter/tests_formatter/` must pass after any rule change.

## Testing Strategy
To maintain the high stability of the formatter, any new rule or bug fix MUST be accompanied by tests.

### 1. Snapshot Testing (Regression)
Snapshot tests catch any change in the formatter's output. They are the primary defense against regressions.
*   **File**: `src/capl_formatter/tests_formatter/test_formatting_snapshots.py`
*   **How to add**: Add a new test method to `TestFormattingSnapshots` class.
*   **Workflow**:
    *   `uv run pytest src/capl_formatter/tests_formatter/test_formatting_snapshots.py --snapshot-update` to generate/update snapshots.
    *   Review the changes in the `snapshots/` directory before committing.

### 2. Golden File Testing (Correctness)
Golden file tests compare the formatter against "perfect" hand-written reference files.
*   **File**: `src/capl_formatter/tests_formatter/test_golden_files.py`
*   **Fixtures**:
    *   `src/capl_formatter/tests_formatter/fixtures/input/*.can`: Messy input code.
    *   `src/capl_formatter/tests_formatter/fixtures/expected/*.can`: Correctly formatted output.
*   **How to add**: Just drop matching `.can` files into the `input/` and `expected/` directories. The test runner will automatically pick them up.

### 3. Rule-Specific Unit Tests
For complex logic, use rule-specific tests (e.g., `test_indentation.py`, `test_spacing.py`).
*   **Best Practice**: Use `engine.add_default_rules()` to test the rule in the context of the full pipeline, or add just the specific rule for isolation.

## Troubleshooting & Debugging
### Identifying Issues
*   **Indented Top-Level Items**: Usually means the node wasn't caught by normalization or `IndentationRule` calculated an incorrect minimum depth.
*   **Double Newlines**: Often a conflict between `StatementSplitRule` and `BlockExpansionRule`. Verify that `StatementSplitRule` is correctly skipping the block type.
*   **"Invisible" Blank Lines**: If a blank line won't disappear, it likely contains spaces (e.g., `\n  \n`). Ensure the cleanup regexes account for `\s*`.

### Debugging Workflow
1.  **AST Inspection**: Use a dump script to see if `tree-sitter` is producing `ERROR` nodes or unexpected nesting (often caused by missing semicolons in CAPL).
2.  **Transformation Tracing**: Add prints to `FormatterEngine._apply_transformations` to see exactly which rule is inserting characters at specific offsets.
3.  **Depth Tracing**: Print the `current_depth` in `IndentationRule.traverse` to verify the nesting logic.

## Best Practices for Debugging Issues

### Step 1: Isolate the Problem (ALWAYS START HERE)
**Create Minimal Test Case**
```python
# test_issue.can
struct A{int x;}  // Keep only the problematic code
```

**Disable All Rules Except One**
```python
# In main.py or test file
engine = FormatterEngine(config)
# engine.add_rule(BlockExpansionRule(config))
engine.add_rule(IndentationRule(config))  # Test only this
# engine.add_rule(SpacingRule(config))

result = engine.format_string(test_source)
```
**Purpose:** Identify which specific rule causes the issue.

### Step 2: Inspect the AST
**Create Debug Script**
```python
# dump_ast.py
from capl_tree_sitter.parser import CAPLParser

parser = CAPLParser()
source = open('test_issue.can').read()
result = parser.parse_string(source)

print(result.tree.root_node.sexp())  # Show full tree structure
```

**What to Look For:**
*   ❌ `ERROR` nodes → Syntax issues (missing semicolons, braces)
*   ❌ Unexpected nesting → Wrong parent/child relationships
*   ❌ Missing nodes → Declarations not parsed

**Common CAPL Syntax Issues:**
```c
// WRONG: Missing semicolon after struct
struct Point{int x;}  // ← No semicolon causes ERROR node

// CORRECT
struct Point{int x;};  // ← With semicolon
```

### Step 3: Trace Transformations
**Add Debug to `engine.py`**
```python
def _apply_transformations(self, source: str, transforms: List[Transformation]) -> str:
    sorted_transforms = sorted(transforms, key=lambda t: (t.start_byte, t.end_byte, t.priority))
    
    print(f"\n=== Applying {len(transforms)} transformations ===")
    for t in sorted_transforms:
        old_text = source[t.start_byte:t.end_byte]
        context = source[max(0, t.start_byte-10):t.end_byte+10]
        print(f"  @ {t.start_byte:4d}-{t.end_byte:4d}: '{old_text}' → '{t.new_content}'")
        print(f"       Context: ...{context}..." )
    
    # ... rest of method
```
**Purpose:** See exactly what's being inserted/deleted where.

### Step 4: Trace Depth Calculation (Indentation Issues)
**Add Debug to `indentation.py`**
```python
def traverse(node, current_depth):
    start_row = node.start_point[0]
    
    # DEBUG: Show depth calculation
    if node.type not in ['{', '}', ';', ',', '(', ')']:
        indent = "  " * current_depth
        print(f"{indent}Line {start_row}: {node.type} at depth {current_depth}")
    
    # Record depth
    if start_row not in line_depths or current_depth < line_depths[start_row]:
        print(f"  → Set line {start_row} depth = {current_depth}")
        line_depths[start_row] = current_depth
    
    # ... rest of logic
```
**Purpose:** Verify depth calculations are correct for each line.

**What to Look For:**
```text
Line 0: struct_specifier at depth 0
  → Set line 0 depth = 0        # ✅ Correct
Line 0: type_identifier at depth 1
  (depth NOT updated, 0 < 1)    # ✅ Correct (using min)
```

### Step 5: Verify Regex Patterns (Blank Line Issues)
**Add Debug to `_cleanup_vertical_whitespace`**
```python
def _cleanup_vertical_whitespace(self, source: str) -> str:
    print("\n=== Blank Line Analysis ===")
    lines = source.split('\n')
    
    for i, line in enumerate(lines):
        if not line.strip():
            print(f"Line {i}: BLANK (len={len(line)}, repr={repr(line)})")
    
    # ... rest of cleanup
```
**Purpose:** See if blank lines contain hidden spaces.

**What to Look For:**
*   `Line 5: BLANK (len=0, repr='')`      # ✅ True blank
*   `Line 8: BLANK (len=4, repr='    ')`  # ❌ Indented blank (needs normalization)

### Step 6: Check Rule Execution Order
**Add Debug to Main Loop**
```python
for i in range(max_passes):
    print(f"\n=== PASS {i+1} ===")
    pass_modified = False
    
    for rule in self.rules:
        print(f"\nApplying: {rule.name}")
        transforms = rule.analyze(context)
        print(f"  Generated {len(transforms)} transformations")
        
        if transforms:
            new_source = self._apply_transformations(current_source, transforms)
            if new_source != current_source:
                print(f"  ✓ Source modified")
                pass_modified = True
```
**Purpose:** Verify rules run in correct order and identify conflicts.



### Emergency Debugging Checklist
When encountering a formatting issue:

 Step 1: Create minimal test case (≤5 lines)
 Step 2: Run dump_ast.py → Check for ERROR nodes
 Step 3: Disable all rules except one → Find culprit
 Step 4: Add transformation trace → See byte offsets
 Step 5: Add depth trace (if indentation) → Verify calculations
 Step 6: Add blank line trace (if spacing) → Find hidden spaces
 Step 7: Run formatter twice → Test idempotency
 Step 8: Review RULES 1-7 → Ensure compliance
