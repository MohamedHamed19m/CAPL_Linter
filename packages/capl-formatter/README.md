# CAPL Formatter

AST-based code formatter for CAPL (CANoe/CANalyzer Programming Language).

## Overview

The `capl-formatter` package provides a robust, stable, and idempotent engine for formatting CAPL source code. Unlike regex-based formatters, it uses `tree-sitter-c` to understand the code's structure, ensuring that transformations are safe and accurate.

## Key Features

- **AST-Aware Transformation**: Applies changes based on code structure rather than text patterns.
- **Two-Pass Engine**: A structural pass for complex changes (splitting, spacing) followed by a final precision indentation pass.
- **Standardized Style**:
  - K&R Brace Style (opening brace on the same line).
  - Consistent spacing around binary operators (`+`, `-`, `*`, etc.).
  - Proper spacing for punctuation (commas, semicolons).
  - Intelligent line splitting for consecutive statements.
  - Quote normalization (consistent double quotes).
  - Include sorting and grouping.
- **Aggressive Cleanup**: Eliminates redundant blank lines and trailing whitespace.

## Usage

```python
from capl_formatter.engine import FormatterEngine
from capl_formatter.models import FormatterConfig
from capl_formatter.rules import SpacingRule, IndentationRule

config = FormatterConfig()
engine = FormatterEngine(config)

# Add rules in order
engine.add_rule(SpacingRule(config))
engine.add_rule(IndentationRule(config))

result = engine.format_string("void f(){int x=1;}")
print(result.source)
```

## Architecture

The formatter follows a **Neutral Fact** transformation model:
1.  **Analyze**: Each rule receives a `FormattingContext` (source + AST) and returns a list of `Transformation` objects (start/end offsets + new content).
2.  **Apply**: The `FormatterEngine` sorts and applies transformations bottom-up or iteratively to achieve stability.
3.  **Converge**: Multiple passes ensure that complex structural changes (like splitting lines) are correctly indented in subsequent passes.