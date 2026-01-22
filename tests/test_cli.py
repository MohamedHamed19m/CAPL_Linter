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
    assert "E001" in result.stdout


def test_cli_format_basic(tmp_path):
    code = "variables{int x=1;}"
    file_path = tmp_path / "test.can"
    file_path.write_text(code)

    result = runner.invoke(app, ["format", str(file_path)])
    assert result.exit_code == 0
    assert "MODIFIED" in result.stdout

    # Check if file was actually modified
    formatted_code = file_path.read_text()
    assert "variables {" in formatted_code
    assert "  int x = 1;" in formatted_code


def test_cli_format_check(tmp_path):
    code = "variables{int x=1;}"
    file_path = tmp_path / "test.can"
    file_path.write_text(code)

    # Use --check
    result = runner.invoke(app, ["format", str(file_path), "--check"])
    assert result.exit_code == 1  # Should fail in check mode if modified
    assert "WOULD BE MODIFIED" in result.stdout

    # File should NOT be modified
    assert file_path.read_text() == code


def test_cli_format_json(tmp_path):
    code = "variables{int x=1;}"
    file_path = tmp_path / "test.can"
    file_path.write_text(code)

    result = runner.invoke(app, ["format", str(file_path), "--json"])
    assert result.exit_code == 0

    import json

    data = json.loads(result.stdout)
    assert data["total_files"] == 1
    assert data["modified_files"] == 1
    assert data["results"][0]["modified"] is True


def test_cli_format_config(tmp_path):
    code = "variables{int x=1;}"
    file_path = tmp_path / "test.can"
    file_path.write_text(code)

    config_content = """
[tool.capl-format]
indent-size = 4
"""
    config_path = tmp_path / ".capl-format.toml"
    config_path.write_text(config_content)

    result = runner.invoke(app, ["format", str(file_path), "--config-file", str(config_path)])
    assert result.exit_code == 0

    formatted_code = file_path.read_text()
    assert "    int x = 1;" in formatted_code  # 4 spaces indent
