# CAPL Linter Package Context

## Overview
The `capl-linter` package is a multi-pass static analysis engine for CAPL. It combines AST-based syntax checking with database-driven semantic analysis to identify both structural violations and logic errors (e.g., undefined symbols).

## Architecture: Multi-Pass Pipeline
To achieve high accuracy and project-wide awareness, the linter follows a structured sequence:

1.  **Parsing & Fact Extraction**: `SymbolExtractor` parses the source into an AST and records "Neutral Facts" (symbols, types, includes) into `aic.db`.
2.  **Dependency Resolution**: The database resolves transitive includes to build a project-wide visibility graph.
3.  **Rule Execution**: `LinterEngine` runs registered rules.
    *   **Syntax Rules**: Direct AST traversal (e.g., arrow operator detection).
    *   **Semantic Rules**: Database queries against the visibility graph (e.g., undefined symbol check).
4.  **Auto-Correction (Optional)**: `AutoFixEngine` applies rule-specific transformations iteratively until the file reaches a stable state.

## Core Rules Reference

| ID | Name | Implementation | Description |
| :--- | :--- | :--- | :--- |
| **E001** | `extern-keyword` | `rules/syntax_rules.py` | Detects and removes the unsupported `extern` keyword. |
| **E002** | `function-declaration` | `rules/syntax_rules.py` | Detects and removes function forward declarations. |
| **E003** | `global-type-definition`| `rules/syntax_rules.py` | Moves `struct`/`enum` definitions into the `variables {}` block. |
| **E004** | `missing-enum-keyword` | `rules/type_rules.py` | Ensures `enum` keyword is present in variable declarations. |
| **E005** | `missing-struct-keyword`| `rules/type_rules.py` | Ensures `struct` keyword is present in variable declarations. |
| **E006** | `variable-outside-block`| `rules/variable_rules.py`| Moves global variables into the `variables {}` block. |
| **E007** | `variable-mid-block` | `rules/variable_rules.py`| Moves local variables to the start of the function body. |
| **E008** | `arrow-operator` | `rules/syntax_rules.py` | Replaces `->` with `.` (arrow operator not supported). |
| **E009** | `pointer-parameter` | `rules/syntax_rules.py` | Flags forbidden pointer parameters (except ethernetpacket*). |
| **E011** | `undefined-symbol` | `rules/semantic_rules.py` | Identifies symbols used but not defined in visible scope. |
| **E012** | `duplicate-function` | `rules/semantic_rules.py` | Flags project-wide duplicate function definitions. |
| **W001** | `circular-include` | `rules/semantic_rules.py` | Warns about circular include dependencies. |

## Design Principles & Invariants
1.  **Database-First Truth**: Rules requiring cross-file knowledge (e.g., E011, E012) MUST query the `SymbolDatabase`, not attempt to parse other files on the fly.
2.  **Atomic Fixes (Collect-Remove-Insert)**: Rules that move code (E003, E006, E007) must use the **Collect-Remove-Insert** pattern:
    *   **Collect**: Identify all lines to move.
    *   **Remove**: Delete them from original positions (bottom-up to preserve indices).
    *   **Insert**: Place them in the target block in their original relative order.
3.  **Fact Neutrality**: The extractor records state without judgment. The linter rule performs the validation.
4.  **Syntax Preservation**: An auto-fix MUST NOT introduce a tree-sitter `ERROR` node.
5.  **Severity Hierarchy**: `ERROR` rules block compilation; `WARNING` rules suggest improvements but allow execution.

## Testing Strategy
Any new rule or bug fix MUST be accompanied by both snapshot and golden file tests.

### 1. Snapshot Testing (Detection)
Snapshots track exactly what issues are reported for a given source snippet.
*   **File**: `src/capl_linter/tests_linter/test_linter_snapshots.py`
*   **Command**: `uv run pytest src/capl_linter/tests_linter/test_linter_snapshots.py --snapshot-update`

### 2. Golden File Testing (Correction)
Golden files verify that auto-fixes produce the exact desired source code.
*   **Workflow**:
    1.  Place messy code in `src/capl_linter/tests_linter/fixtures/input/<rule_name>.can`.
    2.  Place expected fixed code in `src/capl_linter/tests_linter/fixtures/expected/<rule_name>.can`.
*   **Note**: Linter golden tests automatically run a `FormatterEngine` pass after fixes to ensure high-quality output style.

## Troubleshooting & Debugging Workflow

### Step 1: Isolate the AST
If a rule isn't firing, see how tree-sitter sees the code:
Create debug_ast.py and execute it.
```bash
uv run python debug_ast.py
```
Check for `ERROR` nodes or unexpected nesting that might be breaking your AST traversal.

### Step 2: Inspect the Database
For semantic rules (E011, E012), check if the facts are correctly stored:
```bash
sqlite3 aic.db "SELECT * FROM symbols WHERE symbol_name = 'your_func';"
```

### Step 3: Trace Auto-Fixes
If an auto-fix corrupts the file, it's usually an index shift issue. Verify that the rule is sorting line modifications in reverse order or using the Collect-Remove-Insert pattern.

### Step 4: Verify Convergence
Run the linter twice on the same file. If it reports new issues or makes new changes on the second pass, the rule is unstable and lacks idempotency.
