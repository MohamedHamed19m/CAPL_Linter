# CAPL Analyzer

> Static analysis and linting tools for CAPL (CANoe/CANalyzer Programming Language)

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 🚀 Features

- **Auto-Fix System**: Automatically resolves common linting issues.
- **Dependency Analysis**: Track `#include` relationships and build dependency graphs
- **Symbol Extraction**: Extract functions, variables, event handlers, and CAPL-specific constructs
- **Cross-Reference System**: Find all references to any symbol across your codebase
- **Static Analysis / Linter**: Detect common issues and enforce coding standards

## 📋 What Can It Detect?

### Errors
- ❌ Variables declared outside `variables {}` block (CAPL syntax error)
- ❌ Local variables declared after executable statements (mid-block)
- ❌ Undefined symbol references (with support for CAPL built-ins, test functions, and enum members)
- ❌ Duplicate event handlers (excluding system events like `on start`)
- ❌ Circular include dependencies
- ❌ Missing `enum` or `struct` keywords in declarations
- ❌ Forbidden syntax: function declarations (forward declarations)
- ❌ Forbidden syntax: `extern` keyword usage

### Warnings
- ⚠️ Unused variables, functions, messages, and timers
- ⚠️ Timers set without handlers

### Style Issues
- 💅 Naming conventions (global variables should start with `g`, messages with `msg`, timers with `t`)
- 💅 Code organization and structure

## 🔧 Installation

### Using UV (Recommended)

This project is managed as a [uv workspace](https://docs.astral.sh/uv/concepts/workspaces/).

```bash
# Clone the repository
git clone https://github.com/yourusername/capl-analyzer.git
cd capl-analyzer

# Sync the workspace (creates venv and installs all packages)
uv sync

# Run the linter
uv run capl-lint MyNode.can
```

## 🏗️ Project Structure

The project is organized into a modular monorepo structure:

- **`capl-cli`** (Root): User-facing CLI built with `typer`.
- **`packages/capl-tree-sitter`**: Core CAPL parsing using tree-sitter.
- **`packages/capl-symbol-db`**: Symbol extraction and persistent storage (SQLite).
- **`packages/capl-linter`**: Analysis engine and auto-fix logic.

```
capl-analyzer/
├── packages/
│   ├── capl-tree-sitter/
│   ├── capl-symbol-db/
│   └── capl-linter/
├── src/
│   └── capl_cli/          # CLI source
├── examples/
├── docs/
├── pyproject.toml         # Workspace configuration
└── README.md
```

## 🧪 Running Tests

```bash
# Run all tests across the entire workspace
uv run --workspace pytest

# Run tests for a specific package
uv run --package capl-linter pytest

# Run with coverage aggregated across the workspace
uv run --workspace pytest --cov-report=html
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Built with [tree-sitter](https://tree-sitter.github.io/tree-sitter/) for robust parsing
- Inspired by modern linting tools and static analyzers

## 📚 Documentation

For detailed documentation, see the [docs](./docs) directory or visit the [wiki](https://github.com/yourusername/capl-analyzer/wiki).

## 🐛 Known Issues & Roadmap

- [ ] Add support for CAPL 2.0+ features
- [ ] Implement more sophisticated control flow analysis
- [ ] Add auto-fix capabilities for style issues
- [ ] Build VS Code extension
- [ ] Add configuration file support (.capl-lint.toml)

## 💬 Support

If you have any questions or run into issues, please [open an issue](https://github.com/yourusername/capl-analyzer/issues).
