from dataclasses import dataclass, field
from typing import List, Optional, Literal, Any
from tree_sitter import Node


@dataclass
class FormatterConfig:
    indent_size: int = 2
    line_length: int = 100
    brace_style: str = "k&r"
    quote_style: str = "double"
    # Comment configuration
    enable_comment_features: bool = True
    align_inline_comments: bool = True
    inline_comment_column: int = 40
    reflow_comments: bool = True
    preserve_comment_proximity: bool = True


@dataclass
class CommentAttachment:
    comment_node: Node  # Tree-sitter node
    attachment_type: Literal["header", "inline", "footer", "standalone", "section"]
    target_node: Optional[Node]  # Associated code node
    comment_line: int  # Line number
    target_line: int  # Target's line number
    distance: int  # Lines between comment and target


@dataclass
class FormatResult:
    source: str
    modified: bool
    errors: List[str] = field(default_factory=list)


@dataclass
class FormatResults:
    results: List[FormatResult]
    total_files: int
    modified_files: int
    error_files: int
