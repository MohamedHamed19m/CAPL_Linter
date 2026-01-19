import pytest
from capl_formatter.engine import FormatterEngine
from capl_formatter.models import FormatterConfig
from capl_formatter.rules.structure import VariableOrderingRule

def test_variable_ordering_types():
    source = """variables {
  int x;
  message 0x100 msg1;
  msTimer t1;
  char c;
}"""
    # Expected: message, msTimer, primitives (char, int sorted alphabetically?)
    # Primitives: char c, int x.
    expected = """variables {
  message 0x100 msg1;

  msTimer t1;

  char c;
  int x;
}"""
    # Note: Blank line between groups.
    
    config = FormatterConfig()
    engine = FormatterEngine(config)
    engine.add_rule(VariableOrderingRule(config))
    
    result = engine.format_string(source)
    # Check content (ignoring outer whitespace/indentation nuances handled by other rules)
    # But VariableOrderingRule constructs the block content.
    # It should probably produce indented lines? Or let IndentationRule do it?
    # Ideally, VariableOrderingRule just reorders lines.
    # If input is indented, output should be indented.
    # Or IndentationRule fixes it later.
    # Phase 4 (Structure) runs after Phase 2 (Indent)?
    # No, typically Structure runs BEFORE Indent?
    # If Structure rewrites the block, it might mess up indentation.
    # If I verify structure, I ignore indent in comparison?
    
    # Let's assume VariableOrderingRule produces minimal indentation or relies on IndentationRule.
    # But IndentationRule ran in Phase 2. Structure is Phase 4.
    # If I rewrite `variables { ... }`, I should respect indent?
    # Or I should rerun IndentationRule?
    # Formatters usually run in pipeline.
    # The Engine applies rules in order added.
    
    # If VariableOrderingRule output is unindented, and IndentationRule already ran, result is unindented.
    # So VariableOrderingRule MUST indent correctly (2 spaces).
    
    assert "message 0x100 msg1;" in result.source
    assert result.source.index("message") < result.source.index("msTimer")
    assert result.source.index("msTimer") < result.source.index("char")

def test_variable_sorting_alphabetical():
    source = """variables {
  int b;
  int a;
}"""
    expected = """variables {
  int a;
  int b;
}"""
    
    config = FormatterConfig()
    engine = FormatterEngine(config)
    engine.add_rule(VariableOrderingRule(config))
    
    result = engine.format_string(source)
    assert "int a;" in result.source
    assert result.source.index("int a;") < result.source.index("int b;")

def test_variable_comment_preservation():
    source = """variables {
  int b; // comment b
  int a; // comment a
}"""
    # comment should move with variable
    
    config = FormatterConfig()
    engine = FormatterEngine(config)
    engine.add_rule(VariableOrderingRule(config))
    
    result = engine.format_string(source)
    assert "int a; // comment a" in result.source
    assert result.source.index("int a;") < result.source.index("int b;")
