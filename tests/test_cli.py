from typer.testing import CliRunner

from src.capl_cli.main import app

runner = CliRunner()


def test_cli_lint_help():
    result = runner.invoke(app, ["lint", "--help"])
    assert result.exit_code == 0
    assert "Run linter on CAPL files" in result.stdout


def test_cli_analyze(tmp_path):
    code = "variables { int x; }"
    file_path = tmp_path / "test.can"
    file_path.write_text(code)

    db_path = tmp_path / "test.db"

    result = runner.invoke(app, ["analyze", str(file_path), "--db", str(db_path)])
    assert result.exit_code == 0
    assert "Analyzing" in result.stdout
    assert "symbols" in result.stdout


def test_cli_lint_extern(tmp_path):
    code = "extern int x;"
    file_path = tmp_path / "test.can"
    file_path.write_text(code)

    db_path = tmp_path / "test.db"

    # First analyze
    runner.invoke(app, ["analyze", str(file_path), "--db", str(db_path)])

    # Then lint
    result = runner.invoke(app, ["lint", str(file_path), "--db", str(db_path)])
    assert result.exit_code == 1  # Exit code 1 because of ERROR
    assert "ERROR" in result.stdout
    assert "extern-keyword" in result.stdout
