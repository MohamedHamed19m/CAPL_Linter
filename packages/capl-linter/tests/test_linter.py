from capl_linter.engine import LinterEngine
from capl_symbol_db.database import SymbolDatabase
from capl_symbol_db.extractor import SymbolExtractor


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

    # It should find two issues:
    # 1. Extern keyword (E001)
    # 2. Variable outside block (E006)
    assert len(issues) == 2
    assert any(i.rule_id == "E001" for i in issues)
    assert any(i.rule_id == "E006" for i in issues)
