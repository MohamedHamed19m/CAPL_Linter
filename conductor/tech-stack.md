# Tech Stack: CAPL Analyzer

## 1. Production Stack

*   **Python:** Version 3.10+ serves as the core programming language.
*   **Tree-sitter:** Utilized as the Abstract Syntax Tree (AST) parsing framework, enabling robust code analysis.
    *   `tree-sitter-c`: Specifically used as the C grammar to parse CAPL, leveraging its C-like syntax.
*   **SQLite:** Employed via the `sqlite3` Python module for persistent storage of parsed symbols and dependency information in `aic.db`.
*   **uv:** The modern Python package manager used for efficient dependency resolution and project execution.
    *   **Workspaces:** Utilized to manage a modular monorepo structure with independent packages.

## 2. Development Stack

*   **pytest:** The chosen framework for running tests.
*   **pytest-cov:** Provides code coverage reporting to ensure high test quality.
*   **ruff:** A high-performance Python tool for both linting (identifying quality issues) and formatting (replacing black).
*   **mypy:** A static type checker to ensure type correctness and improve code reliability.

## 3. Additional Context

*   **CLI Framework:** The command-line interface is built using `typer`.
*   **Data Architecture:** 
    *   **Internal Logic:** Uses Python `dataclasses` for high-performance internal representation of AST nodes, symbols, and issues.
    *   **External Interface:** Uses `pydantic` (v2.0+) for data validation and JSON serialization at the CLI/API boundary.
*   **Path Handling:** The `pathlib` module (built-in) is utilized for object-oriented filesystem paths.
