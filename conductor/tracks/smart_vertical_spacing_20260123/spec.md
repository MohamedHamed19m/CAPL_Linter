# Track Specification: Smart Vertical Spacing

## Overview
Enhance the `capl-formatter` to support context-aware vertical whitespace management. This track introduces a "Setup vs. Logic" distinction, allowing the formatter to compress configuration code (declarations) while respecting the developer's intentional spacing for logical grouping in the logic phase.

## Functional Requirements
- **Setup Zone Compression**:
    - Within any `compound_statement` or function-local `variables` block, automatically remove all blank lines between consecutive declarations.
    - **Transparent Comments**: Comments located between declarations do not trigger the transition to the Logic Zone. They are treated as transparent for zone detection, and their proximity to the declarations they describe is maintained.
- **Logic Zone Preservation**:
    - Preservation begins at the first "Logic" node: `expression_statement`, `if_statement`, `if_else_statement`, `for_statement`, `while_statement`, `do_statement`, `switch_statement`, or `return_statement`.
    - Once in the Logic Zone, single blank lines between statements or function calls are preserved.
- **Top-Level Variables Block Preservation**:
    - **Top-level** `variables` blocks (global scope) are treated as "Preservation Zones." No compression is forced, allowing developers to group globals as desired.
- **Block Boundary Cleanup**:
    - Remove blank lines immediately following an opening brace `{`.
    - Remove blank lines immediately preceding a closing brace `}`.
- **Global Max Spacing**:
    - Enforce a maximum of one consecutive blank line (collapse 3+ newlines to exactly 2) throughout the entire file.

## Technical Requirements
- **New Rule**: Implement `VerticalSpacingRule` in `packages/capl-formatter/src/capl_formatter/rules/vertical_spacing.py`.
- **State-Aware Traversal**:
    - The rule must maintain a `is_setup_zone` state during block traversal.
    - Transition `is_setup_zone` to `False` permanently for that scope upon encountering the first logic node.
- **Engine Modifications**:
    - **Remove Aggressive Squashing**: Delete `re.sub(r";

+", r";
", source)` and `re.sub(r"
\s*
(\s*[}\]])", r"
\1", source)` from `engine.py`.
    - **Refine Cleanup**: Ensure `_cleanup_vertical_whitespace` respects the rule's preservation of single blank lines while continuing to collapse triple newlines to double.

## Acceptance Criteria
1. Local variables at the start of a function have zero blank lines between them.
2. Comments between setup declarations do not cause the remainder of the setup to be treated as logic.
3. Intentional blank lines between function calls in the logic zone are preserved (up to 1).
4. Top-level `variables` blocks preserve their internal blank lines.
5. Blank lines at the immediate start and end of blocks are removed.
6. All existing golden file tests pass (or are updated to reflect the new spacing logic).

## Out of Scope
- Reordering declarations or logic statements.
- Moving declarations that are mixed into the logic zone back to the setup zone.
