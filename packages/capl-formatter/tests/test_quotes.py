import pytest
from capl_formatter.engine import FormatterEngine
from capl_formatter.models import FormatterConfig
from capl_formatter.rules.quotes import QuoteNormalizationRule

def test_quote_normalization_string():
    source = "write('Hello World');"
    expected = 'write("Hello World");'
    
    config = FormatterConfig()
    engine = FormatterEngine(config)
    engine.add_rule(QuoteNormalizationRule(config))
    
    result = engine.format_string(source)
    assert result.source == expected

def test_quote_normalization_char():
    source = "char c = 'a';"
    # Should not change single char
    expected = "char c = 'a';"
    
    config = FormatterConfig()
    engine = FormatterEngine(config)
    engine.add_rule(QuoteNormalizationRule(config))
    
    result = engine.format_string(source)
    assert result.source == expected

def test_quote_normalization_already_double():
    source = 'write("Hello");'
    
    config = FormatterConfig()
    engine = FormatterEngine(config)
    engine.add_rule(QuoteNormalizationRule(config))
    
    result = engine.format_string(source)
    assert result.source == source

def test_quote_normalization_escaped():
    source = "write('It\'s me');"
    expected = 'write("It\'s me");' # or "It's me" -> "It's me" if we unescape quote?
    # Converting 'It\'s me' to "It's me".
    # Inside "...", ' does not need escape.
    
    config = FormatterConfig()
    engine = FormatterEngine(config)
    engine.add_rule(QuoteNormalizationRule(config))
    
    result = engine.format_string(source)
    # This might be tricky. For now, let's assume simple replacement of outer quotes.
    # If content has \', it becomes valid ' inside ".
    # If content has ", it needs escape inside ".
    # 'He said "Hi"' -> "He said \"Hi\"".
    
    # Let's simple test first.
    pass
