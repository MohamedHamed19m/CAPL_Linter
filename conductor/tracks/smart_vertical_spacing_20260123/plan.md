# Implementation Plan: Smart Vertical Spacing

## Phase 1: Core Engine Refactoring
- [ ] Task: Remove aggressive vertical squashing from `engine.py`.
    - [ ] Delete `re.sub(r";

+", r";
", source)`.
    - [ ] Delete `re.sub(r"
\s*
(\s*[}\]])", r"
\1", source)`.
- [ ] Task: Refine `_cleanup_vertical_whitespace` logic in `engine.py`.
    - [ ] Ensure `
{3,}` is collapsed to `

` (Global Max 1 Blank Line).
- [ ] Task: Conductor - User Manual Verification 'Phase 1: Core Engine Refactoring' (Protocol in workflow.md)

## Phase 2: Rule Implementation
- [ ] Task: Create `packages/capl-formatter/src/capl_formatter/rules/vertical_spacing.py`.
- [ ] Task: Define `LOGIC_NODE_TYPES` set based on CAPL grammar.
    - [ ] Include: `expression_statement`, `if_statement`, `if_else_statement`, `for_statement`, `while_statement`, `do_statement`, `switch_statement`, `return_statement`.
- [ ] Task: Implement `VerticalSpacingRule` with zone state machine.
    - [ ] Implement `_should_process_block` helper to distinguish between Global variables (Skip) and Local variables or `compound_statement` (Process).
    - [ ] Implement `is_setup_zone` flag that flips to `False` on the first Logic Node.
    - [ ] Implement comment transparency logic (comments don't flip the zone).
    - [ ] Logic for compressing `

+` to `
` in Setup Zone.
- [ ] Task: Implement AST-based Brace Edge Cleanup within the rule.
    - [ ] Target space between `{` and first named child.
    - [ ] Target space between last named child and `}`.
- [ ] Task: Register `VerticalSpacingRule` in `engine.py`'s `add_default_rules`.
- [ ] Task: Conductor - User Manual Verification 'Phase 2: Rule Implementation' (Protocol in workflow.md)

## Phase 3: Verification & Regression
- [ ] Task: Create a new golden file test `vertical_spacing_comprehensive.can`.
    - [ ] Case: Compact setup variables.
    - [ ] Case: Preserved spacing in logic calls.
    - [ ] Case: Preserved spacing in global variables.
    - [ ] Case: Comment transparency in setup.
    - [ ] Case: Mixed-content (declarations after logic should NOT compress).
- [ ] Task: Run all golden file tests and update existing snapshots/goldens if spacing changes are intentional.
- [ ] Task: Verify fix for `IP_Endpoint` still holds (no regression in ERROR node protection).
- [ ] Task: Conductor - User Manual Verification 'Phase 3: Verification & Regression' (Protocol in workflow.md)
