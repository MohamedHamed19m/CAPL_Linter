import pytest
from capl_formatter.engine import FormatterEngine
from capl_formatter.models import FormatterConfig

class TestFormattingSnapshots:
    """Snapshot tests catch ANY formatting change."""
    
    def test_struct_formatting(self, snapshot):
        source = "  struct Point{int x;int y;}"
        
        engine = FormatterEngine(FormatterConfig())
        engine.add_default_rules()
        result = engine.format_string(source)
        
        # First run: Creates snapshot file
        # Future runs: Compares against snapshot
        snapshot.assert_match(result.source, 'struct_point.can')
    
    def test_enum_formatting(self, snapshot):
        source = "enum Color{RED,GREEN,BLUE}"
        
        engine = FormatterEngine(FormatterConfig())
        engine.add_default_rules()
        result = engine.format_string(source)
        
        snapshot.assert_match(result.source, 'enum_color.can')
    
    def test_switch_formatting(self, snapshot):
        source = """
void test(){
  switch(x){
    case 1:doThing();break;
    default:other();
  }
}
"""
        
        engine = FormatterEngine(FormatterConfig())
        engine.add_default_rules()
        result = engine.format_string(source)
        
        snapshot.assert_match(result.source, 'switch_statement.can')

    def test_variables_formatting(self, snapshot):
        source = """
variables {
  int x;
  char y[10] = "test";
}
"""
        engine = FormatterEngine(FormatterConfig())
        engine.add_default_rules()
        result = engine.format_string(source)
        
        snapshot.assert_match(result.source, 'variables_block.can')
