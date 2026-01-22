# Implementation Plan: Comprehensive Comment Handling

## Pre-Implementation: Setup
- [ ] Create feature branch `feat/comment-handling`.
- [ ] Document rollback strategy (Revert to main if Phase 1/2 fails; Disable rules if Phase 3 fails).

## Phase 1: Foundation (Data Structures & Engine Prep)
- [ ] Task: Update `models.py` with `CommentAttachment` and enhanced `FormatterConfig`.
    - [ ] Add `CommentAttachment` dataclass.
    - [ ] Add `enable_comment_features` (master switch) and other config fields to `FormatterConfig`.
- [ ] Task: Update `FormattingContext` in `rules/base.py` to support metadata.
    - [ ] Add `metadata` field to `FormattingContext` and initialize in `__post_init__`.
- [ ] Task: Prepare `engine.py` for Phase 0 processing.
    - [ ] Stub `_build_comment_attachment_map` method (return empty dict).
    - [ ] Inject `metadata` containing the attachment map into rule contexts.
- [ ] Task: **Conductor Checkpoint** - Phase 1 Complete
    - [ ] All tasks in Phase 1 marked complete
    - [ ] All Phase 1 exit criteria met
    - [ ] All Phase 1 tests passing
    - [ ] No regressions introduced
    - [ ] Code reviewed by conductor
    - [ ] Approval to proceed to Phase 2

### Phase 1 Exit Criteria
- [ ] All Phase 1 tasks completed
- [ ] `CommentAttachment` dataclass compiles without errors
- [ ] `FormatterConfig` has new fields with defaults
- [ ] `FormattingContext.metadata` is initialized in `__post_init__`
- [ ] `_build_comment_attachment_map()` stub exists and returns empty dict
- [ ] Engine passes `metadata` to at least one rule in Phase 1
- [ ] No existing tests broken
- [ ] Conductor approval received

## Phase 2: Comment Attachment & Preservation
- [ ] Task: Add Debug Utilities (Temporary).
    - [ ] Create `debug_comment_map.py` to visualize comment attachments.
- [ ] Task: Implement Comment Attachment Map logic in `engine.py`.
    - [ ] Implement `_find_all_comments` to extract comment nodes from AST.
    - [ ] **TEST CHECKPOINT**: Create `test_find_all_comments()` - verify it finds 10 comments in test file
    - [ ] Implement `_classify_comment` to determine attachment type.
    - [ ] **TEST CHECKPOINT**: Create `test_classify_comment()` - verify all 5 types detected
    - [ ] Implement `_build_comment_attachment_map` to link comments to target nodes.
    - [ ] **TEST CHECKPOINT**: Run `test_header_comment_proximity()` - should pass now
- [ ] Task: Implement Comment Proximity Preservation in `engine.py`.
    - [ ] Update `_cleanup_vertical_whitespace` to skip blank lines using attachment map.
- [ ] Task: Update Structural Rules for Comment Awareness.
    - [ ] Modify `BlockExpansionRule` to preserve inline comments during brace expansion.
    - [ ] **TEST CHECKPOINT**: Run `test_block_expansion_with_inline_comment()` - should pass
    - [ ] Modify `StatementSplitRule` to preserve inline comments when splitting lines.
    - [ ] **TEST CHECKPOINT**: Run `test_inline_comment_preservation()` - should pass
- [ ] Task: **Conductor Checkpoint** - Phase 2 Complete
    - [ ] All tasks in Phase 2 marked complete
    - [ ] All Phase 2 exit criteria met
    - [ ] All Phase 2 tests passing
    - [ ] No regressions introduced
    - [ ] Code reviewed by conductor
    - [ ] Approval to proceed to Phase 3

### Phase 2 Exit Criteria
- [ ] All Phase 2 tasks completed
- [ ] `_classify_comment()` correctly identifies all 5 attachment types
- [ ] Comment map contains entries for test file with 10+ comments
- [ ] `BlockExpansionRule` preserves inline comments (verified by new test)
- [ ] `StatementSplitRule` doesn't split lines with inline comments
- [ ] Header comments have NO blank line after cleanup (verified by test)
- [ ] `test_header_comment_proximity()` passes
- [ ] `test_inline_comment_preservation()` passes
- [ ] No regressions in existing tests
- [ ] Conductor approval received

