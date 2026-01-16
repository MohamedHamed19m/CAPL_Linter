"""
CAPL Analyzer - Static analysis tools for CAPL (CANoe/CANalyzer) code

This package provides:
- Dependency analysis and include tracking
- Symbol extraction (functions, variables, event handlers)
- Cross-reference system (find all references)
- Static analysis / linting
"""

__version__ = "0.1.0"

from .cross_reference import CAPLCrossReferenceBuilder
from .dependency_analyzer import CAPLDependencyAnalyzer
from .linter import CAPLLinter, LintIssue, Severity
from .symbol_extractor import CAPLSymbolExtractor

__all__ = [
    "CAPLDependencyAnalyzer",
    "CAPLSymbolExtractor",
    "CAPLCrossReferenceBuilder",
    "CAPLLinter",
    "LintIssue",
    "Severity",
]
