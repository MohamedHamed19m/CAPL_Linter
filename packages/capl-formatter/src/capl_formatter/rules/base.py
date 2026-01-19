from dataclasses import dataclass
from abc import ABC, abstractmethod

@dataclass
class FormattingContext:
    source: str
    file_path: str = ""

class BaseFormattingRule(ABC):
    @abstractmethod
    def apply(self, context: FormattingContext) -> None:
        """Apply the formatting rule to the context."""
        pass