## Phase 3: Alignment & Reflowing (Final Polish)
- [ ] Task: Implement `CommentAlignmentRule` in `rules/comments.py`.
    - [ ] Logic to vertically align inline comments in consecutive blocks.
    - [ ] **TEST CHECKPOINT**: Run `test_inline_comment_alignment()` - should pass
- [ ] Task: Enhance and Move `CommentReflowRule`.
    - [ ] Implement "Match Start" wrapping style.
    - [ ] Add exclusion logic for Doxygen tags, ASCII art, and Pragmas.
    - [ ] Move rule execution to Phase 3 in `engine.py`.
    - [ ] **TEST CHECKPOINT**: Run `test_comment_reflow_long_line()` - should pass
- [ ] Task: Handle Edge Cases.
    - [ ] Implement logic for malformed comments and very long words.
    - [ ] Ensure UTF-8/Emoji support in length calculations.
- [ ] Task: **Conductor Checkpoint** - Phase 3 Complete
    - [ ] All tasks in Phase 3 marked complete
    - [ ] All Phase 3 exit criteria met
    - [ ] All Phase 3 tests passing
    - [ ] No regressions introduced
    - [ ] Code reviewed by conductor
    - [ ] Approval to proceed to Phase 4

### Phase 3 Exit Criteria
- [ ] All Phase 3 tasks completed
- [ ] `CommentAlignmentRule` aligns 5+ consecutive inline comments
- [ ] `CommentReflowRule` wraps comments > line_length
- [ ] Doxygen `@param` blocks unchanged (test verifies)
- [ ] ASCII art diagrams unchanged (test verifies)
- [ ] UTF-8 comments align correctly (test with emoji)
- [ ] `test_inline_comment_alignment()` passes
- [ ] `test_comment_reflow_long_line()` passes
- [ ] `test_doxygen_preservation()` passes
- [ ] `test_ascii_art_preservation()` passes
- [ ] No regressions in existing tests
- [ ] Conductor approval received

## Phase 4: Integration & Validation
- [ ] Task: Create Comprehensive Test Fixtures.
    - [ ] Add `tests/test_comments.py` with all required unit test cases.
    - [ ] Add `comments_comprehensive.can` golden files (input and expected).
- [ ] Task: Regression Testing & Snapshots.
    - [ ] Run full test suite and ensure no regressions.
    - [ ] Update snapshot tests with `--snapshot-update`.
- [ ] Task: Performance Benchmarking.
    - [ ] Verify < 10% performance overhead.
- [ ] Task: Documentation Updates.
    - [ ] Update `GEMINI.md` Section "Core Rules Reference".
    - [ ] Update `GEMINI.md` Section "Common Anti-patterns".
    - [ ] Update `README.md` with features and config options.
- [ ] Task: **Conductor Checkpoint** - Phase 4 Complete
    - [ ] All tasks in Phase 4 marked complete
    - [ ] All Phase 4 exit criteria met
    - [ ] All Phase 4 tests passing
    - [ ] No regressions introduced
    - [ ] Code reviewed by conductor
    - [ ] Approval to proceed to Post-Implementation

### Phase 4 Exit Criteria
- [ ] All Phase 4 tasks completed
- [ ] Golden file `comments_comprehensive.can` passes
- [ ] All 8 unit tests in `test_comments.py` pass
- [ ] All existing golden files still pass
- [ ] Snapshots updated and reviewed
- [ ] Performance < 10% overhead (benchmark documented)
- [ ] Idempotency verified: format(format(x)) == format(x)
- [ ] GEMINI.md updated with comment handling section
- [ ] Conductor approval received

## Post-Implementation: Cleanup
- [ ] Task: Remove debug code and scripts.
- [ ] Task: Final regression test.
- [ ] Task: Merge feature branch.
