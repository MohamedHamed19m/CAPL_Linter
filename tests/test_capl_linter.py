"""
Test the CAPL Linter with various code issues
"""

from pathlib import Path


def create_problematic_code():
    """Create a test file with various linting issues"""
    code = """
/*@@var:*/
variables {
  // STYLE ISSUE: Message variable doesn't follow naming convention (should be msgEngine)
  message EngineState engineMsg;
  
  // STYLE ISSUE: Timer doesn't follow naming convention (should be tCycle)
  msTimer cycleTimer;
  
  // WARNING: This timer is set but has no handler
  msTimer orphanTimer;
  
  // WARNING: This message is never used
  message BrakeStatus unusedMsg;
  
  // INFO: This message variable is OK but has no handler for BrakeStatus
  message ThrottleCmd msgThrottle;
  
  // STYLE ISSUE: Variable doesn't start with 'g'
  int counter;
  
  // OK: Properly named global
  int gErrorCount;
}
/*@@end*/

// ERROR: Variable declared outside variables {} block - CAPL SYNTAX ERROR!
int invalidGlobal = 0;

// ERROR: Another variable outside variables block
DWORD anotherBadVar = 100;

// ERROR: Duplicate handler (defined twice)
on start {
  setTimer(cycleTimer, 100);
  setTimer(orphanTimer, 200);
  InitSystem();
}

// ERROR: Duplicate handler
on start {
  write("Starting again...");
}

// OK: This message has a handler and uses engineMsg properly
on message EngineState {
  if (this.RPM > 3000) {
    LogWarning("High RPM");
  }
  engineMsg.RPM = this.RPM;
  output(engineMsg);  // Message is actually used
}

// INFO: Handler for message that's never output in this file
on message ThrottleCmd {
  write("Throttle: %d", this.Position);
}

// WARNING: Timer handler but timer is never reset
on timer cycleTimer {
  engineMsg.RPM = 2500;
  output(engineMsg);
  // Missing: setTimer(this, 100);
}

void InitSystem() {
  counter = 0;
  gErrorCount = 0;
  write("System initialized");
}

// INFO: This function is never called (might be unused)
void UnusedHelper() {
  write("This is never called");
}

void LogWarning(char msg[]) {
  write("[WARN] %s", msg);
  gErrorCount++;
}

// ERROR: Calls undefined function
void BuggyFunction() {
  DoSomethingUndefined();  // This function doesn't exist
  LogWarning("Called undefined");
}
"""
    
    with open("ProblematicCode.can", 'w') as f:
        f.write(code)
    
    print("✓ Created ProblematicCode.can with various issues")
    return "ProblematicCode.can"


def run_full_analysis():
    """Run complete analysis pipeline"""
    from capl_symbol_extractor import CAPLSymbolExtractor
    from capl_cross_reference import CAPLCrossReferenceBuilder
    from capl_linter import CAPLLinter
    
    print("=" * 70)
    print("FULL CAPL ANALYSIS PIPELINE")
    print("=" * 70)
    
    # Create test file
    file_path = create_problematic_code()
    
    # Step 1: Extract symbols
    print("\n📝 Step 1: Extracting symbols...")
    extractor = CAPLSymbolExtractor()
    num_symbols = extractor.store_symbols(file_path)
    print(f"   ✓ Found {num_symbols} symbols")
    
    # Step 2: Build cross-references
    print("\n🔗 Step 2: Building cross-references...")
    xref = CAPLCrossReferenceBuilder()
    num_refs = xref.analyze_file_references(file_path)
    print(f"   ✓ Found {num_refs} references")
    
    # Step 3: Run linter
    print("\n🔍 Step 3: Running static analysis...")
    linter = CAPLLinter()
    issues = linter.analyze_file(file_path)
    print(f"   ✓ Found {len(issues)} issues")
    
    # Display report
    print("\n" + linter.generate_report(issues))
    
    # Show breakdown by rule
    print("\n" + "=" * 70)
    print("ISSUES BY RULE")
    print("=" * 70)
    
    by_rule = {}
    for issue in issues:
        if issue.rule_id not in by_rule:
            by_rule[issue.rule_id] = []
        by_rule[issue.rule_id].append(issue)
    
    for rule_id, rule_issues in sorted(by_rule.items()):
        print(f"\n{rule_id}: {len(rule_issues)} issue(s)")
        for issue in rule_issues[:3]:  # Show first 3
            print(f"  Line {issue.line_number}: {issue.message[:60]}...")
        if len(rule_issues) > 3:
            print(f"  ... and {len(rule_issues) - 3} more")


