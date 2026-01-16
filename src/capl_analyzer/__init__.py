"""
CAPL Analyzer - Static analysis tools for CAPL (CANoe/CANalyzer) code

This package provides:
- Dependency analysis and include tracking
- Symbol extraction (functions, variables, event handlers)
- Cross-reference system (find all references)
- Static analysis / linting
"""

__version__ = "0.1.0"

from .dependency_analyzer import CAPLDependencyAnalyzer
from .symbol_extractor import CAPLSymbolExtractor
from .cross_reference import CAPLCrossReferenceBuilder
from .linter import CAPLLinter, LintIssue, Severity

__all__ = [
    "CAPLDependencyAnalyzer",
    "CAPLSymbolExtractor",
    "CAPLCrossReferenceBuilder",
    "CAPLLinter",
    "LintIssue",
    "Severity",
]
