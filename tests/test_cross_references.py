"""
Comprehensive test and query interface for CAPL cross-reference system
"""

import sqlite3
from pathlib import Path


def test_cross_references(file_path: str = "MyNode.can"):
    """Test cross-reference extraction"""
    from capl_analyzer.cross_reference import CAPLCrossReferenceBuilder

    print("=" * 70)
    print("BUILDING CROSS-REFERENCES")
    print("=" * 70)

    xref = CAPLCrossReferenceBuilder()

    print(f"\n📝 Analyzing {file_path}...")
    ref_count = xref.analyze_file_references(file_path)
    print(f"✓ Found {ref_count} symbol references")

    return xref


def query_references(xref, symbol_name: str):
    """Query all references to a symbol"""
    print(f"\n{'=' * 70}")
    print(f"REFERENCES TO: {symbol_name}")
    print("=" * 70)

    refs = xref.find_all_references(symbol_name)

    if not refs:
        print(f"  No references found for '{symbol_name}'")
        return

    print(f"\nFound {len(refs)} reference(s):\n")

    # Group by file
    by_file = {}
    for ref in refs:
        file_name = Path(ref.file_path).name
        if file_name not in by_file:
            by_file[file_name] = []
        by_file[file_name].append(ref)

    for file_name, file_refs in sorted(by_file.items()):
        print(f"📁 {file_name}")
        for ref in sorted(file_refs, key=lambda r: r.line_number):
            ref_type_icon = {"call": "📞", "usage": "🔍", "assignment": "✏️", "output": "📤"}.get(
                ref.reference_type, "•"
            )

            print(
                f"  {ref_type_icon} Line {ref.line_number:4d} [{ref.reference_type:10s}] {ref.context[:50]}"
            )


def show_call_graph(xref, function_name: str):
    """Display call graph for a function"""
    print(f"\n{'=' * 70}")
    print(f"CALL GRAPH FOR: {function_name}")
    print("=" * 70)

    graph = xref.get_call_graph(function_name)

    # Who calls this function?
    if graph["callers"]:
        print(f"\n📥 Called by ({len(graph['callers'])} caller(s)):")
        for caller, file, line in graph["callers"]:
            print(f"  ← {caller:30s} ({file}:{line})")
    else:
        print("\n📥 Not called by any tracked function (might be entry point)")

    # What does this function call?
    if graph["callees"]:
        print(f"\n📤 Calls ({len(graph['callees'])} function(s)):")
        for callee, file, line in graph["callees"]:
            print(f"  → {callee:30s} ({file}:{line})")
    else:
        print("\n📤 Does not call any tracked functions")


def show_message_analysis(xref, message_name: str):
    """Show complete analysis of a message"""
    print(f"\n{'=' * 70}")
    print(f"MESSAGE ANALYSIS: {message_name}")
    print("=" * 70)

    # Find handlers
    handlers = xref.get_message_handlers(message_name)
    if handlers:
        print(f"\n📨 Event Handlers ({len(handlers)}):")
        for file, handler, line in handlers:
            print(f"  {file}:{line} → {handler}")
    else:
        print(f"\n📨 No event handlers found for {message_name}")

    # Find outputs
    outputs = xref.get_message_outputs(message_name)
    if outputs:
        print(f"\n📤 Output Calls ({len(outputs)}):")
        for file, func, line in outputs:
            print(f"  {file}:{line} in {func}")
    else:
        print(f"\n📤 No output() calls found for {message_name}")


def inspect_reference_database():
    """Show what's in the cross-reference tables"""
    print("\n" + "=" * 70)
    print("CROSS-REFERENCE DATABASE INSPECTION")
    print("=" * 70)

    with sqlite3.connect("aic.db") as conn:
        # Symbol references count
        cursor = conn.execute("""
            SELECT reference_type, COUNT(*) as count
            FROM symbol_references
            GROUP BY reference_type
            ORDER BY count DESC
        """)

        print("\n📊 References by Type:")
        for ref_type, count in cursor.fetchall():
            print(f"  {ref_type:15s}: {count:4d}")

        # Most referenced symbols
        cursor = conn.execute("""
            SELECT symbol_name, COUNT(*) as count
            FROM symbol_references
            GROUP BY symbol_name
            ORDER BY count DESC
            LIMIT 10
        """)

        print("\n🔥 Top 10 Most Referenced Symbols:")
        for i, (symbol, count) in enumerate(cursor.fetchall(), 1):
            print(f"  {i:2d}. {symbol:25s}: {count:3d} references")

        # Function call statistics
        cursor = conn.execute("""
            SELECT COUNT(DISTINCT caller_symbol_id) as callers,
                   COUNT(DISTINCT callee_name) as callees,
                   COUNT(*) as total_calls
            FROM function_calls
        """)

        row = cursor.fetchone()
        if row:
            print("\n📞 Call Graph Statistics:")
            print(f"  Functions that call others: {row[0]}")
            print(f"  Unique functions called:    {row[1]}")
            print(f"  Total call sites:           {row[2]}")