def analyze_existing_file(file_path: str):
    """Analyze an existing CAPL file"""
    from capl_symbol_extractor import CAPLSymbolExtractor
    from capl_cross_reference import CAPLCrossReferenceBuilder
    from capl_linter import CAPLLinter
    
    print(f"Analyzing: {file_path}")
    print("=" * 70)
    
    # Ensure data is up to date
    print("\n1️⃣ Extracting symbols...")
    extractor = CAPLSymbolExtractor()
    extractor.store_symbols(file_path)
    
    print("2️⃣ Building cross-references...")
    xref = CAPLCrossReferenceBuilder()
    xref.analyze_file_references(file_path)
    
    print("3️⃣ Running linter...\n")
    linter = CAPLLinter()
    issues = linter.analyze_file(file_path)
    
    print(linter.generate_report(issues))
    
    return issues


def compare_before_after():
    """Show how linter helps improve code quality"""
    
    # Bad code
    bad_code = """
variables {
  message EngineState engine;
  msTimer timer1;
  int count = 0;
}

on start {
  setTimer(timer1, 100);
}

on timer timer1 {
  engine.RPM = 2500;
  output(engine);
}

void Helper() {
  write("Helper called");
}
"""
    
    # Good code (fixed)
    good_code = """
variables {
  message EngineState msgEngine;
  msTimer tUpdate;
  int gCount = 0;
}

on start {
  setTimer(tUpdate, 100);
  Helper();
}

on message EngineState {
  write("Received: %d RPM", this.RPM);
}

on timer tUpdate {
  msgEngine.RPM = 2500;
  output(msgEngine);
  setTimer(this, 100);  // Reset timer
}

void Helper() {
  write("Helper called");
  gCount++;
}
"""
    
    print("=" * 70)
    print("CODE QUALITY COMPARISON")
    print("=" * 70)
    
    # Save and analyze bad code
    with open("BadCode.can", 'w') as f:
        f.write(bad_code)
    
    print("\n❌ BEFORE (with issues):")
    print("-" * 70)
    issues_before = analyze_existing_file("BadCode.can")
    
    # Save and analyze good code
    with open("GoodCode.can", 'w') as f:
        f.write(good_code)
    
    print("\n✅ AFTER (fixed):")
    print("-" * 70)
    issues_after = analyze_existing_file("GoodCode.can")
    
    print("\n" + "=" * 70)
    print("IMPROVEMENT SUMMARY")
    print("=" * 70)
    print(f"Issues before: {len(issues_before)}")
    print(f"Issues after:  {len(issues_after)}")
    print(f"Improvement:   {len(issues_before) - len(issues_after)} issues fixed")


def quick_check(file_path: str):
    """Quick check - just show error and warning counts"""
    from capl_linter import CAPLLinter, Severity
    
    linter = CAPLLinter()
    issues = linter.analyze_file(file_path)
    
    errors = sum(1 for i in issues if i.severity == Severity.ERROR)
    warnings = sum(1 for i in issues if i.severity == Severity.WARNING)
    info = sum(1 for i in issues if i.severity == Severity.INFO)
    style = sum(1 for i in issues if i.severity == Severity.STYLE)
    
    if not issues:
        print(f"✅ {Path(file_path).name}: Clean!")
    else:
        parts = []
        if errors: parts.append(f"❌ {errors} error(s)")
        if warnings: parts.append(f"⚠️  {warnings} warning(s)")
        if info: parts.append(f"ℹ️  {info} info")
        if style: parts.append(f"💅 {style} style")
        
        print(f"{Path(file_path).name}: {', '.join(parts)}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "demo":
            # Full demo with problematic code
            run_full_analysis()
        
        elif command == "compare":
            # Show before/after
            compare_before_after()
        
        elif command == "quick":
            # Quick check of file(s)
            for file_path in sys.argv[2:]:
                quick_check(file_path)
        
        else:
            # Analyze specific file
            analyze_existing_file(command)
    
    else:
        print("Usage:")
        print("  python test_capl_linter.py demo       - Run full demo")
        print("  python test_capl_linter.py compare    - Show before/after")
        print("  python test_capl_linter.py quick <files>  - Quick check")
        print("  python test_capl_linter.py <file>     - Analyze specific file")