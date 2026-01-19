# Specification: CAPL Formatter (`capl-formatter`)

## Overview
Implement a standalone CAPL formatting package and integrate it into the `drift` CLI. The formatter will follow an opinionated "Black-style" philosophy, providing consistent, high-quality code formatting with minimal configuration, specifically tailored for automotive CAPL development.

## Functional Requirements

### 1. Core Formatting Engine
- Implement a `FormatterEngine` in `packages/capl-formatter/` to orchestrate transformations.
- Support a plugin-based architecture for formatting rules via a `BaseFormattingRule` interface.
- Implement a `BaseRewriteStrategy` to handle transformations (supporting both token-based and AST-based approaches).

### 2. Style Rules (Opinionated Defaults)
- **Indentation**: 2 spaces.
- **Line Length**: Max 100 characters.
- **Brace Style**: K&R style for functions and event handlers (opening brace on the same line).
- **Quotes**: Enforce double quotes for strings.
- **Spacing**:
  - Space after commas and around binary operators.
  - Space before opening braces.
- **Blank Lines**:
  - 1 blank line before functions/event handlers.
  - 2 blank lines before major blocks (`variables`, `includes`).

### 3. Comment Management
- **Reflow**: Wrap line (`//`) and block (`/* */`) comments to fit the line length limit.
- **Block Alignment**: Normalize JSDoc/Doxygen-style documentation blocks (aligned `*` on continuation lines).
- **ASCII Art Preservation**: Keep large decorative headers exactly as-is (e.g., blocks starting with `/****`, `/*====`).

### 4. Code Organization & Cleanup
- **Include Sorting**:
  - Group `.cin` (libraries) first, then `.can` (nodes).
  - Alphabetical sorting within groups; remove duplicates.
  - One blank line between groups.
- **Pragma Handling**:
  - `#pragma library` directives must be preserved exactly as-is.
  - Positioning: Pragmas should appear after includes and before the `variables {}` block.
- **Variable Ordering**:
  - Order within `variables {}`: `message` → `msTimer` → `sysvar` → primitives (int, char, etc.).
  - Alphabetical sorting by name within each type group.
  - **Comment Preservation**: Preserve inline comments associated with variables during reordering.
  - Blank line between groups.
- **Whitespace Cleanup**:
  - Remove trailing whitespace on all lines.
  - Ensure single newline at end of file (POSIX compliance).
  - Collapse multiple consecutive blank lines to a maximum of 2.

### 5. Line Wrapping (Hybrid/Heuristic)
- **Definitions**: Force "Chop Down" style (one parameter per line) for signatures exceeding the limit.
- **Calls**: "Fit as many as possible" unless deeply nested or containing extremely long arguments.
- **Initializers**: Smart wrapping for array and struct initializers (field/element alignment).

### 6. CLI & Configuration
- **Command**: `drift format [paths] [--check] [--json]`.
- **Configuration**: Support `.capl-format.toml` for overrides (defaulting to opinionated).
- **Output Formats**: Human-readable console output (default) or `--json` for machine-readable output.
- **Error Handling**: Skip and continue on syntax errors. Log errors for problematic files and proceed with others.
- **Exit Codes**:
  - `0`: All files formatted successfully.
  - `1`: Syntax errors encountered, or formatting violations detected in `--check` mode.

## Non-Functional Requirements
- **Architecture**: Adhere to SOLID principles (Single Responsibility, Open/Closed, Dependency Inversion).
- **Quality**: >80% test coverage for all formatting logic.
- **Idempotency**: Repeated formatting must produce stable output (stable formatting).

## Acceptance Criteria
- `drift format` correctly applies all specified style and organization rules.
- `drift format --check` correctly reports violations without modifying files and exits with code 1.
- Running `drift format` multiple times on the same file produces identical output.
- Formatter gracefully handles parse errors; invalid CAPL syntax does not crash the tool and is reported clearly.
- Comments, pragmas, and decorative headers are preserved correctly during processing.
- The monorepo structure is maintained with a clean `packages/capl-formatter/`.
