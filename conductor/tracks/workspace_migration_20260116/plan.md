# Implementation Plan: UV Workspace Migration (Monorepo Structure)

## Phase 1: Workspace Setup & Structure

- [ ] Task: Create workspace root structure
    - [ ] Create workspace root `pyproject.toml` with `[tool.uv.workspace]` and `package = true`
    - [ ] Configure `[project.scripts]` for `capl-lint` and `capl-analyze`
    - [ ] Define workspace sources: `capl-tree-sitter`, `capl-symbol-db`, `capl-linter`
    - [ ] Create `packages/` directory
    - [ ] Verify workspace detection using `uv tree --workspace`
- [ ] Task: Initialize package directories
    - [ ] Run `uv init packages/capl-tree-sitter --lib`
    - [ ] Run `uv init packages/capl-symbol-db --lib`
    - [ ] Run `uv init packages/capl-linter --lib`
    - [ ] Create `src/capl_cli/` directory in workspace root
    - [ ] Verify all members appear in workspace: `uv tree --workspace`
- [ ] Task: Document workspace commands
    - [ ] Create `WORKSPACE.md` with usage examples (sync, lock, package-specific tests)
    - [ ] Update root `README.md` with workspace structure
    - [ ] Add migration guide for existing users
- [ ] Task: Conductor - User Manual Verification 'Phase 1: Workspace Setup' (Protocol in workflow.md)

## Phase 2: Extract Tree-Sitter Package

- [ ] Task: Configure `capl-tree-sitter` package
    - [ ] Update `packages/capl-tree-sitter/pyproject.toml` with `tree-sitter` dependencies
    - [ ] Establish package internal structure (`parser.py`, `ast_walker.py`, `node_types.py`, `queries.py`)
- [ ] Task: Extract parsing logic (TDD)
    - [ ] Define `ASTNode`, `ParseResult`, and `NodeMatch` dataclasses in `node_types.py`
    - [ ] Create `CAPLParser` class in `parser.py` (migrated from `symbol_extractor.py`)
    - [ ] Create `ASTWalker` for tree traversal and `queries.py` for tree-sitter helpers
    - [ ] Write failing parsing tests in `packages/capl-tree-sitter/tests/`
    - [ ] Implement/Refactor logic to pass tests and verify >85% coverage
- [ ] Task: Test workspace dependency
    - [ ] Verify root-level import: `from capl_tree_sitter import CAPLParser`
    - [ ] Test package isolation: `uv run --package capl-tree-sitter pytest`
- [ ] Task: Conductor - User Manual Verification 'Phase 2: Tree-Sitter Package' (Protocol in workflow.md)

## Phase 3: Extract Symbol Database Package

- [ ] Task: Configure `capl-symbol-db` package
    - [ ] Update `packages/capl-symbol-db/pyproject.toml` with dependency on `capl-tree-sitter`
    - [ ] Establish package internal structure (`extractor.py`, `database.py`, `models.py`, `dependency.py`, `xref.py`)
- [ ] Task: Extract symbol models and extraction (TDD)
    - [ ] Define `SymbolInfo`, `VariableDeclaration`, and `FunctionDefinition` dataclasses in `models.py`
    - [ ] Move symbol extraction logic to `extractor.py` and refactor to use `CAPLParser`
    - [ ] Write failing extraction tests in `packages/capl-symbol-db/tests/`
    - [ ] Implement/Refactor to pass tests and verify >85% coverage
- [ ] Task: Extract database operations (TDD)
    - [ ] Move SQLite schema and `SymbolDatabase` class to `database.py`
    - [ ] Move dependency analysis from `dependency_analyzer.py` to `dependency.py`
    - [ ] Move cross-reference tracking to `xref.py`
    - [ ] Write database and xref tests and verify >80% coverage
- [ ] Task: Conductor - User Manual Verification 'Phase 3: Symbol Database Package' (Protocol in workflow.md)

## Phase 4: Extract Linter Package

- [ ] Task: Configure `capl-linter` package
    - [ ] Update `packages/capl-linter/pyproject.toml` with tree-sitter and symbol-db dependencies
    - [ ] Establish package internal structure (`engine.py`, `autofix.py`, `models.py`, `registry.py`, `rules/`)
- [ ] Task: Define linter data structures
    - [ ] Define `InternalIssue` and `AutoFixAction` dataclasses in `models.py`
- [ ] Task: Extract linting rules and engine (TDD)
    - [ ] Move rules to split modules in `rules/` (variable, type, syntax, style)
    - [ ] Create `RuleRegistry` for dynamic loading and `LinterEngine` in `engine.py`
    - [ ] Move `autofix.py` and create `AutoFixEngine` class
    - [ ] Write failing tests for rules and auto-fix convergence
    - [ ] Implement/Refactor to pass tests and verify >85% coverage
- [ ] Task: Conductor - User Manual Verification 'Phase 4: Linter Package' (Protocol in workflow.md)

## Phase 5: Implement CLI Package (Workspace Root)

- [ ] Task: Configure workspace root as CLI package
    - [ ] Update root `pyproject.toml` to include `pydantic>=2.0.0` and `typer`
    - [ ] Create `src/capl_cli/` structure (main, commands, formatters, models, converters)
- [ ] Task: Implement Pydantic models and bridge (TDD)
    - [ ] Create external `LintIssue` and `LinterConfig` Pydantic models in `models.py`
    - [ ] Implement Dataclass → Pydantic converters in `converters.py`
    - [ ] Write validation tests and verify zero overhead during analysis
- [ ] Task: Implement formatters and commands (TDD)
    - [ ] Implement text, JSON, and GitHub formatters per guidelines
    - [ ] Move and integrate CLI commands (`lint`, `analyze`, `fix`)
    - [ ] Add CLI flags: `--format`, `--verbose`, etc.
    - [ ] Write integration tests in `tests/`
- [ ] Task: Conductor - User Manual Verification 'Phase 5: CLI Package' (Protocol in workflow.md)

## Phase 6: Migration & Workspace Validation

- [ ] Task: Migrate existing code and cleanup
    - [ ] Update all project-wide imports to use new workspace package names
    - [ ] Fix any circular dependencies detected by `uv tree --workspace`
    - [ ] Verify all imports resolve: `uv run --workspace python -c "import capl_cli"`
    - [ ] Delete old `src/capl_analyzer/` directory
- [ ] Task: Update CI/CD and Quality Audit
    - [ ] Update GitHub Actions to use `uv run --workspace pytest` and lockfile validation
    - [ ] Run workspace formatting (`ruff format .`) and linting (`ruff check --fix .`)
    - [ ] Verify coverage >80% aggregated across entire workspace
    - [ ] Test fresh install: `uv sync --reinstall`
- [ ] Task: Conductor - User Manual Verification 'Phase 6: Migration Complete' (Protocol in workflow.md)
