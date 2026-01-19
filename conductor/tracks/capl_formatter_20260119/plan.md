# Implementation Plan: CAPL Formatter (`capl-formatter`)

This plan follows the Test-Driven Development (TDD) methodology and SOLID principles as outlined in the project's workflow and specification.

## Phase 1: Package Scaffold & Core Engine [checkpoint: 53eaead]
- [x] Task: Initialize `packages/capl-formatter/` workspace package e02d3e9
    - [x] Create `pyproject.toml`, `README.md`, and directory structure
    - [x] Configure `uv` workspace to include the new package
    - [x] Set up basic `pytest` configuration for the package
- [x] Task: Implement Core Abstractions (SOLID) 063ce53
    - [x] Write tests for rule discovery and strategy execution
    - [x] Implement `BaseFormattingRule` interface
    - [x] Implement `BaseRewriteStrategy` and a basic `TokenRewriteStrategy`
    - [x] Implement `FormatterConfig` dataclass/model
- [x] Task: Implement `FormatterEngine` 4e107a6
    - [x] Write tests for engine orchestration (applying multiple rules)
    - [x] Implement `FormatterEngine` to manage the flow of formatting a single file
    - [x] **Implement `FormatResult` and `FormatResults` dataclasses for structured output**
    - [x] Implement parse error handling (skip and log) within the engine
- [x] Task: Conductor - User Manual Verification 'Phase 1: Package Scaffold & Core Engine' (Protocol in workflow.md)

## Phase 2: Fundamental Syntax Formatting [checkpoint: e973b84]
- [x] Task: Implement Indentation and Whitespace Rules 739f531
    - [x] Write tests for 2-space indentation and trailing whitespace removal
    - [x] Implement `IndentationRule`
    - [x] Implement `WhitespaceCleanupRule` (trailing space, EOF newline, blank line collapsing)
- [x] Task: Implement Brace and Spacing Rules de0cb3e
    - [x] Write tests for K&R brace style and operator/comma spacing
    - [x] Implement `BraceStyleRule`
    - [x] Implement `SpacingRule`
- [x] **Task: Implement Quote Normalization Rule** 25bd81f
    - [x] **Write tests for double-quote enforcement in string literals**
    - [x] **Implement `QuoteNormalizationRule` (validate double quotes, flag single quotes as errors)**
- [x] Task: Implement Blank Line Rules 5b28f61
    - [x] Write tests for function/handler spacing (1 blank line) and major block spacing (2 blank lines)
    - [x] Implement `BlankLineRule`
- [x] Task: Implement Block Expansion and Keyword Spacing e973b84
    - [x] Implement `BlockExpansionRule` to expand blocks
    - [x] Update `SpacingRule` for keyword spacing
- [x] Task: Conductor - User Manual Verification 'Phase 2: Fundamental Syntax Formatting' (Protocol in workflow.md)

## Phase 3: Comment & Pragma Management [checkpoint: 28d4136]
- [x] Task: Implement Comment Reflow 28d4136
    - [x] Write tests for line (//) and block (/* */) comment reflowing at 100 chars
    - [x] Implement `CommentReflowRule` with JSDoc/Doxygen alignment support
- [x] Task: Implement Preservation Logic 28d4136
    - [x] Write tests for ASCII art header preservation (/****, /*====)
    - [x] Implement preservation logic within `CommentReflowRule`
- [x] Task: Implement Pragma Handling 28d4136
    - [x] Write tests for `#pragma library` preservation and positioning
    - [x] Implement `PragmaHandlingRule`
- [x] Task: Conductor - User Manual Verification 'Phase 3: Comment & Pragma Management' (Protocol in workflow.md)

## Phase 4: Structural Organization
- [ ] Task: Implement Include Sorting
    - [ ] Write tests for .cin/.can grouping and alphabetical sorting
    - [ ] Implement `IncludeSortingRule` (grouped, sorted, unique)
- [ ] Task: Implement Variable Ordering
    - [ ] Write tests for variable type hierarchy and alphabetical sorting
    - [ ] Implement `VariableOrderingRule` with inline comment preservation
- [ ] **Task: Implement Event Handler Ordering (Optional)**
    - [ ] **Write tests for standardized handler order (on start → on message → on timer → functions)**
    - [ ] **Implement `EventHandlerOrderingRule`**
- [ ] Task: Conductor - User Manual Verification 'Phase 4: Structural Organization' (Protocol in workflow.md)

## Phase 5: Intelligent Line Wrapping
- [ ] Task: Implement Definition Wrapping (Chop Down)
    - [ ] Write tests for long function signatures forced to "Chop Down"
    - [ ] Implement `DefinitionWrappingRule`
- [ ] Task: Implement Call and Initializer Wrapping (Heuristic)
    - [ ] Write tests for "Fit as many as possible" calls and smart initializer wrapping
    - [ ] Implement `CallWrappingRule` and `InitializerWrappingRule`
- [ ] Task: Conductor - User Manual Verification 'Phase 5: Intelligent Line Wrapping' (Protocol in workflow.md)

## Phase 6: CLI Integration & Configuration
- [ ] Task: Implement `drift format` command
    - [ ] Write tests for CLI argument parsing and multi-path support
    - [ ] **Write tests for handling large file sets (50+ files)**
    - [ ] Integrate `FormatterEngine` into the `drift` CLI
- [ ] Task: Implement `--check` and `--json` flags
    - [ ] Write tests for check-only mode and JSON output formatting
    - [ ] Implement violation reporting and exit code logic (0 success, 1 failure/violation)
- [ ] Task: Configuration File Support
    - [ ] Write tests for `.capl-format.toml` loading and overrides
    - [ ] Implement configuration discovery and merging logic
- [ ] Task: Conductor - User Manual Verification 'Phase 6: CLI Integration & Configuration' (Protocol in workflow.md)

## Phase 7: Final Polish & Documentation
- [ ] Task: Project-wide Integration Testing
    - [ ] Run formatter on all `examples/` files and verify output stability (idempotency)
    - [ ] Fix any edge cases discovered during bulk formatting
    - [ ] **Create regression test suite with "before/after" snapshots of formatted files**
- [ ] Task: Update Documentation
    - [ ] Update `README.md` with formatting features and examples
    - [ ] Add a "Formatting Guide" to the `docs/` directory
- [ ] Task: Conductor - User Manual Verification 'Phase 7: Final Polish & Documentation' (Protocol in workflow.md)
