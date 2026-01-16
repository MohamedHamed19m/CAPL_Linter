import pytest
from pathlib import Path
from capl_analyzer.symbol_extractor import CAPLSymbolExtractor, update_database_schema

def test_symbol_extraction(tmp_path):
    """Test symbol extraction on a CAPL file"""
    code = """
variables {
  int gVar;
}

void MyFunc() {
  int lVar;
}
"""
    test_file = tmp_path / "test_symbols.can"
    test_file.write_text(code)
    
    db_path = str(tmp_path / "test.db")
    update_database_schema(db_path=db_path)
    extractor = CAPLSymbolExtractor(db_path=db_path)
    
    num_symbols = extractor.store_symbols(str(test_file))
    assert num_symbols > 0
    
    symbols = extractor.list_symbols_in_file(str(test_file.resolve()))
    names = [s[0] for s in symbols]
    assert "gVar" in names
    assert "MyFunc" in names
    assert "lVar" in names