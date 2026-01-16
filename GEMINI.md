# CAPL Analyzer Project Context

## Project Overview

**CAPL Analyzer** is a static analysis and linting tool for CAPL (CANoe/CANalyzer Programming Language) files (`.can`, `.cin`). It parses CAPL code to detect common errors, enforce coding standards, and analyze dependencies. It is built with Python and leverages `tree-sitter-capl` (via `tree-sitter-c` as a base) for robust parsing.

**Key Features:**
*   **Static Analysis/Linting:** Detects errors (e.g., variables outside `variables {}` block, missing type keywords), warnings (unused variables), and style issues.
*   **Auto-Fix System:** Automatically fixes common issues like missing keywords, forbidden syntax, and variable placement.
*   **Symbol Extraction:** Extracts variables, functions, event handlers, enums, and structs.
*   **Dependency Analysis:** Tracks `#include` dependencies and detects circular references.
*   **Cross-Reference:** Finds symbol usages and builds call graphs.

**Architecture:**
*   **Core Logic:** `src/capl_analyzer/` contains the main logic.
    *   `linter.py`: The main linter engine and report generator.
    *   `autofix.py`: Logic for automatically fixing reported issues.
    *   `symbol_extractor.py`: Extracts symbols using tree-sitter.
    *   `dependency_analyzer.py`: Handles include graphs.
    *   `cross_reference.py`: Builds cross-reference databases.
*   **Database:** Uses an SQLite database (`aic.db`) to store parsed symbols and dependencies for fast access and cross-file analysis.
*   **CLI:** `cli.py` provides the command-line interface (`capl-analyze`, `capl-lint`).

## Building and Running

This project uses `uv` for dependency management and execution.

**Prerequisites:**
*   Python 3.10+
*   `uv` (Universal Python Package Manager)

**Common Commands:**

*   **Install Dependencies (Editable Mode):**
    ```bash
    uv pip install -e .
    # Or with dev dependencies
    uv pip install -e ".[dev]"
    ```

*   **Run Linter:**
    ```bash
    uv run capl-lint <file.can>
    # Run on entire project
    uv run capl-lint --project
    # Run with auto-fix
    uv run capl-lint --fix <file.can>
    ```

*   **Run Analysis (Dependency/Symbol Dump):**
    ```bash
    uv run capl-analyze analyze <file.can>
    ```

*   **Run Tests:**
    ```bash
    uv run pytest
    ```

## Development Conventions

*   **Code Style:** The project uses `ruff` and `ruff format` (implied by `pyproject.toml` config) for formatting and linting Python code. Ensure code is typed and formatted before committing.
*   **Database Schema:** The SQLite schema is defined in `symbol_extractor.py` and other modules. When adding new symbol types or features, ensure the schema `CREATE TABLE` and `INSERT` statements are updated.
*   **Auto-Fix Strategy:** Auto-fixes are implemented in `autofix.py`. Complex fixes that shift line numbers (like moving variables) are handled iteratively by the linter loop to ensuring safety.
*   **Parsing:** All parsing is done via `tree-sitter`. Do not use regex for parsing complex code structures; rely on the AST.
