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

```bash
# Install UV if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone the repository
git clone https://github.com/yourusername/capl-analyzer.git
cd capl-analyzer

# Create virtual environment and install
uv venv
uv pip install -e .
```

### Using pip

```bash
pip install -e .
```

## 📖 Quick Start

### 1. Analyze Dependencies

```python
from capl_analyzer import CAPLDependencyAnalyzer

analyzer = CAPLDependencyAnalyzer(
    db_path="aic.db",
    search_paths=["./includes", "./common"]
)

# Analyze a single file
analyzer.analyze_file("MyNode.can")

# Get dependencies
deps = analyzer.get_dependencies("MyNode.can", recursive=True)
print(f"Dependencies: {deps}")

# Generate dependency graph
analyzer.generate_dependency_graph("deps.dot")
```

### 2. Extract Symbols

```python
from capl_analyzer import CAPLSymbolExtractor

extractor = CAPLSymbolExtractor()

# Extract and store symbols
extractor.store_symbols("MyNode.can")

# List symbols in file
symbols = extractor.list_symbols_in_file("MyNode.can")
for name, sym_type, line, sig in symbols:
    print(f"{line:4d} | {sym_type:15s} | {name}")
```

### 3. Find All References

```python
from capl_analyzer import CAPLCrossReferenceBuilder

xref = CAPLCrossReferenceBuilder()

# Build cross-references
xref.analyze_file_references("MyNode.can")

# Find all references to a symbol
refs = xref.find_all_references("msgEngine")
for ref in refs:
    print(f"{ref.file_path}:{ref.line_number} [{ref.reference_type}]")

# Get call graph
graph = xref.get_call_graph("UpdateEngine")
print("Called by:", graph['callers'])
print("Calls:", graph['callees'])
```

### 4. Run Linter

```python
from capl_analyzer import CAPLLinter

linter = CAPLLinter()

# Analyze a file
issues = linter.analyze_file("MyNode.can")

# Generate report
print(linter.generate_report(issues))
```

Or use the command-line interface:

```bash
# Lint a single file
capl-lint MyNode.can

# Lint entire project
capl-lint --project

# Filter by severity
capl-lint --severity warning MyNode.can

# Show what would be fixed (dry run)
capl-lint --fix-dry-run MyNode.can

# Automatically fix issues
capl-lint --fix MyNode.can

# Fix only specific rule IDs
capl-lint --fix --fix-only variable-outside-block MyNode.can
```

## 🏗️ Project Structure

```
capl-analyzer/
├── src/
│   └── capl_analyzer/
│       ├── __init__.py
│       ├── dependency_analyzer.py
│       ├── symbol_extractor.py
│       ├── cross_reference.py
│       └── linter.py
├── tests/
│   ├── test_dependency_analyzer.py
│   ├── test_symbol_extractor.py
│   ├── test_cross_reference.py
│   └── test_linter.py
├── examples/
│   ├── MyNode.can
│   └── ProblematicCode.can
├── docs/
├── pyproject.toml
└── README.md
```

## 🧪 Running Tests

```bash
# Install dev dependencies
uv pip install -e ".[dev]"

# Run all tests
pytest

# Run with coverage
pytest --cov=capl_analyzer --cov-report=html
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
