from pathlib import Path
import pytest
from capl_symbol_db.database import SymbolDatabase
from capl_symbol_db.dependency import DependencyAnalyzer
from capl_linter.rules.semantic_rules import CircularIncludeRule


def test_circular_dependency_detection(tmp_path):
    # Setup files in tmp_path
    file_a = tmp_path / "CircularA.can"
    file_b = tmp_path / "CircularB.can"

    file_a.write_text('#include "CircularB.can"\nvariables { int g_a; }', encoding="utf-8")
    file_b.write_text('#include "CircularA.can"\nvariables { int g_b; }', encoding="utf-8")

    # Initialize DB and Dependency Analyzer
    db_path = tmp_path / "test_circular.db"
    db = SymbolDatabase(str(db_path))
    dep_analyzer = DependencyAnalyzer(db)

    # Analyze dependencies for both files
    dep_analyzer.analyze_file(file_a)
    dep_analyzer.analyze_file(file_b)

    # Run the Rule
    rule = CircularIncludeRule()
    issues = rule.check(file_a, db)

    # Verify results
    assert len(issues) > 0
    assert issues[0].rule_id == "W001"
    assert "Circular include detected" in issues[0].message
    assert "Consider refactoring" in issues[0].message
    assert "CircularA.can" in issues[0].message
    assert "CircularB.can" in issues[0].message


if __name__ == "__main__":
    pytest.main([__file__])
