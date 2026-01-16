"""
Test script for CAPL Symbol Extractor
"""

from pathlib import Path
import sqlite3


def test_symbol_extraction(file_path: str = "EnhancedNode.can"):
    """Test symbol extraction on a CAPL file"""
    from capl_symbol_extractor import CAPLSymbolExtractor, update_database_schema
      
    print("=" * 70)
    print(f"TESTING SYMBOL EXTRACTION: {file_path}")
    print("=" * 70)
    
    # Update schema to include new columns
    update_database_schema()
    
    # Create extractor
    extractor = CAPLSymbolExtractor()
    
    # Extract and store symbols
    print(f"\n📝 Analyzing {file_path}...")
    num_symbols = extractor.store_symbols(file_path)
    print(f"✓ Found and stored {num_symbols} symbols")
    
    # Display results
    print("\n" + "=" * 70)
    print("SYMBOLS EXTRACTED")
    print("=" * 70)
    
    symbols = extractor.list_symbols_in_file(str(Path(file_path).resolve()))
    
    # Group by type
    by_type = {}
    for name, sym_type, line, sig in symbols:
        if sym_type not in by_type:
            by_type[sym_type] = []
        by_type[sym_type].append((name, line, sig))
    
    # Display grouped
    for sym_type, items in sorted(by_type.items()):
        print(f"\n📌 {sym_type.upper().replace('_', ' ')}:")
        print("-" * 70)
        for name, line, sig in items:
            print(f"  Line {line:4d} | {name}")
            if sig and len(sig) < 60:
                print(f"           → {sig}")
    
    return extractor


def test_symbol_queries(extractor):
    """Test various symbol query operations"""
    print("\n" + "=" * 70)
    print("SYMBOL QUERIES")
    print("=" * 70)
    
    # Test 1: Find all event handlers
    print("\n1️⃣  All Event Handlers in Project:")
    handlers = extractor.get_event_handlers()
    for file_path, name, line in handlers:
        print(f"  {Path(file_path).name}:{line} → {name}")
    
    # Test 2: Find specific symbol
    print("\n2️⃣  Find symbol 'msgEngine':")
    results = extractor.find_symbol('msgEngine')
    for file_path, sym_type, line, sig in results:
        print(f"  {Path(file_path).name}:{line} | {sym_type} | {sig}")
    
    # Test 3: Find all functions
    print("\n3️⃣  Find all functions:")
    results = extractor.find_symbol('CheckSystemStatus', 'function')
    if results:
        for file_path, sym_type, line, sig in results:
            print(f"  {Path(file_path).name}:{line} | {sig}")
    else:
        print("  (No functions found with that name)")


def inspect_database_symbols():
    """Show what's in the symbols table"""
    print("\n" + "=" * 70)
    print("DATABASE INSPECTION - SYMBOLS TABLE")
    print("=" * 70)
    
    with sqlite3.connect("aic.db") as conn:
        cursor = conn.execute("""
            SELECT 
                f.file_path,
                s.symbol_name,
                s.symbol_type,
                s.line_number,
                s.scope,
                s.signature
            FROM symbols s
            JOIN files f ON s.file_id = f.file_id
            ORDER BY f.file_path, s.line_number
        """)
        
        current_file = None
        for file_path, name, sym_type, line, scope, sig in cursor.fetchall():
            file_name = Path(file_path).name
            if file_name != current_file:
                print(f"\n📁 {file_name}")
                print("-" * 70)
                current_file = file_name
            
            scope_str = f"[{scope}]" if scope else ""
            print(f"  {line:4d} | {sym_type:15s} {scope_str:15s} | {name}")


def generate_symbol_report():
    """Generate a summary report of all symbols"""
    print("\n" + "=" * 70)
    print("SYMBOL STATISTICS")
    print("=" * 70)
    
    with sqlite3.connect("aic.db") as conn:
        # Count by type
        cursor = conn.execute("""
            SELECT symbol_type, COUNT(*) as count
            FROM symbols
            GROUP BY symbol_type
            ORDER BY count DESC
        """)
        
        print("\nSymbols by Type:")
        for sym_type, count in cursor.fetchall():
            print(f"  {sym_type:20s}: {count:3d}")
        
        # Count by file
        cursor = conn.execute("""
            SELECT f.file_path, COUNT(*) as count
            FROM symbols s
            JOIN files f ON s.file_id = f.file_id
            GROUP BY f.file_path
            ORDER BY count DESC
        """)
        
        print("\nSymbols by File:")
        for file_path, count in cursor.fetchall():
            print(f"  {Path(file_path).name:30s}: {count:3d}")


def create_enhanced_test_file():
    """Create a more comprehensive test file"""
    content = """
/*@@var:*/
variables {
  message EngineState msgEngine;
  message BrakeStatus msgBrake;
  msTimer tCycle;
  msTimer tWarning;
  int gIsRunning = 0;
  DWORD counter;
}
/*@@end*/

// Global variables outside variables block
const int MAX_RPM = 5000;
int errorCount = 0;

on start {
  setTimer(tCycle, 100);
  write("System started");
}

on preStart {
  write("Initializing...");
  gIsRunning = 0;
}

on message EngineState {
  if (this.RPM > 3000) {
    write("Warning: High RPM detected!");
    setTimer(tWarning, 500);
  }
  msgEngine.RPM = this.RPM;
}

on message BrakeStatus {
  if (this.Status == 1) {
    write("Brakes applied");
  }
}

on signal Engine.RPM {
  write("RPM signal changed: %d", this);
}

on timer tCycle {
  msgEngine.RPM = 2500;
  output(msgEngine);
  setTimer(this, 100);
}

on timer tWarning {
  write("Warning timer expired");
}

on key 'a' {
  write("Key 'a' pressed");
}

on stopMeasurement {
  write("Measurement stopped");
  gIsRunning = 0;
}

void CheckSystemStatus(int systemID) {
  // Complex logic here...
  write("System %d is OK", systemID);
}

int CalculateAverage(int values[], int count) {
  int sum = 0;
  int i;
  for (i = 0; i < count; i++) {
    sum += values[i];
  }
  return sum / count;
}

void LogError(char msg[]) {
  errorCount++;
  write("[ERROR] %s", msg);
}
"""
    
    with open("EnhancedNode.can", 'w') as f:
        f.write(content)
    
    print("✓ Created EnhancedNode.can for comprehensive testing")
    return "EnhancedNode.can"


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        # Test with provided file
        file_path = sys.argv[1]
    else:
        # Create and test with enhanced file
        print("No file provided, creating test file...\n")
        file_path = create_enhanced_test_file()
    
    # Run tests
    extractor = test_symbol_extraction(file_path)
    test_symbol_queries(extractor)
    inspect_database_symbols()
    generate_symbol_report()
    
    print("\n" + "=" * 70)
    print("✅ TESTING COMPLETE")
    print("=" * 70)
    print("\nNext steps:")
    print("  • Integrate with dependency analyzer")
    print("  • Add cross-reference tracking (who calls what)")
    print("  • Build 'jump to definition' feature")
    print("  • Create LSP-style 'find all references'")