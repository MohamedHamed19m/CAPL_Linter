# CAPL Analyzer Workspace

This project uses a [uv workspace](https://docs.astral.sh/uv/concepts/workspaces/) to manage multiple independent packages within a single repository.

## Structure

- **`capl-cli`** (Root): The user-facing CLI and entry point.
- **`packages/capl-tree-sitter`**: Tree-sitter parsing and AST utilities.
- **`packages/capl-symbol-db`**: Symbol extraction and SQLite database.
- **`packages/capl-linter`**: Linting rules and auto-fix engine.

## Common Commands

### Workspace Management

```bash
# Sync entire workspace and install all dependencies
uv sync

# Update all dependencies in the workspace
uv lock --upgrade

# View workspace dependency tree
uv tree
```

### Running Tests

```bash
# Run tests for all packages in the workspace
uv run --workspace pytest

# Run tests for a specific package
uv run --package capl-linter pytest

# Run tests with coverage for a specific package
uv run --package capl-linter pytest --cov=src/capl_linter
```

### Development

```bash
# Run the CLI from source
uv run capl-lint examples/AutoFixTest.can

# Format all code in the workspace
uv run ruff format .

# Lint all code in the workspace
uv run ruff check .
```

## Migration Guide

If you are migrating from the monolithic structure:

1. Use `uv sync` to set up the new workspace environment.
2. Update any external scripts that depended on the internal path of `src/capl_analyzer/`. The CLI entry point `capl-lint` remains the same.
3. Inter-package dependencies are managed via `{ workspace = true }` in `pyproject.toml`.
