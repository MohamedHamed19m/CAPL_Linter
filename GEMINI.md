# CAPL Analyzer Project Context

## Quick Navigation Index

| Feature / Logic | Primary File Path |
| :--- | :--- |
| **CLI Entry Point** | `src/capl_cli/main.py` |
| **Rule Registry** | `packages/capl-linter/src/capl_linter/registry.py` |
| **Linter Engine** | `packages/capl-linter/src/capl_linter/engine.py` |
| **Syntax Rules** | `packages/capl-linter/src/capl_linter/rules/syntax_rules.py` |
| **Type Rules** | `packages/capl-linter/src/capl_linter/rules/type_rules.py` |
| **Variable Rules** | `packages/capl-linter/src/capl_linter/rules/variable_rules.py` |
| **Semantic Rules** | `packages/capl-linter/src/capl_linter/rules/semantic_rules.py` |
| **Database Schema** | `packages/capl-symbol-db/src/capl_symbol_db/database.py` |
| **Dependency Analysis** | `packages/capl-symbol-db/src/capl_symbol_db/dependency.py` |
| **Symbol Extraction** | `packages/capl-symbol-db/src/capl_symbol_db/extractor.py` |
| **CAPL Parser** | `packages/capl-tree-sitter/src/capl_tree_sitter/parser.py` |

## Project Overview

**CAPL Analyzer** is a static analysis and linting tool for CAPL (CANoe/CANalyzer Programming Language) files. It is now organized as a **UV Workspace** (monorepo) to ensure modularity, isolated testing, and clear dependency management.

## Architecture: UV Workspace

The codebase is split into independent library packages and a root CLI package, following a **"Neutral Fact"** architecture where the database stores raw attributes and the linter performs judgment.

### 1. Library Packages (in `packages/`)
*   **`capl-tree-sitter`**: Core parsing layer.
    *   `parser.py`: High-level `CAPLParser` class.
    *   `queries.py`: `CAPLQueryHelper` for S-expression queries.
    *   `capl_patterns.py`: Recognition of CAPL-specific AST structures.
*   **`capl-symbol-db`**: Persistence and extraction layer.
    *   `extractor.py`: Extracts **neutral facts** (e.g., `has_body`, `param_count`) without performing validation.
    *   `database.py`: Manages `aic.db` with support for recursive CTEs for transitive includes.
    *   `xref.py`: Cross-reference and call graph builder.
*   **`capl-linter`**: Analysis and correction layer.
    *   `engine.py`: `LinterEngine` coordinates multi-pass analysis and rule execution.
    *   `builtins.py`: List of CAPL standard library functions and keywords.
    *   `autofix.py`: `AutoFixEngine` delegates to rule-specific `fix()` methods.
    *   `rules/`: Individual rule implementations categorized into `syntax`, `type`, `variable`, and `semantic` rules.

### 2. CLI Package (Root)
*   **`src/capl_cli/`**: The `capl-cli` package.
    *   `main.py`: Entry point with support for `--project` and `--fix`.
    *   `config.py`: Loads configuration from `.capl-lint.toml`.

## Data Architecture
*   **Internal Processing**: Uses Python `dataclasses`.
*   **Fact Neutrality**: The extractor MUST NOT validate. It only records state (e.g., `has_body=False`). The Linter rules perform all judgment based on these facts or by re-parsing the AST for syntax patterns.

## How to Add New Features

### Adding a New Lint Rule
1.  Create a new rule class in `packages/capl-linter/src/capl_linter/rules/`.
2.  Inherit from `BaseRule` and implement:
    *   `rule_id`: Standardized code (e.g., `E001`).
    *   `name`: Human-readable slug.
    *   `severity`: `Severity` enum.
    *   `check(file_path, db)`: Re-parse via `CAPLParser` for syntax rules, or query `db.get_visible_symbols()` for semantic rules.
3.  Register the rule in `packages/capl-linter/src/capl_linter/registry.py`.

### Adding New Auto-Fix Logic
1.  Implement the `fix(file_path, issues)` method within your rule class.
2.  Set `auto_fixable = True` in the rule class.
3.  The `AutoFixEngine` will automatically discover and execute the fix during the iterative loop.

### Adding New Symbol Extraction
1.  Update the query or logic in `packages/capl-symbol-db/src/capl_symbol_db/extractor.py`.
2.  If storing new data, update the schema in `packages/capl-symbol-db/src/capl_symbol_db/database.py`.

## Building and Running

### Setup
```bash
# Sync entire workspace (creates venv and installs all packages)
uv sync

# Update all dependencies
uv lock --upgrade
```

### Common Commands
*   **Run Linter with Auto-Fix:**
    ```bash
    uv run capl-lint lint --fix <file.can>
    ```
*   **Run Analysis (Dependency/Symbol Dump):**
    ```bash
    uv run capl-analyze analyze <file.can>
    ```
*   **Run All Tests:**
    ```bash
    uv run pytest
    ```
*   **Run Tests for a Specific Package:**
    ```bash
    uv run --package capl-linter pytest
    ```

## Development Conventions
*   **Grammar**: We use `tree-sitter-c` as a base. Keywords like `variables` and `on start` are handled as errors or via sibling text lookups.
*   **Parsing**: Use `CAPLQueryHelper` for complex structure matching. Avoid regex for nested code.
*   **Iterative Fixes**: Always assume a fix might shift line numbers. The iterative loop (`max_passes=10`) in `main.py` is the safety mechanism.