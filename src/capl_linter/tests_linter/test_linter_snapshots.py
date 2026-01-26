from capl_linter.engine import LinterEngine
from capl_symbol_db.database import SymbolDatabase
from capl_symbol_db.extractor import SymbolExtractor


def format_issues_for_snapshot(issues):
    """Convert a list of issues into a stable string for snapshot comparison."""
    # Sort issues by line number and then rule_id to ensure stability
    sorted_issues = sorted(issues, key=lambda x: (x.line, x.rule_id))
    lines = []
    for issue in sorted_issues:
        lines.append(
            f"Line {issue.line}: [{issue.rule_id}] {issue.severity.name} - {issue.message}"
        )
    return "\n".join(lines)


class TestLinterSnapshots:
    """Snapshot tests for linter issue reporting."""

    def _run_lint(self, tmp_path, code):
        db_path = tmp_path / "test.db"
        file_path = tmp_path / "test.can"
        file_path.write_text(code)

        # 1. Analyze (Extractor + Database)
        extractor = SymbolExtractor()
        syms = extractor.extract_all(file_path)

        db = SymbolDatabase(str(db_path))
        file_id = db.store_file(file_path, code.encode())
        db.store_symbols(file_id, syms)

        # 2. Lint
        engine = LinterEngine(str(db_path))
        return engine.analyze_file(file_path)

    def test_syntax_violations(self, tmp_path, snapshot):
        code = """
extern int x;
on start {
  int *p;
  x = *p; // Pointer syntax
}
"""
        issues = self._run_lint(tmp_path, code)
        snapshot.assert_match(format_issues_for_snapshot(issues), "syntax_violations.txt")

    def test_variable_placement(self, tmp_path, snapshot):
        code = """
int global_var; // Outside variables block
variables {
  int ok_var;
}
void func() {
  int local_ok;
}
"""
        issues = self._run_lint(tmp_path, code)
        snapshot.assert_match(format_issues_for_snapshot(issues), "variable_placement.txt")