def create_comprehensive_test():
    """Create a test file with various cross-reference scenarios"""
    content = """
/*@@var:*/
variables {
  message EngineState msgEngine;
  message BrakeStatus msgBrake;
  msTimer tCycle;
  msTimer tWarning;
  int gCounter = 0;
}
/*@@end*/

int gErrorCount = 0;

on start {
  setTimer(tCycle, 100);
  gCounter = 0;
  InitSystem();
}

on message EngineState {
  if (this.RPM > 3000) {
    LogWarning("High RPM");
    setTimer(tWarning, 500);
    gCounter++;
  }
  msgEngine.RPM = this.RPM;
}

on message BrakeStatus {
  if (this.Status == 1) {
    LogInfo("Brakes applied");
  }
}

on timer tCycle {
  UpdateEngine();
  output(msgEngine);
  setTimer(this, 100);
}

on timer tWarning {
  LogWarning("Warning timeout");
}

void InitSystem() {
  gCounter = 0;
  gErrorCount = 0;
  LogInfo("System initialized");
}

void UpdateEngine() {
  msgEngine.RPM = CalculateRPM();
  gCounter++;
}

int CalculateRPM() {
  return 2500 + gCounter * 10;
}

void LogInfo(char msg[]) {
  write("[INFO] %s", msg);
}

void LogWarning(char msg[]) {
  write("[WARN] %s", msg);
  gErrorCount++;
}

void LogError(char msg[]) {
  write("[ERROR] %s", msg);
  gErrorCount++;
  if (gErrorCount > 10) {
    write("Too many errors!");
  }
}
"""

    with open("XRefTest.can", "w") as f:
        f.write(content)

    print("✓ Created XRefTest.can for comprehensive testing")
    return "XRefTest.can"


def run_comprehensive_analysis():
    """Run a full analysis showing all features"""
    import sys

    # Create test file if needed
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
    else:
        print("Creating comprehensive test file...\n")
        file_path = create_comprehensive_test()

    # Build cross-references
    xref = test_cross_references(file_path)

    # Inspect database
    inspect_reference_database()

    # Example queries
    print("\n" + "=" * 70)
    print("EXAMPLE QUERIES")
    print("=" * 70)

    # Query 1: Variable references
    query_references(xref, "gCounter")

    # Query 2: Function calls
    query_references(xref, "LogWarning")

    # Query 3: Call graph
    show_call_graph(xref, "UpdateEngine")

    # Query 4: Message analysis
    show_message_analysis(xref, "msgEngine")

    # Generate visualization
    print("\n" + "=" * 70)
    print("GENERATING VISUALIZATIONS")
    print("=" * 70)
    xref.generate_call_graph_dot("call_graph.dot")

    print("\n" + "=" * 70)
    print("✅ ANALYSIS COMPLETE")
    print("=" * 70)
    print("\nYou can now query the database for:")
    print("  • Find all references: xref.find_all_references('symbolName')")
    print("  • Call graph: xref.get_call_graph('functionName')")
    print("  • Message handlers: xref.get_message_handlers('MessageName')")
    print("  • Message outputs: xref.get_message_outputs('msgName')")


def interactive_query():
    """Interactive query interface"""
    from capl_analyzer.cross_reference import CAPLCrossReferenceBuilder

    xref = CAPLCrossReferenceBuilder()

    print("\n" + "=" * 70)
    print("INTERACTIVE CROSS-REFERENCE QUERY")
    print("=" * 70)
    print("\nCommands:")
    print("  refs <symbol>     - Find all references to a symbol")
    print("  calls <function>  - Show call graph for a function")
    print("  msg <message>     - Analyze message usage")
    print("  stats             - Show database statistics")
    print("  quit              - Exit")
    print()

    while True:
        try:
            cmd = input("\nQuery> ").strip()

            if not cmd or cmd == "quit":
                break

            parts = cmd.split(maxsplit=1)
            if len(parts) < 1:
                continue

            command = parts[0].lower()
            arg = parts[1] if len(parts) > 1 else ""

            if command == "refs" and arg:
                query_references(xref, arg)
            elif command == "calls" and arg:
                show_call_graph(xref, arg)
            elif command == "msg" and arg:
                show_message_analysis(xref, arg)
            elif command == "stats":
                inspect_reference_database()
            else:
                print("Unknown command or missing argument")

        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")

    print("\nGoodbye!")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "interactive":
        interactive_query()
    else:
        run_comprehensive_analysis()
