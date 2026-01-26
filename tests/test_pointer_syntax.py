from pathlib import Path

from capl_linter.engine import LinterEngine


def test_linter_pointer_syntax():
    db_path = "test_pointer.db"
    if Path(db_path).exists():
        Path(db_path).unlink()

    engine = LinterEngine(db_path=db_path)

    # Path to the example file
    file_path = Path("examples/Pointers_errors.can")

    # Analyze the file
    issues = engine.analyze_file(file_path, force=True)

    # Filter issues by the new rules E008 and E009
    arrow_issues = [i for i in issues if i.rule_id == "E008"]
    param_issues = [i for i in issues if i.rule_id == "E009"]

    # From Pointers_errors.can:
    # 1. void MyFunc2(struct Data* data_ptr) -> E009 (pointer_parameter)
    # 2. write("Data ID: %d", data_ptr->id); -> E008 (arrow_operator)

    assert len(param_issues) >= 1
    assert len(arrow_issues) >= 1

    assert any("Pointer parameter" in i.message for i in param_issues)
    assert any("Arrow operator '->'" in i.message for i in arrow_issues)

    # Cleanup
    if Path(db_path).exists():
        Path(db_path).unlink()


def test_arrow_operator_autofix(tmp_path):
    from textwrap import dedent

    code = dedent(
        """
        void MyFunc(struct Data data_ptr) {
            data_ptr->id = 5;
        }
        """
    ).strip()
    file_path = tmp_path / "test_fix.can"
    file_path.write_text(code, encoding="utf-8")

    db_path = tmp_path / "test.db"

    from typer.testing import CliRunner

    from src.capl_cli.main import app

    runner = CliRunner()

    # Apply fix
    result = runner.invoke(app, ["lint", str(file_path), "--db", str(db_path), "--fix"])
    print(result.output)
    assert result.exit_code == 0

    fixed_code = file_path.read_text()
    assert "data_ptr.id = 5;" in fixed_code
    assert "->" not in fixed_code
