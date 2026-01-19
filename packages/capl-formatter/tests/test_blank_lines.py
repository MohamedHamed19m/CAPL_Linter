import pytest
from capl_formatter.engine import FormatterEngine
from capl_formatter.models import FormatterConfig
from capl_formatter.rules.blank_lines import BlankLineRule

def test_blank_lines_variables():
    source = "includes {}\nvariables {"
    # Expect 2 blank lines between includes and variables?
    # Spec: "2 blank lines before major blocks (variables, includes)"
    # If includes is first, no blank lines before it (start of file).
    # If variables follows includes, 2 blank lines.
    expected = "includes {}\n\n\nvariables {"
    
    config = FormatterConfig()
    engine = FormatterEngine(config)
    engine.add_rule(BlankLineRule(config))
    
    result = engine.format_string(source)
    assert result.source == expected

def test_blank_lines_function():
    source = "variables {}\nvoid func() {}"
    # Expect 1 blank line before function
    expected = "variables {}\n\nvoid func() {}"
    
    config = FormatterConfig()
    engine = FormatterEngine(config)
    engine.add_rule(BlankLineRule(config))
    
    result = engine.format_string(source)
    assert result.source == expected

def test_blank_lines_handler():
    source = "void f() {}\non start {}"
    # Expect 1 blank line before handler
    expected = "void f() {}\n\non start {}"
    
    config = FormatterConfig()
    engine = FormatterEngine(config)
    engine.add_rule(BlankLineRule(config))
    
    result = engine.format_string(source)
    assert result.source == expected

def test_blank_lines_already_correct():
    source = "variables {}\n\nvoid func() {}"
    
    config = FormatterConfig()
    engine = FormatterEngine(config)
    engine.add_rule(BlankLineRule(config))
    
    result = engine.format_string(source)
    assert result.source == source
