import pytest
from capl_formatter.engine import FormatterEngine
from capl_formatter.models import FormatterConfig
from capl_formatter.rules.indentation import IndentationRule
from capl_formatter.rules.whitespace import WhitespaceCleanupRule

def test_whitespace_cleanup_trailing():
    source = "int x = 1;   \n"
    expected = "int x = 1;\n"
    
    config = FormatterConfig()
    engine = FormatterEngine(config)
    engine.add_rule(WhitespaceCleanupRule(config))
    
    result = engine.format_string(source)
    assert result.source == expected

def test_whitespace_cleanup_eof_newline():
    source = "int x = 1;"
    expected = "int x = 1;\n"
    
    config = FormatterConfig()
    engine = FormatterEngine(config)
    engine.add_rule(WhitespaceCleanupRule(config))
    
    result = engine.format_string(source)
    assert result.source == expected

def test_whitespace_cleanup_collapse_blank_lines():
    source = "int x = 1;\n\n\n\nint y = 2;"
    # Expect max 2 blank lines (lines 2 and 3 are empty) and EOF newline
    expected = "int x = 1;\n\n\nint y = 2;\n"
    
    config = FormatterConfig()
    engine = FormatterEngine(config)
    engine.add_rule(WhitespaceCleanupRule(config))
    
    result = engine.format_string(source)
    assert result.source == expected

def test_indentation_basic():
    source = "variables {\nint x;\n}"
    expected = "variables {\n  int x;\n}"
    
    config = FormatterConfig(indent_size=2)
    engine = FormatterEngine(config)
    engine.add_rule(IndentationRule(config))
    
    result = engine.format_string(source)
    assert result.source == expected

def test_indentation_nested():
    source = "void func() {\nif (cond) {\nreturn;\n}\n}"
    expected = "void func() {\n  if (cond) {\n    return;\n  }\n}"
    
    config = FormatterConfig(indent_size=2)
    engine = FormatterEngine(config)
    engine.add_rule(IndentationRule(config))
    
    result = engine.format_string(source)
    assert result.source == expected
