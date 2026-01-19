from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class FormatterConfig:
    indent_size: int = 2
    line_length: int = 100
    brace_style: str = "k&r"
    quote_style: str = "double"

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
