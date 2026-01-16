# Implementation Plan - Initial Linting and Auto-Fix Capabilities

This plan outlines the steps to implement and refine the core linting rules and auto-fix functionalities for the CAPL Analyzer, ensuring a robust foundation for code quality assurance.

## Phase 1: Variable Declaration Enforcement

- [~] Task: Enforce variable placement rules (outside `variables {}` block)
    - [ ] Write failing tests for variables declared at global scope outside the variables block
    - [ ] Refine implementation in `symbol_extractor.py` and `linter.py` to correctly identify and flag these cases
    - [ ] Implement/Refine auto-fix in `autofix.py` to move declarations into the block
    - [ ] Verify fix and ensure >80% coverage
- [ ] Task: Enforce variable placement rules (mid-block declarations)
    - [ ] Write failing tests for local variables declared after executable statements in functions, testcases, and event handlers
    - [ ] Refine implementation in `symbol_extractor.py` and `linter.py` to detect mid-block declarations
    - [ ] Implement/Refine auto-fix in `autofix.py` to move declarations to the start of the block
    - [ ] Verify fix and ensure >80% coverage
- [ ] Task: Conductor - User Manual Verification 'Phase 1: Variable Declaration Enforcement' (Protocol in workflow.md)

## Phase 2: Type Usage and Definition Enforcement

- [ ] Task: Enforce explicit enum and struct keywords in declarations
    - [ ] Write failing tests for declarations missing the `enum` or `struct` keyword (e.g., `STATUS s;`)
    - [ ] Refine `symbol_extractor.py` to detect known enums/structs used without keywords
    - [ ] Implement/Refine auto-fix in `autofix.py` to prepend the missing keyword
    - [ ] Verify fix and ensure >80% coverage
- [ ] Task: Enforce placement rules for enum and struct definitions
    - [ ] Write failing tests for `enum` or `struct` definitions declared at global scope outside `variables {}`
    - [ ] Refine `symbol_extractor.py` and `linter.py` to flag these definitions
    - [ ] Implement/Refine auto-fix in `autofix.py` to move the definition into the block
    - [ ] Verify fix and ensure >80% coverage
- [ ] Task: Conductor - User Manual Verification 'Phase 2: Type Usage and Definition Enforcement' (Protocol in workflow.md)

## Phase 3: Forbidden Syntax Detection

- [ ] Task: Detect and remove forbidden function declarations
    - [ ] Write failing tests for function forward declarations (e.g., `void MyFunc(int x);`)
    - [ ] Refine `symbol_extractor.py` and `linter.py` to detect and flag declarations vs definitions
    - [ ] Implement/Refine auto-fix in `autofix.py` to remove the forbidden declaration
    - [ ] Verify fix and ensure >80% coverage
- [ ] Task: Detect and handle forbidden `extern` keyword usage
    - [ ] Write failing tests for variables using the `extern` keyword
    - [ ] Refine `symbol_extractor.py` and `linter.py` to detect the `extern` keyword (ignoring comments)
    - [ ] Implement/Refine auto-fix in `autofix.py` to remove the keyword (triggering subsequent placement checks)
    - [ ] Verify fix and ensure >80% coverage
- [ ] Task: Conductor - User Manual Verification 'Phase 3: Forbidden Syntax Detection' (Protocol in workflow.md)

## Phase 4: Integration and UX Refinement
 
- [ ] Task: Refine iterative auto-fix loop and CLI output
    - [ ] Write tests for the iterative fix loop in `linter.py` to ensure it converges safely
    - [ ] Improve report formatting and transparency of auto-fix actions in `linter.py`
    - [ ] Ensure all public methods are documented and type hints are comprehensive
    - [ ] Verify project-wide consistency and perform final verification run on all examples
    - [ ] Verify final code coverage for the entire track meets >80% requirement
- [ ] Task: Implement Pydantic models for external interface
    - [ ] Add pydantic>=2.0.0 to pyproject.toml
    - [ ] Create LintIssue(BaseModel) for report output
    - [ ] Create LinterConfig(BaseModel) for user configuration
    - [ ] Add conversion: dataclass → Pydantic for final output
    - [ ] Implement --format json using Pydantic serialization
    - [ ] Generate JSON schema for CI/CD integration
    - [ ] Write validation tests for config edge cases
- [ ] Task: Bridge internal dataclasses to external Pydantic models
    - [ ] Create converter: internal_issue_to_lint_issue()
    - [ ] Ensure zero validation overhead during core analysis
    - [ ] Validate only at serialization boundary
- [ ] Task: Conductor - User Manual Verification 'Phase 4: Integration and UX Refinement' (Protocol in workflow.md)
