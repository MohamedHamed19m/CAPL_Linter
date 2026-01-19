import pytest
from capl_formatter.engine import FormatterEngine
from capl_formatter.models import FormatterConfig
from capl_formatter.rules.wrapping import DefinitionWrappingRule, CallWrappingRule, InitializerWrappingRule

def test_definition_wrapping_chop_down():
    # Long signature
    source = "void LongFunction(int param1, char param2[], message 0x100 msg, float param4) {}"
    # Assume line length 50 to force wrap
    
    config = FormatterConfig(line_length=50, indent_size=2)
    engine = FormatterEngine(config)
    engine.add_rule(DefinitionWrappingRule(config))
    
    result = engine.format_string(source)
    # Ignore surrounding whitespace/newlines, focus on signature structure
    assert len(result.source.splitlines()) > 1
    assert "void LongFunction(" in result.source
    assert "  int param1," in result.source

def test_call_wrapping_fit_as_many():
    # Long call
    source = "CallFunction(arg1, arg2, arg3, arg4, arg5);"
    # Length 43. Limit 20.
    
    config = FormatterConfig(line_length=20, indent_size=2)
    engine = FormatterEngine(config)
    engine.add_rule(CallWrappingRule(config))
    
    result = engine.format_string(source)
    assert len(result.source.splitlines()) > 1
    assert "arg1," in result.source

def test_initializer_wrapping_long():
    source = "arr = {1, 2, 3, 4, 5, 6, 7, 8, 9, 10};"
    # Assume limit forces wrap
    
    config = FormatterConfig(line_length=20, indent_size=2)
    engine = FormatterEngine(config)
    engine.add_rule(InitializerWrappingRule(config))
    
    result = engine.format_string(source)
    assert "{\n" in result.source
    assert ",\n" in result.source

def test_definition_no_wrap():
    source = "void f() {}"
    config = FormatterConfig(line_length=50)
    engine = FormatterEngine(config)
    engine.add_rule(DefinitionWrappingRule(config))
    result = engine.format_string(source)
    assert result.source == source

def test_call_no_wrap():
    source = "f();"
    config = FormatterConfig(line_length=50)
    engine = FormatterEngine(config)
    engine.add_rule(CallWrappingRule(config))
    result = engine.format_string(source)
    assert result.source == source