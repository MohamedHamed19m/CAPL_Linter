import pytest
from capl_formatter.engine import FormatterEngine
from capl_formatter.models import FormatterConfig
from capl_formatter.rules.pragmas import PragmaHandlingRule

def test_pragma_preservation():
    source = '#pragma library "capldll.dll"'
    # Should maintain exact format (ignoring whitespace cleanup for this specific rule test)
    expected = '#pragma library "capldll.dll"'
    
    config = FormatterConfig()
    engine = FormatterEngine(config)
    engine.add_rule(PragmaHandlingRule(config))
    
    result = engine.format_string(source)
    assert result.source.strip() == expected.strip()

def test_pragma_positioning():
    # Pragmas should move to top (after includes, before variables)
    source = """
variables { int x; }
#pragma library "lib.dll"
void f() {}
"""
    expected = """
#pragma library "lib.dll"
variables { int x; }
void f() {}
"""
    # Note: Whitespace/newlines handled by other rules. PragmaRule just moves lines.
    # We expect #pragma to move before variables.
    
    config = FormatterConfig()
    engine = FormatterEngine(config)
    engine.add_rule(PragmaHandlingRule(config))
    
    result = engine.format_string(source.strip())
    # Normalize result newlines for check
    assert "#pragma library" in result.source
    assert result.source.startswith('#pragma library "lib.dll"')

def test_pragma_multiple():
    source = """
#pragma library "lib1.dll"
variables {}
#pragma library "lib2.dll"
"""
    expected_start = """#pragma library "lib1.dll"
#pragma library "lib2.dll"
variables {{}}"""
    
    config = FormatterConfig()
    engine = FormatterEngine(config)
    engine.add_rule(PragmaHandlingRule(config))
    
    result = engine.format_string(source.strip())
    assert result.source.startswith('#pragma library "lib1.dll"\n#pragma library "lib2.dll"')
