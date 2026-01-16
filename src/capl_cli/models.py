from typing import Literal

from pydantic import BaseModel, Field

SeverityType = Literal["ERROR", "WARNING", "INFO", "STYLE"]


class LintIssue(BaseModel):
    """External representation of a linting issue for CLI/API users"""

    severity: SeverityType
    file_path: str
    line_number: int = Field(gt=0)
    column: int = Field(ge=0)
    rule_id: str
    message: str
    suggestion: str | None = None
    auto_fixable: bool = False


class LinterConfig(BaseModel):
    """Configuration for the linter CLI"""

    db_path: str = "aic.db"
    severity_limit: SeverityType = "STYLE"
    fix_enabled: bool = False
    fix_only: list[str] | None = None
