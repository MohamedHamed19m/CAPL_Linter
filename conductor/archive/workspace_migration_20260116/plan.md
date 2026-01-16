# Implementation Plan: UV Workspace Migration (Monorepo Structure)

## Phase 1: Workspace Setup & Structure

- [x] Task: Create workspace root structure
    - [x] Create workspace root `pyproject.toml` with `[tool.uv.workspace]` and `package = true`
    - [x] Configure `[project.scripts]` for `capl-lint` and `capl-analyze`
    - [x] Define workspace sources: `capl-tree-sitter`, `capl-symbol-db`, `capl-linter`
    - [x] Create `packages/` directory
    - [x] Verify workspace detection using `uv tree --workspace`
- [x] Task: Initialize package directories
    - [x] Run `uv init packages/capl-tree-sitter --lib`
    - [x] Run `uv init packages/capl-symbol-db --lib`
    - [x] Run `uv init packages/capl-linter --lib`
    - [x] Create `src/capl_cli/` directory in workspace root
    - [x] Verify all members appear in workspace: `uv tree --workspace`
- [x] Task: Document workspace commands
    - [x] Create `WORKSPACE.md` with usage examples (sync, lock, package-specific tests)
    - [x] Update root `README.md` with workspace structure
    - [x] Add migration guide for existing users
- [x] Task: Conductor - User Manual Verification 'Phase 1: Workspace Setup' (Protocol in workflow.md)

## Phase 2: Extract Tree-Sitter Package

- [x] Task: Configure `capl-tree-sitter` package
    - [x] Update `packages/capl-tree-sitter/pyproject.toml` with `tree-sitter` dependencies
    - [x] Establish package internal structure (`parser.py`, `ast_walker.py`, `node_types.py`, `queries.py`)
- [x] Task: Extract parsing logic (TDD)
    - [x] Define `ASTNode`, `ParseResult`, and `NodeMatch` dataclasses in `node_types.py`
    - [x] Create `CAPLParser` class in `parser.py` (migrated from `symbol_extractor.py`)
    - [x] Create `ASTWalker` for tree traversal and `queries.py` for tree-sitter helpers
    - [x] Write failing parsing tests in `packages/capl-tree-sitter/tests/`
    - [x] Implement/Refactor logic to pass tests and verify >85% coverage
- [x] Task: Test workspace dependency
    - [x] Verify root-level import: `from capl_tree_sitter import CAPLParser`
    - [x] Test package isolation: `uv run --package capl-tree-sitter pytest`
- [x] Task: Conductor - User Manual Verification 'Phase 2: Tree-Sitter Package' (Protocol in workflow.md)

## Phase 3: Extract Symbol Database Package

- [x] Task: Configure `capl-symbol-db` package
    - [x] Update `packages/capl-symbol-db/pyproject.toml` with dependency on `capl-tree-sitter`
    - [x] Establish package internal structure (`extractor.py`, `database.py`, `models.py`, `dependency.py`, `xref.py`)
- [x] Task: Extract symbol models and extraction (TDD)
    - [x] Define `SymbolInfo`, `VariableDeclaration`, and `FunctionDefinition` dataclasses in `models.py`
    - [x] Move symbol extraction logic to `extractor.py` and refactor to use `CAPLParser`
    - [x] Write failing extraction tests in `packages/capl-symbol-db/tests/`
    - [x] Implement/Refactor to pass tests and verify >85% coverage
- [x] Task: Extract database operations (TDD)
    - [x] Move SQLite schema and `SymbolDatabase` class to `database.py`
    - [x] Move dependency analysis from `dependency_analyzer.py` to `dependency.py`
    - [x] Move cross-reference tracking to `xref.py`
    - [x] Write database and xref tests and verify >80% coverage
- [x] Task: Conductor - User Manual Verification 'Phase 3: Symbol Database Package' (Protocol in workflow.md)

## Phase 4: Extract Linter Package

- [x] Task: Configure `capl-linter` package
    - [x] Update `packages/capl-linter/pyproject.toml` with tree-sitter and symbol-db dependencies
    - [x] Establish package internal structure (`engine.py`, `autofix.py`, `models.py`, `registry.py`, `rules/`)
- [x] Task: Define linter data structures
    - [x] Define `InternalIssue` and `AutoFixAction` dataclasses in `models.py`
- [x] Task: Extract linting rules and engine (TDD)
    - [x] Move rules to split modules in `rules/` (variable, type, syntax, style)
    - [x] Create `RuleRegistry` for dynamic loading and `LinterEngine` in `engine.py`
    - [x] Move `autofix.py` and create `AutoFixEngine` class
    - [x] Write failing tests for rules and auto-fix convergence
    - [x] Implement/Refactor to pass tests and verify >85% coverage
- [x] Task: Conductor - User Manual Verification 'Phase 4: Linter Package' (Protocol in workflow.md)

## Phase 5: Implement CLI Package (Workspace Root)

- [x] Task: Configure workspace root as CLI package
    - [x] Update root `pyproject.toml` to include `pydantic>=2.0.0` and `typer`
    - [x] Create `src/capl_cli/` structure (main, commands, formatters, models, converters)
- [x] Task: Implement Pydantic models and bridge (TDD)
    - [x] Create external `LintIssue` and `LinterConfig` Pydantic models in `models.py`
    - [x] Implement Dataclass → Pydantic converters in `converters.py`
    - [x] Write validation tests and verify zero overhead during analysis
- [x] Task: Implement formatters and commands (TDD)
    - [x] Implement text, JSON, and GitHub formatters per guidelines
    - [x] Move and integrate CLI commands (`lint`, `analyze`, `fix`)
    - [x] Add CLI flags: `--format`, `--verbose`, etc.
    - [x] Write integration tests in `tests/`
- [x] Task: Conductor - User Manual Verification 'Phase 5: CLI Package' (Protocol in workflow.md)

## Phase 6: Migration & Workspace Validation

- [x] Task: Migrate existing code and cleanup
    - [x] Update all project-wide imports to use new workspace package names
    - [x] Fix any circular dependencies detected by `uv tree --workspace`
    - [x] Verify all imports resolve: `uv run --workspace python -c "import capl_cli"`
    - [x] Delete old `src/capl_analyzer/` directory
- [x] Task: Update CI/CD and Quality Audit
    - [x] Update GitHub Actions to use `uv run --workspace pytest` and lockfile validation
    - [x] Run workspace formatting (`ruff format .`) and linting (`ruff check --fix .`)
    - [x] Verify coverage >80% aggregated across entire workspace
    - [x] Test fresh install: `uv sync --reinstall`
- [x] Task: Conductor - User Manual Verification 'Phase 6: Migration Complete' (Protocol in workflow.md)