import pytest
from pathlib import Path
from capl_linter.engine import LinterEngine
from capl_symbol_db.extractor import SymbolExtractor
from capl_symbol_db.database import SymbolDatabase


def test_linter_forbidden_syntax(tmp_path):
    db_path = tmp_path / "test.db"
    engine = LinterEngine(str(db_path))

    code = "extern int x;"
    file_path = tmp_path / "test.can"
    file_path.write_text(code)

    # 1. Analyze (Extractor + Database)
    extractor = SymbolExtractor()
    syms = extractor.extract_all(file_path)

    db = SymbolDatabase(str(db_path))
    file_id = db.store_file(file_path, code.encode())
    db.store_symbols(file_id, syms)

    # 2. Lint
    issues = engine.analyze_file(file_path)

    assert len(issues) == 1
    assert issues[0].rule_id == "extern-keyword"
    assert "extern" in issues[0].message.lower()
