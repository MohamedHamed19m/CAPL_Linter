# Specification: UV Workspace Migration (Monorepo Structure)

## Overview
Restructure the CAPL Analyzer from a monolithic package into a modern UV workspace. This architectural refactoring improves modularity, enables isolated testing, and simplifies dependency management by decomposing the codebase into layered, independent packages.

## Functional Requirements
1.  **Workspace Initialization**:
    -   Create a `pyproject.toml` at the root defining the UV workspace with `[tool.uv.workspace]`.
    -   Set `package = true` in root `[tool.uv]` to make the CLI installable.
    -   Centralize development dependencies (`pytest`, `ruff`, `mypy`) in the workspace root.

2.  **Package Decomposition (Layered Approach)**:
    -   **`capl-tree-sitter`**: Tree-sitter parsing, AST traversal, and CAPL node types. Uses **dataclasses** for performance.
    -   **`capl-symbol-db`**: Symbol extraction, SQLite database operations, dependency analysis, and cross-reference tracking. Uses **dataclasses** for SymbolInfo, DependencyEdge, etc.
    -   **`capl-linter`**: Linting rules engine, auto-fix system, and rule registry. Uses **dataclasses** for InternalIssue, AutoFixAction.
    -   **`capl-cli`**: User-facing CLI (workspace root) built with `typer`. Uses **Pydantic** for external interface (LintIssue, LinterConfig, JSON output).

3.  **Filesystem Restructuring**:
    -   Move library packages into `packages/` directory: `packages/capl-tree-sitter/`, `packages/capl-symbol-db/`, `packages/capl-linter/`.
    -   Workspace root contains CLI source: `src/capl_cli/`.
    -   Update imports to use workspace package names with `{ workspace = true }` sources.
    -   Keep shared resources at root: `examples/`, `docs/`.

4.  **Testing Migration**:
    -   Colocate unit tests within each package: `packages/<package>/tests/`.
    -   Maintain root-level integration tests if needed.
    -   Enable per-package testing: `uv run --package <name> pytest`.

5.  **Entry Point Preservation**:
    -   Maintain `capl-lint` and `capl-analyze` commands via `[project.scripts]`.
    -   Ensure all commands remain operational after migration.

6.  **UV Workspace Configuration**:
    -   Define workspace dependencies using `[tool.uv.sources]` with `{ workspace = true }`.
    -   Ensure single shared lockfile (`uv.lock`) at workspace root.
    -   Configure workspace members via `[tool.uv.workspace] members = ["packages/*"]`.

## Non-Functional Requirements
-   **Data Architecture**: Dataclasses for internal processing (Phases 1-3 packages), Pydantic only for CLI external interface (Phase 4).
-   **Aggregated Coverage**: Workspace-wide coverage >80% (individual packages: capl-tree-sitter 85%+, capl-symbol-db 85%+, capl-linter 85%+, capl-cli 70%+).
-   **Dependency Isolation**: Clear layering: tree-sitter → symbol-db → linter → cli (no circular dependencies).
-   **Zero Regression**: Migration must not change linter output or auto-fix behavior for existing CAPL examples.
-   **Performance**: No measurable overhead from workspace structure vs. single package.

## Acceptance Criteria
-   [ ] `uv sync` installs entire workspace successfully.
-   [ ] `uv run capl-lint` executes correctly on all example files.
-   [ ] `uv run --workspace pytest` runs all tests successfully.
-   [ ] `uv run --package capl-linter pytest` runs package-specific tests.
-   [ ] Single `uv.lock` exists at workspace root.
-   [ ] All workspace packages use `{ workspace = true }` for inter-package dependencies.
-   [ ] `uv tree --workspace` shows correct dependency graph with no circular dependencies.
-   [ ] All packages pass `ruff format --check` and `ruff check`.
-   [ ] Coverage reports aggregate correctly across workspace (>80% total).
-   [ ] CLI commands (`capl-lint`, `capl-analyze`) work identically to pre-migration behavior.

## Out of Scope
-   Adding new linting rules or analysis features.
-   Publishing individual packages to PyPI.
-   Changing core SQLite schema or tree-sitter grammar.
-   Implementing new CLI commands or output formats.
-   Performance optimizations beyond maintaining parity.
