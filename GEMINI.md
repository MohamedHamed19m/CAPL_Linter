# CAPL Analyzer Project Context

## Quick Navigation Index

| Feature / Logic | Primary File Path |
| :--- | :--- |
| **CLI Entry Point** | `src/capl_cli/main.py` |
| **Rule Registry** | `src/capl_linter/registry.py` |
| **Linter Engine** | `src/capl_linter/engine.py` |
| **Syntax Rules** | `src/capl_linter/rules/syntax_rules.py` |
| **Type Rules** | `src/capl_linter/rules/type_rules.py` |
| **Variable Rules** | `src/capl_linter/rules/variable_rules.py` |
| **Semantic Rules** | `src/capl_linter/rules/semantic_rules.py` |
| **Formatter Engine** | `src/capl_formatter/engine.py` |
| **Ordering Rule** | `src/capl_formatter/rules/top_level_ordering.py` |
| **Database Schema** | `src/capl_symbol_db/database.py` |
| **Dependency Analysis** | `src/capl_symbol_db/dependency.py` |
| **Symbol Extraction** | `src/capl_symbol_db/extractor.py` |
| **CAPL Parser** | `src/capl_tree_sitter/parser.py` |

## Project Overview

> **Architecture Change (January 2026):** This project was previously organized as a UV workspace with separate packages in `packages/`. It has been consolidated into a single package (`capllint`) with multiple modules in `src/`. All path references have been updated accordingly.

**CAPL Analyzer** is a static analysis and linting tool for CAPL (CANoe/CANalyzer Programming Language) files.

## Architecture: Single Package with Modules

The codebase is organized as a **single Python package** (`capllint`) with multiple internal modules in `src/`, following a **"Neutral Fact"** architecture where the database stores raw attributes and the linter performs judgment.

### Modules (in `src/`)
*   **`capl_cli/`**: CLI entry point using Typer.
    *   `main.py`: Command-line interface with `lint`, `format`, and `analyze` commands.
    *   `config.py`: Loads configuration from `.capl-lint.toml`.
*   **`capl_tree_sitter/`**: Core parsing layer.
    *   `parser.py`: High-level `CAPLParser` class.
    *   `queries.py`: `CAPLQueryHelper` for S-expression queries.
    *   `capl_patterns.py`: Recognition of CAPL-specific AST structures.
*   **`capl_symbol_db/`**: Persistence and extraction layer.
    *   `extractor.py`: Extracts **neutral facts** (e.g., `has_body`, `param_count`) without performing validation.
    *   `database.py`: Manages `aic.db` with support for recursive CTEs for transitive includes.
    *   `xref.py`: Cross-reference and call graph builder.
*   **`capl_linter/`**: Analysis and correction layer.
    *   `engine.py`: `LinterEngine` coordinates multi-pass analysis and rule execution.
    *   `builtins.py`: List of CAPL standard library functions and keywords.
    *   `autofix.py`: `AutoFixEngine` delegates to rule-specific `fix()` methods.
    *   `rules/`: Individual rule implementations categorized into `syntax`, `type`, `variable`, and `semantic` rules.
*   **`capl_formatter/`**: Opinionated code formatter.
    *   `engine.py`: `FormatterEngine` manages the 5-phase transformation pipeline (Structure -> Whitespace -> Indentation -> Comments -> Reordering).
    *   `rules/`: Specialized transformation rules (e.g., `VerticalSpacingRule`, `TopLevelOrderingRule`, `IndentationRule`).
    *   `models.py`: Configuration and transformation data structures.

## Data Architecture
*   **Internal Processing**: Uses Python `dataclasses`.
*   **Fact Neutrality**: The extractor MUST NOT validate. It only records state (e.g., `has_body=False`). The Linter rules perform all judgment based on these facts or by re-parsing the AST for syntax patterns.

## How to Add New Features

### Adding a New Lint Rule
1.  Create a new rule class in `src/capl_linter/rules/`.
2.  Inherit from `BaseRule` and implement:
    *   `rule_id`: Standardized code (e.g., `E001`).
    *   `name`: Human-readable slug.
    *   `severity`: `Severity` enum.
    *   `check(file_path, db)`: Re-parse via `CAPLParser` for syntax rules, or query `db.get_visible_symbols()` for semantic rules.
3.  Register the rule in `src/capl_linter/registry.py`.

### Adding New Auto-Fix Logic
1.  Implement the `fix(file_path, issues)` method within your rule class.
2.  Set `auto_fixable = True` in the rule class.
3.  The `AutoFixEngine` will automatically discover and execute the fix during the iterative loop.

### Adding New Symbol Extraction
1.  Update the query or logic in `src/capl_symbol_db/extractor.py`.
2.  If storing new data, update the schema in `src/capl_symbol_db/database.py`.

## Building and Running

### Setup
```bash
# Install dependencies
uv sync

# Update dependencies
uv lock --upgrade
```

### Common Commands
*   **Run Formatter:**
    ```bash
    uv run capllint format <file.can>
    ```
*   **Run Linter with Auto-Fix:**
    ```bash
    uv run capllint lint --fix <file.can>
    ```
*   **Run Analysis (Dependency/Symbol Dump):**
    ```bash
    uv run capllint analyze <file.can>
    ```
*   **Run All Tests:**
    ```bash
    uv run pytest
    ```
*   **Run Tests for a Specific Module:**
    ```bash
    uv run pytest src/capl_linter/
    uv run pytest src/capl_formatter/
    ```

## Development Conventions
*   **Grammar**: We use `tree-sitter-c` as a base. Keywords like `variables` and `on start` are handled as errors or via sibling text lookups.
*   **Parsing**: Use `CAPLQueryHelper` for complex structure matching. Avoid regex for nested code.
*   **Iterative Fixes**: Always assume a fix might shift line numbers. The iterative loop (`max_passes=10`) in `main.py` is the safety mechanism.

## User Notes:
* when the user want you to commit the changes run this command (git status; git diff --staged; git log -n 3).
