# Implementation Plan: Comprehensive Comment Handling

## Pre-Implementation: Setup
- [x] Create feature branch `feat/comment-handling`. 03e5c95
- [x] Document rollback strategy (Revert to main if Phase 1/2 fails; Disable rules if Phase 3 fails). 03e5c95

## Phase 1: Foundation (Data Structures & Engine Prep)
- [x] Task: Update `models.py` with `CommentAttachment` and enhanced `FormatterConfig`. 03e5c95
    - [x] Add `CommentAttachment` dataclass.
    - [x] Add `enable_comment_features` (master switch) and other config fields to `FormatterConfig`.
- [x] Task: Update `FormattingContext` in `rules/base.py` to support metadata. 03e5c95
    - [x] Add `metadata` field to `FormattingContext` and initialize in `__post_init__`.
- [x] Task: Prepare `engine.py` for Phase 0 processing. 03e5c95
    - [x] Stub `_build_comment_attachment_map` method (return empty dict).
    - [x] Inject `metadata` containing the attachment map into rule contexts.
- [x] Task: **Conductor Checkpoint** - Phase 1 Complete [checkpoint: d1bc274]
    - [x] All tasks in Phase 1 marked complete
    - [x] All Phase 1 exit criteria met
    - [x] All Phase 1 tests passing
    - [x] No regressions introduced
    - [x] Code reviewed by conductor
    - [x] Approval to proceed to Phase 2

### Phase 1 Exit Criteria
- [x] All Phase 1 tasks completed
- [x] `CommentAttachment` dataclass compiles without errors
- [x] `FormatterConfig` has new fields with defaults
- [x] `FormattingContext.metadata` is initialized in `__post_init__`
- [x] `_build_comment_attachment_map()` stub exists and returns empty dict
- [x] Engine passes `metadata` to at least one rule in Phase 1
- [x] No existing tests broken
- [x] Conductor approval received

## Phase 2: Comment Attachment & Preservation
- [x] Task: Add Debug Utilities (Temporary). 3748252
    - [x] Create `debug_comment_map.py` to visualize comment attachments.
- [x] Task: Implement Comment Attachment Map logic in `engine.py`. 3748252
    - [x] Implement `_find_all_comments` to extract comment nodes from AST.
    - [x] **TEST CHECKPOINT**: Create `test_find_all_comments()` - verify it finds 10 comments in test file
    - [x] Implement `_classify_comment` to determine attachment type.
    - [x] **TEST CHECKPOINT**: Create `test_classify_comment()` - verify all 5 types detected
    - [x] Implement `_build_comment_attachment_map` to link comments to target nodes.
    - [x] **TEST CHECKPOINT**: Run `test_header_comment_proximity()` - should pass now
- [x] Task: Implement Comment Proximity Preservation in `engine.py`. 3748252
    - [x] Update `_cleanup_vertical_whitespace` to skip blank lines using attachment map.
- [x] Task: Update Structural Rules for Comment Awareness. 3748252
    - [x] Modify `BlockExpansionRule` to preserve inline comments during brace expansion.
    - [x] **TEST CHECKPOINT**: Run `test_block_expansion_with_inline_comment()` - should pass
    - [x] Modify `StatementSplitRule` to preserve inline comments when splitting lines.
    - [x] **TEST CHECKPOINT**: Run `test_inline_comment_preservation()` - should pass
- [x] Task: **Conductor Checkpoint** - Phase 2 Complete [checkpoint: 3748252]
    - [x] All tasks in Phase 2 marked complete
    - [x] All Phase 2 exit criteria met
    - [x] All Phase 2 tests passing
    - [x] No regressions introduced
    - [x] Code reviewed by conductor
    - [x] Approval to proceed to Phase 3

### Phase 2 Exit Criteria
- [x] All Phase 2 tasks completed
- [x] `_classify_comment()` correctly identifies all 5 attachment types
- [x] Comment map contains entries for test file with 10+ comments
- [x] `BlockExpansionRule` preserves inline comments (verified by new test)
- [x] `StatementSplitRule` doesn't split lines with inline comments
- [x] Header comments have NO blank line after cleanup (verified by test)
- [x] `test_header_comment_proximity()` passes
- [x] `test_inline_comment_preservation()` passes
- [x] No regressions in existing tests
- [x] Conductor approval received

## Phase 3: Alignment & Reflowing (Final Polish)
- [x] Task: Implement `CommentAlignmentRule` in `rules/comments.py`. 8aad750
    - [x] Logic to vertically align inline comments in consecutive blocks.
    - [x] **TEST CHECKPOINT**: Run `test_inline_comment_alignment()` - should pass
- [x] Task: Enhance and Move `CommentReflowRule`. 8aad750
    - [x] Implement "Match Start" wrapping style.
    - [x] Add exclusion logic for Doxygen tags, ASCII art, and Pragmas.
    - [x] Move rule execution to Phase 3 in `engine.py`.
    - [x] **TEST CHECKPOINT**: Run `test_comment_reflow_long_line()` - should pass
- [x] Task: Handle Edge Cases. 8aad750
    - [x] Implement logic for malformed comments and very long words.
    - [x] Ensure UTF-8/Emoji support in length calculations.
- [x] Task: **Conductor Checkpoint** - Phase 3 Complete [checkpoint: 8aad750]
    - [x] All tasks in Phase 3 marked complete
    - [x] All Phase 3 exit criteria met
    - [x] All Phase 3 tests passing
    - [x] No regressions introduced
    - [x] Code reviewed by conductor
    - [x] Approval to proceed to Phase 4

### Phase 3 Exit Criteria
- [x] All Phase 3 tasks completed
- [x] `CommentAlignmentRule` aligns 5+ consecutive inline comments
- [x] `CommentReflowRule` wraps comments > line_length
- [x] Doxygen `@param` blocks unchanged (test verifies)
- [x] ASCII art diagrams unchanged (test verifies)
- [x] UTF-8 comments align correctly (test with emoji)
- [x] `test_inline_comment_alignment()` passes
- [x] `test_comment_reflow_long_line()` passes
- [x] `test_doxygen_preservation()` passes
- [x] `test_ascii_art_preservation()` passes
- [x] No regressions in existing tests
- [x] Conductor approval received

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
