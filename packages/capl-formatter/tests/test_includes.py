import pytest
from capl_formatter.engine import FormatterEngine
from capl_formatter.models import FormatterConfig
from capl_formatter.rules.structure import IncludeSortingRule

def test_include_sorting():
    source = """
#include "node.can"
#include "lib.cin"
#include "utils.cin"
#include "common.can"
"""
    # Expected: cin first (sorted), then can (sorted).
    expected = """
#include "lib.cin"
#include "utils.cin"

#include "common.can"
#include "node.can"
"""
    # Note: Expect blank line between groups.
    # Also blank line at start/end depending on insertion?
    # Usually includes are at top. If source has leading newlines, result might have them.
    # IncludeSortingRule usually replaces the *block* of includes.
    
    config = FormatterConfig()
    engine = FormatterEngine(config)
    engine.add_rule(IncludeSortingRule(config))
    
    result = engine.format_string(source.strip())
    # Strip result to ignore outer whitespace for comparison
    assert result.source.strip() == expected.strip()

def test_include_deduplication():
    source = """
#include "lib.cin"
#include "lib.cin"
"""
    expected = '#include "lib.cin"'
    
    config = FormatterConfig()
    engine = FormatterEngine(config)
    engine.add_rule(IncludeSortingRule(config))
    
    result = engine.format_string(source.strip())
    assert result.source.strip() == expected.strip()

def test_include_comment_preservation():
    source = """
#include "b.cin" // comment b
#include "a.cin" // comment a
"""
    expected = """
#include "a.cin" // comment a
#include "b.cin" // comment b
"""
    
    config = FormatterConfig()
    engine = FormatterEngine(config)
    engine.add_rule(IncludeSortingRule(config))
    
    result = engine.format_string(source.strip())
    assert result.source.strip() == expected.strip()
