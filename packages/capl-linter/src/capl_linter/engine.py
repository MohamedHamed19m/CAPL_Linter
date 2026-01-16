from typing import List, Optional, Dict
from pathlib import Path
from capl_symbol_db.database import SymbolDatabase
from capl_symbol_db.extractor import SymbolExtractor
from capl_symbol_db.xref import CrossReferenceBuilder
from capl_symbol_db.dependency import DependencyAnalyzer
from .models import InternalIssue
from .registry import RuleRegistry

class LinterEngine:
    """Core engine for CAPL linting"""

    def __init__(self, db_path: str = "aic.db"):
        self.db_path = db_path
        self.db = SymbolDatabase(db_path)
        self.extractor = SymbolExtractor()
        self.xref = CrossReferenceBuilder(self.db)
        self.dep_analyzer = DependencyAnalyzer(self.db)
        self.registry = RuleRegistry()
        self.issues: List[InternalIssue] = []

    def analyze_file(self, file_path: Path, force: bool = False) -> List[InternalIssue]:
        """Run all lint checks on a file"""
        file_path = file_path.resolve()
        
        # Ensure file is analyzed
        if force or self._needs_analysis(file_path):
            syms = self.extractor.extract_all(file_path)
            with open(file_path, "rb") as f:
                source_code = f.read()
                file_id = self.db.store_file(file_path, source_code)
            self.db.store_symbols(file_id, syms)
            self.xref.analyze_file_references(file_path)
            self.dep_analyzer.analyze_file(file_path)
            
        self.issues = []
        for rule in self.registry.get_all_rules():
            self.issues.extend(rule.check(file_path, self.db))
            
        return sorted(self.issues, key=lambda x: x.line)

    def _needs_analysis(self, file_path: Path) -> bool:
        stored_hash = self.db.get_file_hash(file_path)
        if not stored_hash:
            return True
            
        import hashlib
        with open(file_path, "rb") as f:
            current_hash = hashlib.md5(f.read()).hexdigest()
            
        return stored_hash != current_hash
