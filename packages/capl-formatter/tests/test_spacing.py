import pytest
from capl_formatter.engine import FormatterEngine
from capl_formatter.models import FormatterConfig
from capl_formatter.rules.spacing import SpacingRule, BraceStyleRule

def test_brace_style_knr():
    source = "if (x)\n{\n  return;\n}"
    expected = "if (x) {\n  return;\n}"
    
    config = FormatterConfig()
    engine = FormatterEngine(config)
    engine.add_rule(BraceStyleRule(config))
    
    result = engine.format_string(source)
    assert result.source == expected

def test_brace_style_already_knr():
    source = "if (x) {\n  return;\n}"
    
    config = FormatterConfig()
    engine = FormatterEngine(config)
    engine.add_rule(BraceStyleRule(config))
    
    result = engine.format_string(source)
    assert result.source == source

def test_spacing_comma():
    source = "func(a,b,c);"
    expected = "func(a, b, c);"
    
    config = FormatterConfig()
    engine = FormatterEngine(config)
    engine.add_rule(SpacingRule(config))
    
    result = engine.format_string(source)
    assert result.source == expected

def test_spacing_before_brace():
    source = "if (x){"
    expected = "if (x) {"
    
    config = FormatterConfig()
    engine = FormatterEngine(config)
    engine.add_rule(SpacingRule(config))
    
    result = engine.format_string(source)
    assert result.source == expected

