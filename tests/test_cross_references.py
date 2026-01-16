from capl_symbol_db.database import SymbolDatabase
from capl_symbol_db.xref import CrossReferenceBuilder


def test_cross_references(tmp_path):
    code = """
    void Func1() {
      Func2();
    }
    void Func2() {}
    """
    file_path = tmp_path / "test.can"
    file_path.write_text(code)

    db_path = tmp_path / "test.db"
    db = SymbolDatabase(str(db_path))
    xref = CrossReferenceBuilder(db)

    num_refs = xref.analyze_file_references(file_path)
    assert num_refs > 0
