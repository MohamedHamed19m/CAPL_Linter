import pytest
from capl_formatter.engine import FormatterEngine
from capl_formatter.models import FormatterConfig
from capl_formatter.rules.whitespace import WhitespaceCleanupRule

def test_whitespace_cleanup_simple():
    config = FormatterConfig()
    engine = FormatterEngine(config)
    engine.add_rule(WhitespaceCleanupRule(config))
    
    source = "int x = 1;   \nint y = 2;"
    expected = "int x = 1;\nint y = 2;\n"
    
    result = engine.format_string(source)
    assert result.source == expected
    assert result.modified is True

def test_whitespace_cleanup_idempotency():
    config = FormatterConfig()
    engine = FormatterEngine(config)
    engine.add_rule(WhitespaceCleanupRule(config))
    
    source = "int x = 1;\n"
    
    result1 = engine.format_string(source)
    assert result1.modified is False
    assert result1.source == source
    
    result2 = engine.format_string(result1.source)
    assert result2.modified is False
    assert result2.source == source
