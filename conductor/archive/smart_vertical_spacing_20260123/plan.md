# Implementation Plan: Smart Vertical Spacing

## Phase 1: Core Engine Refactoring [checkpoint: 5db2267]
- [x] Task: Remove aggressive vertical squashing from `engine.py`. [5db2267]
    - [x] Delete `re.sub(r";

+", r";
", source)`.
    - [x] Delete `re.sub(r"
\s*
(\s*[}\]])", r"
\1", source)`.
- [x] Task: Refine `_cleanup_vertical_whitespace` logic in `engine.py`. [5db2267]
    - [x] Ensure `
{3,}` is collapsed to `

` (Global Max 1 Blank Line).
- [x] Task: Conductor - User Manual Verification 'Phase 1: Core Engine Refactoring' (Protocol in workflow.md) [5db2267]

## Phase 2: Rule Implementation [checkpoint: 0aa393e]
- [x] Task: Create `packages/capl-formatter/src/capl_formatter/rules/vertical_spacing.py`. [0aa393e]
- [x] Task: Define `LOGIC_NODE_TYPES` set based on CAPL grammar. [0aa393e]
    - [x] Include: `expression_statement`, `if_statement`, `if_else_statement`, `for_statement`, `while_statement`, `do_statement`, `switch_statement`, `return_statement`.
- [x] Task: Implement `VerticalSpacingRule` with zone state machine. [0aa393e]
    - [x] Implement `_should_process_block` helper to distinguish between Global variables (Skip) and Local variables or `compound_statement` (Process).
    - [x] Implement `is_setup_zone` flag that flips to `False` on the first Logic Node.
    - [x] Implement comment transparency logic (comments don't flip the zone).
    - [x] Logic for compressing `

+` to `
` in Setup Zone.
- [x] Task: Implement AST-based Brace Edge Cleanup within the rule. [0aa393e]
    - [x] Target space between `{` and first named child.
    - [x] Target space between last named child and `}`.
- [x] Task: Register `VerticalSpacingRule` in `engine.py`'s `add_default_rules`. [0aa393e]
- [x] Task: Conductor - User Manual Verification 'Phase 2: Rule Implementation' (Protocol in workflow.md) [0aa393e]

## Phase 3: Verification & Regression [checkpoint: 0aa393e]
- [x] Task: Create a new golden file test `vertical_spacing_comprehensive.can`. [0aa393e]
    - [x] Case: Compact setup variables.
    - [x] Case: Preserved spacing in logic calls.
    - [x] Case: Preserved spacing in global variables.
    - [x] Case: Comment transparency in setup.
    - [x] Case: Mixed-content (declarations after logic should NOT compress).
- [x] Task: Run all golden file tests and update existing snapshots/goldens if spacing changes are intentional. [0aa393e]
- [x] Task: Verify fix for `IP_Endpoint` still holds (no regression in ERROR node protection). [0aa393e]
- [x] Task: Conductor - User Manual Verification 'Phase 3: Verification & Regression' (Protocol in workflow.md) [0aa393e]