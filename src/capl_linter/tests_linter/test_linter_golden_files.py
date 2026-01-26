import difflib
from pathlib import Path

import pytest

from capl_formatter.engine import FormatterEngine
from capl_formatter.models import FormatterConfig
from capl_linter.autofix import AutoFixEngine
from capl_linter.engine import LinterEngine
from capl_symbol_db.database import SymbolDatabase
from capl_symbol_db.extractor import SymbolExtractor

FIXTURES_DIR = Path(__file__).parent / "fixtures"
INPUT_DIR = FIXTURES_DIR / "input"
EXPECTED_DIR = FIXTURES_DIR / "expected"


def get_test_cases():
    """Find all input files."""
    if not INPUT_DIR.exists():
        return []
    return [f.stem for f in INPUT_DIR.glob("*.can")]


@pytest.mark.parametrize("test_name", get_test_cases())
def test_linter_autofix_golden_file(test_name, tmp_path):
    """Test linter auto-fix against golden files."""

    # 1. Prepare temp file
    input_file = INPUT_DIR / f"{test_name}.can"
    input_source = input_file.read_text(encoding="utf-8")

    work_file = tmp_path / f"{test_name}.can"
    work_file.write_text(input_source, encoding="utf-8")

    # 2. Setup DB and Extract Symbols
    db_path = tmp_path / "test.db"
    extractor = SymbolExtractor()
    syms = extractor.extract_all(work_file)

    db = SymbolDatabase(str(db_path))
    file_id = db.store_file(work_file, input_source.encode())
    db.store_symbols(file_id, syms)

    # 3. Lint and Fix (Iterative with DB refresh)
    engine = LinterEngine(str(db_path))
    autofix = AutoFixEngine()

    max_passes = 5
    for _ in range(max_passes):
        # IMPORTANT: Refresh the DB facts before each pass
        current_content = work_file.read_text(encoding="utf-8")
        syms = extractor.extract_all(work_file)

        db = SymbolDatabase(str(db_path))
        db.clear_file_data(work_file)  # Ensure we don't have duplicate facts
        file_id = db.store_file(work_file, current_content.encode())
        db.store_symbols(file_id, syms)

        issues = engine.analyze_file(work_file)
        fixable = [i for i in issues if i.auto_fixable]
        if not fixable:
            break

        new_content = autofix.apply_fixes(work_file, fixable)
        work_file.write_text(new_content, encoding="utf-8")

    # 4. Format the result (The "Ruff" way)
    final_content = work_file.read_text(encoding="utf-8")
    formatter = FormatterEngine(FormatterConfig())
    formatter.add_default_rules()
    formatted_result = formatter.format_string(final_content)

    # 5. Compare
    expected_file = EXPECTED_DIR / f"{test_name}.can"
    expected_source = expected_file.read_text(encoding="utf-8")

    if formatted_result.source != expected_source:
        diff = difflib.unified_diff(
            expected_source.splitlines(keepends=True),
            formatted_result.source.splitlines(keepends=True),
            fromfile="expected",
            tofile="actual",
        )
        diff_text = "".join(diff)
        pytest.fail(f"Auto-fix + Format mismatch for {test_name}:\n{diff_text}")
