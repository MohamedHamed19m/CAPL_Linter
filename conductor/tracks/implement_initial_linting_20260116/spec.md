# Track Specification: Implement Initial Linting and Auto-Fix Capabilities

## 1. Overview

This track focuses on establishing a robust foundation for CAPL code quality assurance within the CAPL Analyzer tool. It involves implementing a comprehensive set of linting rules and corresponding auto-fix functionalities for fundamental CAPL syntax, style, and common best practices. The goal is to immediately address critical pain points identified by Embedded Software Engineers, Test Automation Engineers, and Code Reviewers, enabling them to write more reliable, maintainable, and compliant CAPL code.

## 2. Goals

*   **For Embedded Software Engineers:** Provide immediate feedback on common coding errors and suggest/apply fixes to ensure automotive system reliability.
*   **For Test Automation Engineers:** Automate the correction of repetitive CAPL code issues, reducing manual effort and improving the efficiency of test suite maintenance.
*   **For Code Reviewers:** Standardize CAPL code quality across projects and teams by enforcing predefined rules, thus streamlining the code review process.

## 3. Scope

This track will cover:

### 3.1. Linting Rules & Auto-Fixes
*   **Variable Declarations:**
    *   **Rule:** Variables declared outside `variables {}` block.
    *   **Auto-Fix:** Move variable declaration into the `variables {}` block.
    *   **Rule:** Local variables declared after executable statements (mid-block).
    *   **Auto-Fix:** Move local variable declaration to the beginning of its scope (function/event handler/testcase).
*   **Type Usage:**
    *   **Rule:** Missing `enum` or `struct` keywords in declarations (e.g., `STATUS myVar;` instead of `enum STATUS myVar;`).
    *   **Auto-Fix:** Add the appropriate `enum` or `struct` keyword.
*   **Forbidden Syntax:**
    *   **Rule:** Function declarations (forward declarations).
    *   **Auto-Fix:** Remove the function declaration line.
    *   **Rule:** `extern` keyword usage.
    *   **Auto-Fix:** Remove the `extern` keyword (this may trigger the `variable-outside-block` rule, which will be handled in a subsequent pass).
*   **Global Type Definitions:**
    *   **Rule:** `enum` or `struct` definitions declared outside the `variables {}` block.
    *   **Auto-Fix:** Move the `enum` or `struct` definition into the `variables {}` block.

### 3.2. Error/Warning Reporting
*   Generate clear and actionable error/warning messages following the **Balanced Technical** prose style defined in `product-guidelines.md`:
    *   **Format:** `❌ ERROR (Line X): [rule-id]`
    *   **Content:** Precise description + actionable suggestion
    *   **Indicators:** Auto-fixable status, CAPL specification references
*   **Example:**
❌ ERROR (Line 25): variable-outside-block
   Variable 'badVar' declared outside 'variables {}' block
   💡 Move 'badVar' declaration into the variables {} block
   🔧 Auto-fixable


### 3.3. Integration
*   Ensure seamless integration with the existing `capl-lint` CLI.
*   Leverage the `symbol_extractor` and internal SQLite database (`aic.db`) for efficient analysis.
*   **Output Formats (Phase 4):** 
    *   Human-readable text (default)
    *   JSON format (`--format json`)
*   **Progressive Disclosure:**
    *   Brief summary by default
    *   Detailed output with `--verbose` flag
    *   CAPL specification references in detailed mode
## 4. Non-Goals

*   Implementing all possible CAPL linting rules.
*   Complex control flow analysis.
*   Inter-file analysis beyond basic include dependencies for linting.

## 5. Technical Details

*   **Python Implementation:** All new rules and auto-fixes will be implemented in Python within the `src/capl_analyzer/` directory.
*   **Tree-sitter:** AST parsing for precise rule detection.
*   **SQLite:** Database for storing extracted symbols and type definitions.
*   **Iterative Auto-Fix:** The auto-fix system will operate in an iterative manner, applying one type of fix at a time and re-analyzing the file, ensuring safety and correctness.
*   **Data Architecture:**
    *   **Internal Engine (Phases 1-3):** Uses Python `dataclasses` for high-performance symbol representation and AST traversal. No runtime validation overhead.
    *   **External Interface (Phase 4):** Uses `pydantic` models for validated CLI output, JSON serialization, and configuration handling.
    *   **Bridge Layer:** Converts internal dataclass representations to validated Pydantic models only at serialization boundaries.

## 6. Quality Standards

*   **Test Coverage:** Minimum 80% code coverage across all phases
    *   Phase 1-3 (core engine): 80%+ recommended
    *   Phase 4 (CLI/integration): 70%+ acceptable
*   **Validation:**
    *   Real-world CAPL file testing before phase sign-off    


## 7. Dependencies

### Phase 1-3 (Core Engine)
*   `tree-sitter>=0.25.2` - AST parsing
*   `tree-sitter-c>=0.24.1` - C grammar for CAPL
*   No additional dependencies (uses built-in `dataclasses`)

### Phase 4 (External Interface)
*   `pydantic>=2.0.0` - Validation and serialization

### Development
*   `pytest>=7.0.0` - Testing framework
*   `pytest-cov>=4.0.0` - Coverage reporting
*   `ruff>=0.1.0` - Linting and formatting
*   `mypy>=1.0.0` - Type checking    