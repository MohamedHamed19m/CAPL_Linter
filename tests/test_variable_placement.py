import pytest
from capl_linter.engine import LinterEngine


def test_variable_outside_variables_block(tmp_path):
    code = "int gVar; // Outside block"
    file_path = tmp_path / "test.can"
    file_path.write_text(code)

    db_path = tmp_path / "test.db"
    engine = LinterEngine(str(db_path))

    issues = engine.analyze_file(file_path)

    # Should find E006
    assert any(i.rule_id == "E006" for i in issues)
