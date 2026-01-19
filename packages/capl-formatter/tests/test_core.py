import pytest
from capl_formatter.engine import FormatterEngine
from capl_formatter.models import FormatterConfig, FormatResult
from capl_formatter.rules.base import BaseFormattingRule

class MockRule(BaseFormattingRule):
    def apply(self, context):
        context.source = context.source.replace("old", "new")

def test_formatter_config_defaults():
    config = FormatterConfig()
    assert config.indent_size == 2
    assert config.line_length == 100

def test_engine_applies_rules():
    config = FormatterConfig()
    engine = FormatterEngine(config=config)
    engine.add_rule(MockRule())
    
    source = "This is old code"
    result = engine.format_string(source)
    
    assert isinstance(result, FormatResult)
    assert result.source == "This is new code"
    assert result.modified is True

def test_engine_no_change():
    config = FormatterConfig()
    engine = FormatterEngine(config=config)
    engine.add_rule(MockRule())
    
    source = "This is clean code"
    result = engine.format_string(source)
    
    assert result.source == source
    assert result.modified is False

def test_token_rewrite_strategy():
    from capl_formatter.strategies import TokenRewriteStrategy
    strategy = TokenRewriteStrategy()
    source = "test"
    assert strategy.rewrite(source) == source
