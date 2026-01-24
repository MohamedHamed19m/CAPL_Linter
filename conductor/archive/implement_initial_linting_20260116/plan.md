# Implementation Plan - Initial Linting and Auto-Fix Capabilities

This plan outlines the steps to implement and refine the core linting rules and auto-fix functionalities for the CAPL Analyzer, ensuring a robust foundation for code quality assurance.

## Phase 1: Variable Declaration Enforcement

- [x] Task: Enforce variable placement rules (outside `variables {}` block)
    - [x] Write failing tests for variables declared at global scope outside the variables block
    - [x] Refine implementation in `symbol_extractor.py` and `linter.py` to correctly identify and flag these cases
    - [x] Implement/Refine auto-fix in `autofix.py` to move declarations into the block
    - [x] Verify fix and ensure >80% coverage
- [x] Task: Enforce variable placement rules (mid-block declarations)
    - [x] Write failing tests for local variables declared after executable statements in functions, testcases, and event handlers
    - [x] Refine implementation in `symbol_extractor.py` and `linter.py` to detect mid-block declarations
    - [x] Implement/Refine auto-fix in `autofix.py` to move declarations to the start of the block
    - [x] Verify fix and ensure >80% coverage
- [x] Task: Conductor - User Manual Verification 'Phase 1: Variable Declaration Enforcement' (Protocol in workflow.md)

## Phase 2: Type Usage and Definition Enforcement

- [x] Task: Enforce explicit enum and struct keywords in declarations
    - [x] Write failing tests for declarations missing the `enum` or `struct` keyword (e.g., `STATUS s;`)
    - [x] Refine `symbol_extractor.py` to detect known enums/structs used without keywords
    - [x] Implement/Refine auto-fix in `autofix.py` to prepend the missing keyword
    - [x] Verify fix and ensure >80% coverage
- [x] Task: Enforce placement rules for enum and struct definitions
    - [x] Write failing tests for `enum` or `struct` definitions declared at global scope outside `variables {}`
    - [x] Refine `symbol_extractor.py` and `linter.py` to flag these definitions
    - [x] Implement/Refine auto-fix in `autofix.py` to move the definition into the block
    - [x] Verify fix and ensure >80% coverage
- [x] Task: Conductor - User Manual Verification 'Phase 2: Type Usage and Definition Enforcement' (Protocol in workflow.md)

## Phase 3: Forbidden Syntax Detection

- [x] Task: Detect and remove forbidden function declarations
    - [x] Write failing tests for function forward declarations (e.g., `void MyFunc(int x);`)
    - [x] Refine `symbol_extractor.py` and `linter.py` to detect and flag declarations vs definitions
    - [x] Implement/Refine auto-fix in `autofix.py` to remove the forbidden declaration
    - [x] Verify fix and ensure >80% coverage
- [x] Task: Detect and handle forbidden `extern` keyword usage
    - [x] Write failing tests for variables using the `extern` keyword
    - [x] Refine `symbol_extractor.py` and `linter.py` to detect the `extern` keyword (ignoring comments)
    - [x] Implement/Refine auto-fix in `autofix.py` to remove the keyword (triggering subsequent placement checks)
    - [x] Verify fix and ensure >80% coverage
- [x] Task: Conductor - User Manual Verification 'Phase 3: Forbidden Syntax Detection' (Protocol in workflow.md)

## Phase 4: Integration and UX Refinement
 
- [x] Task: Refine iterative auto-fix loop and CLI output
    - [x] Write tests for the iterative fix loop in `linter.py` to ensure it converges safely
    - [x] Improve report formatting and transparency of auto-fix actions in `linter.py`
    - [x] Ensure all public methods are documented and type hints are comprehensive
    - [x] Verify project-wide consistency and perform final verification run on all examples
    - [x] Verify final code coverage for the entire track meets >80% requirement
- [x] Task: Implement Pydantic models for external interface
    - [x] Add pydantic>=2.0.0 to pyproject.toml
    - [x] Create LintIssue(BaseModel) for report output
    - [x] Create LinterConfig(BaseModel) for user configuration
    - [x] Add conversion: dataclass → Pydantic for final output
    - [x] Implement --format json using Pydantic serialization
    - [x] Generate JSON schema for CI/CD integration
    - [x] Write validation tests for config edge cases
- [x] Task: Bridge internal dataclasses to external Pydantic models
    - [x] Create converter: internal_issue_to_lint_issue()
    - [x] Ensure zero validation overhead during core analysis
    - [x] Validate only at serialization boundary
- [x] Task: Conductor - User Manual Verification 'Phase 4: Integration and UX Refinement' (Protocol in workflow.md)
