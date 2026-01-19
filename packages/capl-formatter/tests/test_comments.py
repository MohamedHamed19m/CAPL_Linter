import pytest
from capl_formatter.engine import FormatterEngine
from capl_formatter.models import FormatterConfig
from capl_formatter.rules.comments import CommentReflowRule

def test_comment_reflow_line():
    # 100 chars limit.
    # 1234567890...
    prefix = "// " + "A" * 90 
    # Total length 93. Fits.
    # Add 20 chars -> 113. Should wrap.
    source = prefix + " " + "B" * 20
    
    config = FormatterConfig(line_length=100)
    engine = FormatterEngine(config)
    engine.add_rule(CommentReflowRule(config))
    
    result = engine.format_string(source)
    lines = result.source.splitlines()
    assert len(lines) == 2
    assert lines[0].startswith("// AAA")
    assert lines[1].strip().startswith("// BBB")
    assert len(lines[0]) <= 100

def test_comment_reflow_block():
    source = "/* " + "A" * 90 + " " + "B" * 20 + " */"
    
    config = FormatterConfig(line_length=100)
    engine = FormatterEngine(config)
    engine.add_rule(CommentReflowRule(config))
    
    result = engine.format_string(source)
    lines = result.source.splitlines()
    assert len(lines) >= 3
    assert lines[0].strip() == "/*"
    assert "AAAA" in lines[1]
    assert "BBBB" in lines[2]
    # Check for * alignment if implemented
    if len(lines) > 1:
        assert lines[1].strip().startswith("*")

def test_comment_preservation_ascii_art():
    # Block starting with /*** or /*=== should be preserved
    source = """/**************************************************
 * HEADER
 **************************************************/"""
    expected = source
    
    config = FormatterConfig(line_length=100)
    engine = FormatterEngine(config)
    engine.add_rule(CommentReflowRule(config))
    
    result = engine.format_string(source)
    assert result.source == expected