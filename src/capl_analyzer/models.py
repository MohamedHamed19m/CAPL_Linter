
from typing import List, Optional
from pydantic import BaseModel, Field
from enum import Enum

class Severity(str, Enum):
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"
    STYLE = "STYLE"

class LintIssue(BaseModel):
    severity: Severity
    file_path: str
    line_number: int
    column: int
    rule_id: str
    message: str
    suggestion: Optional[str] = None
    auto_fixable: bool = False

class LinterConfig(BaseModel):
    db_path: str = "aic.db"
    severity_limit: Severity = Severity.STYLE
    fix_enabled: bool = False
    fix_only: Optional[List[str]] = None
