import pytest
from capl_formatter.engine import FormatterEngine
from capl_formatter.models import FormatterConfig
from capl_formatter.rules.block_expansion import BlockExpansionRule

def test_block_expansion_variables():
    source = "variables {int x;}"
    expected = "variables {\nint x;\n}"
    
    config = FormatterConfig()
    engine = FormatterEngine(config)
    engine.add_rule(BlockExpansionRule(config))
    
    result = engine.format_string(source)
    assert result.source == expected

def test_block_expansion_function():
    source = "void func() { return; }"
    # Expect expansion. Note: space before } matches [^\n] so it is preserved before \n
    expected = "void func() {\n return; \n}"
    
    config = FormatterConfig()
    engine = FormatterEngine(config)
    engine.add_rule(BlockExpansionRule(config))
    
    result = engine.format_string(source)
    assert result.source == expected

def test_block_expansion_initializer():
    source = "arr = {1, 2};"
    # Should expand (consistent style)
    expected = "arr = {\n1, 2\n};"
    
    config = FormatterConfig()
    engine = FormatterEngine(config)
    engine.add_rule(BlockExpansionRule(config))
    
    result = engine.format_string(source)
    assert result.source == expected

def test_block_expansion_else():
    source = "if(x){} else {}"
    # } else should stay on same line (or whatever rule 3 allows).
    # But {} -> {\n}
    # Expected: "if(x) {\n} else {\n}"
    
    # Rule 1: ) { -> ) {\n
    # Rule 2: } -> \n} (if not preceded by \n)
    # Rule 3: } else -> } else (no newline inserted)
    
    # Trace:
    # "if(x) {\n} else {\n}" (after Rule 1)
    # Rule 2:
    # } -> \n} (if not preceded by \n).
    # First }: Preceded by \n? Yes "{\n}".
    # Second }: Preceded by \n? Yes "{\n}".
    
    # Rule 3: } else. Ignored.
    
    expected = "if(x) {\n} else {\n}"
    
    config = FormatterConfig()
    engine = FormatterEngine(config)
    engine.add_rule(BlockExpansionRule(config))
    
    result = engine.format_string(source)
    assert result.source == expected
