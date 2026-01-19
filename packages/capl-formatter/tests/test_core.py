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

def test_engine_parse_error_handling():
    class ErrorRule(BaseFormattingRule):
        def apply(self, context):
            raise ValueError("Parse error simulation")
            
    config = FormatterConfig()
    engine = FormatterEngine(config=config)
    engine.add_rule(ErrorRule())
    
    source = "some code"
    result = engine.format_string(source)
    
    assert result.modified is False
    assert len(result.errors) > 0
    assert "Parse error simulation" in result.errors[0]

def test_engine_format_files(tmp_path):
    f1 = tmp_path / "test1.can"
    f1.write_text("old", encoding="utf-8")
    
    config = FormatterConfig()
    engine = FormatterEngine(config=config)
    engine.add_rule(MockRule())
    
    results = engine.format_files([str(f1)])
    
    assert results.total_files == 1
    assert results.modified_files == 1
    assert f1.read_text(encoding="utf-8") == "new"
