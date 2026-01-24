from __future__ import annotations

from pathlib import Path

from capl_symbol_db.database import SymbolDatabase
from capl_symbol_db.dependency import DependencyAnalyzer
from capl_symbol_db.extractor import SymbolExtractor
from capl_symbol_db.xref import CrossReferenceBuilder

from .models import InternalIssue
from .registry import RuleRegistry
from .rules.base import BaseRule


class LinterEngine:
    """Core engine for CAPL linting"""

    def __init__(self, db_path: str = "aic.db", custom_builtins: list[str] | None = None):
        self.db_path = db_path
        self.db = SymbolDatabase(db_path)
        self.extractor = SymbolExtractor()
        self.xref = CrossReferenceBuilder(self.db)
        self.dep_analyzer = DependencyAnalyzer(self.db)
        self.registry = RuleRegistry()
        self.issues: list[InternalIssue] = []
        self.custom_builtins = custom_builtins or []

    def analyze_file(
        self, file_path: Path, force: bool = False, rules: list[BaseRule] | None = None
    ) -> list[InternalIssue]:
        """Run lint checks on a file.

        Args:
            file_path: Path to the file
            force: Whether to re-analyze even if hash matches
            rules: Specific rules to run (if None, all registered rules are run)
        """
        file_path = file_path.resolve()

        # Ensure file is analyzed
        if force or self._needs_analysis(file_path):
            self._analyze_single_file(file_path)

        self.issues = []
        target_rules = rules if rules is not None else self.registry.get_all_rules()

        for rule in target_rules:
            # Inject custom builtins into semantic rules if they support it
            if hasattr(rule, "custom_builtins"):
                rule.custom_builtins = self.custom_builtins
            self.issues.extend(rule.check(file_path, self.db))

        return sorted(self.issues, key=lambda x: x.sort_key)

    def analyze_project(self, root_path: Path) -> int:
        """Scan all CAPL files in a directory to populate the database"""
        root_path = Path(root_path).resolve()
        count = 0

        # Find all .can and .cin files
        for ext in ["**/*.can", "**/*.cin"]:
            for file_path in root_path.glob(ext):
                if self._needs_analysis(file_path):
                    self._analyze_single_file(file_path)
                    count += 1

        return count

    def _analyze_single_file(self, file_path: Path):
        """Perform symbol extraction and XRef/Dependency analysis for one file"""
        syms = self.extractor.extract_all(file_path)
        with open(file_path, "rb") as f:
            source_code = f.read()
            file_id = self.db.store_file(file_path, source_code)
        self.db.store_symbols(file_id, syms)
        self.xref.analyze_file_references(file_path)
        self.dep_analyzer.analyze_file(file_path)

    def _needs_analysis(self, file_path: Path) -> bool:
        stored_hash = self.db.get_file_hash(file_path)
        if not stored_hash:
            return True

        import hashlib

        with open(file_path, "rb") as f:
            current_hash = hashlib.md5(f.read()).hexdigest()

        return stored_hash != current_hash
