from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from tree_sitter import Tree

@dataclass
class Transformation:
    """A single, atomic change to the source code using character offsets.
    
    Attributes:
        start_byte: Character offset where the change starts.
        end_byte: Character offset where the change ends.
        new_content: The new text to insert at this position.
        priority: Order of application if multiple transformations exist at the same position.
    """
    start_byte: int
    end_byte: int
    new_content: str
    priority: int = 0

@dataclass
class FormattingContext:
    """Read-only container for the source code and its AST during a formatting pass."""
    source: str
    file_path: str = ""
    tree: Optional[Tree] = None
    lines: List[str] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.lines is None:
            self.lines = self.source.splitlines(keepends=True)
        if self.metadata is None:
            self.metadata = {}

class FormattingRule(ABC):
    """Abstract base for all formatting rules."""
    @property
    @abstractmethod
    def rule_id(self) -> str: pass
    @property
    @abstractmethod
    def name(self) -> str: pass

class ASTRule(FormattingRule):
    """A rule that relies on tree-sitter AST for structural analysis."""
    @abstractmethod
    def analyze(self, context: FormattingContext) -> List[Transformation]: pass

class TextRule(FormattingRule):
    """A rule that operates primarily on raw text or line patterns."""
    @abstractmethod
    def analyze(self, context: FormattingContext) -> List[Transformation]: pass
