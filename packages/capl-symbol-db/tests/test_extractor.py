import pytest
from pathlib import Path
from capl_symbol_db.extractor import SymbolExtractor
from capl_symbol_db.database import SymbolDatabase


def test_symbol_extraction(tmp_path):
    extractor = SymbolExtractor()
    code = """
    enum MyEnum { val1, val2 };
    on message EngineData {
      write("Engine!");
    }
    """
    file_path = tmp_path / "test.can"
    file_path.write_text(code)

    symbols = extractor.extract_all(file_path)

    # Check for enum definition
    enum_syms = [s for s in symbols if s.context == "enum_definition"]
    assert len(enum_syms) == 1
    assert enum_syms[0].name == "MyEnum"

    # Check for event handler
    on_msg = [s for s in symbols if s.symbol_type == "event_handler"]
    assert len(on_msg) == 1
    assert on_msg[0].name == "EngineData"


def test_database_storage(tmp_path):
    db_path = tmp_path / "test.db"
    db = SymbolDatabase(str(db_path))

    code = b"on start {}"
    file_path = tmp_path / "test.can"
    file_path.write_bytes(code)

    file_id = db.store_file(file_path, code)
    assert file_id > 0

    from capl_symbol_db.models import SymbolInfo

    syms = [SymbolInfo(name="on start", symbol_type="event_handler", line_number=1)]
    db.store_symbols(file_id, syms)

    # Verify hash
    stored_hash = db.get_file_hash(file_path)
    import hashlib

    assert stored_hash == hashlib.md5(code).hexdigest()
