import pytest
from capl_formatter.engine import FormatterEngine
from capl_formatter.models import FormatterConfig
from capl_formatter.rules.indentation import IndentationRule

def test_indentation_basic():
    config = FormatterConfig(indent_size=2)
    engine = FormatterEngine(config)
    engine.add_rule(IndentationRule(config))
    
    # Braces on new lines for simple test (handled by other rules in reality)
    source = "void f()\n{\nint x;\n}"
    expected = "void f()\n{\n  int x;\n}\n" # engine adds EOF newline if Whitespace rule present? No, Indent doesn't.
    # Wait, IndentationRule doesn't add EOF newline. Result source depends on input.
    
    result = engine.format_string(source)
    assert "  int x;" in result.source

def test_indentation_idempotency():
    config = FormatterConfig(indent_size=2)
    engine = FormatterEngine(config)
    engine.add_rule(IndentationRule(config))
    
    source = "void f()\n{\n  int x;\n}"
    
    result1 = engine.format_string(source)
    assert result1.modified is False
    assert result1.source == source
