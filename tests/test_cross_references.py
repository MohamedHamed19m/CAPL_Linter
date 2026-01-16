import pytest
from pathlib import Path
from capl_analyzer.cross_reference import CAPLCrossReferenceBuilder

def test_cross_references(tmp_path):
    """Test cross-reference extraction"""
    code = """
variables {
  message EngineState msgEngine;
}

on start {
  msgEngine.RPM = 100;
  output(msgEngine);
}
"""
    test_file = tmp_path / "test_xref.can"
    test_file.write_text(code)
    
    db_path = str(tmp_path / "test.db")
    xref = CAPLCrossReferenceBuilder(db_path=db_path)
    
    ref_count = xref.analyze_file_references(str(test_file))
    assert ref_count > 0
    
    # Find assignment
    refs = xref.find_all_references("msgEngine")
    types = [r.reference_type for r in refs]
    assert "assignment" in types
    assert "output" in types