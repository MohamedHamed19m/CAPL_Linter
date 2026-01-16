from abc import ABC, abstractmethod
from typing import List
from pathlib import Path
from capl_symbol_db.database import SymbolDatabase
from ..models import InternalIssue


class BaseRule(ABC):
    """Abstract base class for all linting rules"""

    @property
    @abstractmethod
    def rule_id(self) -> str:
        pass

    @abstractmethod
    def check(self, file_path: Path, db: SymbolDatabase) -> List[InternalIssue]:
        pass
