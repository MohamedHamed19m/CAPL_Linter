import re
import textwrap
from typing import List, Optional
from .base import ASTRule, TextRule, FormattingContext, Transformation
from ..models import FormatterConfig, CommentAttachment

class CommentAlignmentRule(TextRule):
    """Aligns inline comments vertically."""
    
    def __init__(self, config: FormatterConfig):
        self.config = config

    @property
    def rule_id(self) -> str: return "F013"
    @property
    def name(self) -> str: return "comment-alignment"

    def analyze(self, context: FormattingContext) -> List[Transformation]:
        if not self.config.align_inline_comments: return []
        if not context.metadata or 'comment_attachments' not in context.metadata: return []
        
        transformations = []
        comment_map = context.metadata['comment_attachments']
        
        # Identify groups of consecutive lines with inline comments
        inline_comments = [c for c in comment_map.values() if c.attachment_type == 'inline']
        if not inline_comments: return []
        
        # Group by line number proximity (consecutive lines)
        groups = []
        # Sort by line number
        inline_comments.sort(key=lambda x: x.comment_line)
        
        current_group = [inline_comments[0]]
        for i in range(1, len(inline_comments)):
            c = inline_comments[i]
            last = current_group[-1]
            if c.comment_line == last.comment_line + 1:
                current_group.append(c)
            else:
                groups.append(current_group)
                current_group = [c]
        if current_group:
            groups.append(current_group)
            
        # Process groups
        for group in groups:
            if len(group) < 2: continue # Only align if 2+ lines
            
            max_code_end = 0
            
            # Calculate required column
            for c in group:
                line = context.lines[c.comment_line]
                col = c.comment_node.start_point[1]
                text_before = line[:col].rstrip()
                code_end = len(text_before)
                max_code_end = max(max_code_end, code_end)
            
            target_col = max(self.config.inline_comment_column, max_code_end + 2)
            
            for c in group:
                line = context.lines[c.comment_line]
                current_col = c.comment_node.start_point[1]
                
                # Check if we need to change spaces
                # Find start byte of comment
                start_byte = c.comment_node.start_byte
                
                # Find extent of spaces before comment
                pos = start_byte - 1
                while pos >= 0 and context.source[pos] in [' ', '\t']:
                    pos -= 1
                
                text_before = context.source[0:pos+1].splitlines()[-1] if pos >= 0 else ""
                # Simple calc: we know where the code ends (pos+1)
                
                # Verify we aren't messing up (safety check)
                if pos + 1 >= start_byte: 
                    # No spaces? Insert some
                    spaces_needed = target_col - len(text_before)
                    if spaces_needed < 1: spaces_needed = 1
                    transformations.append(Transformation(start_byte, start_byte, " " * spaces_needed))
                else:
                    # Replace existing spaces
                    # Recalculate code len from source to be safe
                    # Actually we did max_code_end using line slicing, which is correct
                    # The text_before calculated here might be different if context.lines logic differed
                    
                    code_len_on_line = c.comment_node.start_point[1] - (start_byte - (pos + 1))
                    # Wait, start_point[1] is col of comment start.
                    # start_byte is global.
                    # pos+1 is global end of code.
                    # So (start_byte - (pos+1)) is length of space gap.
                    # So code_len = start_point[1] - gap_len.
                    
                    gap_len = start_byte - (pos + 1)
                    actual_code_end = c.comment_node.start_point[1] - gap_len
                    
                    spaces_needed = target_col - actual_code_end
                    if spaces_needed < 1: spaces_needed = 1
                    
                    transformations.append(Transformation(
                        start_byte=pos + 1,
                        end_byte=start_byte,
                        new_content=" " * spaces_needed
                    ))
                
        return transformations

class CommentReflowRule(TextRule):
    """Reflows comments to stay within line length."""
    def __init__(self, config: FormatterConfig):
        self.config = config

    @property
    def rule_id(self) -> str: return "F012"
    @property
    def name(self) -> str: return "comment-reflow"

    def analyze(self, context: FormattingContext) -> List[Transformation]:
        if not self.config.reflow_comments: return []
        
        transformations = []
        # Pattern for comments only (avoid strings which are handled by parser usually, 
        # but TextRule runs on source. We must be careful not to touch comments inside strings.
        # But CAPL comments // and /* are distinct.
        pattern = r'(\/\/.*)|(\/\*[\s\S]*?\*\/)'
        
        for m in re.finditer(pattern, context.source):
            comment = m.group(0)
            
            # Exclusions
            if self._should_exclude(comment): continue
            
            # Find indentation
            start_offset = m.start()
            line_start = context.source.rfind('\n', 0, start_offset) + 1
            if line_start == 0 and start_offset > 0 and context.source[start_offset-1] != '\n':
                # Comment is inline or not at start of file
                pass
            
            indent_str = context.source[line_start:start_offset]
            # If inline comment (indent contains code), we handle differently?
            # For reflow, we treat "Match Start" as: align with //
            
            # Calculate effective indent for wrapping
            # Just use spaces equal to column of //
            col = start_offset - line_start
            prefix = " " * col + "// "
            
            if comment.startswith("//"):
                if len(comment) + col > self.config.line_length:
                    content = comment[2:].strip()
                    width = self.config.line_length - len(prefix)
                    if width < 20: width = 20
                    
                    wrapped = textwrap.wrap(content, width=width, break_long_words=False)
                    if not wrapped: continue
                    
                    new_comment = "// " + wrapped[0]
                    if len(wrapped) > 1:
                        # For subsequent lines, use prefix
                        sep = "\n" + " " * col + "// "
                        new_comment += sep + sep.join(wrapped[1:])
                    
                    transformations.append(Transformation(m.start(), m.end(), new_comment))
            
            # TODO: Block comment reflow (simplified for now to avoid breaking Doxygen)
            
        return transformations

    def _should_exclude(self, comment: str) -> bool:
        if comment.startswith("/**") or comment.startswith("///") or "@param" in comment:
            return True
        if "+-" in comment or "| " in comment or "---" in comment or "***" in comment:
            return True
        return False