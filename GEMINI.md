# CAPL Analyzer Project Context

## Project Overview

**CAPL Analyzer** is a static analysis and linting tool for CAPL (CANoe/CANalyzer Programming Language) files. It is now organized as a **UV Workspace** (monorepo) to ensure modularity, isolated testing, and clear dependency management.

## Architecture: UV Workspace

The codebase is split into independent library packages and a root CLI package:

### 1. Library Packages (in `packages/`)
*   **`capl-tree-sitter`**: Core parsing layer.
    *   `parser.py`: High-level `CAPLParser` class.
    *   `queries.py`: `CAPLQueryHelper` for executing S-expression queries.
    *   `ast_walker.py`: AST traversal utilities.
    *   `node_types.py`: Internal **dataclasses** for AST nodes and matches.
*   **`capl-symbol-db`**: Persistence and extraction layer.
    *   `extractor.py`: Extracts symbols, variables, and type definitions.
    *   `database.py`: Central SQLite (`aic.db`) schema management.
    *   `dependency.py`: Transitive `#include` analysis.
    *   `xref.py`: Cross-reference and call graph builder.
*   **`capl-linter`**: Analysis and correction layer.
    *   `engine.py`: `LinterEngine` coordinates analysis and rule execution.
    *   `registry.py`: `RuleRegistry` for managing pluggable lint rules.
    *   `autofix.py`: `AutoFixEngine` for iterative code correction.
    *   `rules/`: Individual rule implementations (e.g., `syntax_rules.py`, `variable_rules.py`).

### 2. CLI Package (Root)
*   **`src/capl_cli/`**: The `capl-cli` package.
    *   `main.py`: Entry point using `typer`.
    *   `models.py`: External **Pydantic** models for API/JSON responses.
    *   `converters.py`: Bridge logic (Dataclass → Pydantic).

## Data Architecture
*   **Internal Processing**: All logic within library packages uses Python `dataclasses` for high performance.
*   **External Interface**: The CLI converts internal dataclasses to Pydantic models at the boundary for validation and JSON serialization.

## How to Add New Features

### Adding a New Lint Rule
1.  Create a new rule class in `packages/capl-linter/src/capl_linter/rules/`.
2.  Inherit from `BaseRule` and implement `rule_id` and `check(file_path, db)`.
3.  Register the rule in `packages/capl-linter/src/capl_linter/registry.py`.

### Adding New Auto-Fix Logic
1.  Add a new fixer method to `AutoFixEngine` in `packages/capl-linter/src/capl_linter/autofix.py`.
2.  Register the rule ID in the `self._fixers` dictionary.
3.  The CLI's iterative loop handles re-analysis between fix passes automatically.

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