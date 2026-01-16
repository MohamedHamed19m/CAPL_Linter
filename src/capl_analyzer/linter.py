"""
CAPL Linter - Static Analysis and Code Quality Checker
Uses the symbol database and cross-reference system to detect issues
"""

import sqlite3
from pathlib import Path
from typing import List, Dict, Set, Optional
from dataclasses import dataclass
from enum import Enum


class Severity(Enum):
    """Issue severity levels"""
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"
    STYLE = "STYLE"


@dataclass
class LintIssue:
    """A linting issue found in code"""
    severity: Severity
    file_path: str
    line_number: int
    column: int
    rule_id: str
    message: str
    suggestion: Optional[str] = None


class CAPLLinter:
    """Static analyzer for CAPL code"""
    
    def __init__(self, db_path: str = "aic.db"):
        self.db_path = db_path
        self.issues: List[LintIssue] = []
    
    def _ensure_file_analyzed(self, file_path: str):
        """Ensure the file has been analyzed and symbols/refs are in DB"""
        from .symbol_extractor import CAPLSymbolExtractor
        from .cross_reference import CAPLCrossReferenceBuilder
        from .dependency_analyzer import CAPLDependencyAnalyzer
        
        extractor = CAPLSymbolExtractor(self.db_path)
        xref = CAPLCrossReferenceBuilder(self.db_path)
        dep_analyzer = CAPLDependencyAnalyzer(self.db_path)
        
        file_needs_analysis = True
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT file_id, last_parsed FROM files 
                    WHERE file_path = ?
                """, (file_path,))
                
                result = cursor.fetchone()
                
                if result:
                    file_id = result[0]
                    cursor = conn.execute("""
                        SELECT COUNT(*) FROM symbols WHERE file_id = ?
                    """, (file_id,))
                    symbol_count = cursor.fetchone()[0]
                    
                    if symbol_count > 0:
                        file_needs_analysis = False
        except sqlite3.OperationalError:
            file_needs_analysis = True
        
        if file_needs_analysis:
            extractor.store_symbols(file_path)
            xref.analyze_file_references(file_path)
            dep_analyzer.analyze_file(file_path)

    def analyze_file(self, file_path: str) -> List[LintIssue]:
        """Run all lint checks on a file"""
        self.issues = []
        file_path = str(Path(file_path).resolve())
        
        # Ensure file is analyzed before linting
        self._ensure_file_analyzed(file_path)
        
        # Run various checks
        self._check_unused_variables(file_path)
        self._check_unused_functions(file_path)
        self._check_undefined_references(file_path)
        self._check_timer_misuse(file_path)
        self._check_message_handlers(file_path)
        self._check_naming_conventions(file_path)
        self._check_duplicate_handlers(file_path)
        self._check_missing_setTimer_in_timer_handler(file_path)
        self._check_circular_dependencies(file_path)
        
        return sorted(self.issues, key=lambda x: (x.file_path, x.line_number))
    
    def analyze_project(self) -> List[LintIssue]:
        """Run all lint checks on entire project"""
        self.issues = []
        
        files = []
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("SELECT DISTINCT file_path FROM files")
                files = [row[0] for row in cursor.fetchall()]
        except sqlite3.OperationalError:
            # Table might not exist yet
            pass
        
        for file_path in files:
            self.analyze_file(file_path)
        
        # Add project-wide checks
        self._check_orphaned_messages()
        self._check_never_output_messages()
        
        return sorted(self.issues, key=lambda x: (x.file_path, x.line_number))
    
    def _check_unused_variables(self, file_path: str):
        """Detect variables that are declared but never used"""
        with sqlite3.connect(self.db_path) as conn:
            # Find all variable declarations
            cursor = conn.execute("""
                SELECT s.symbol_name, s.line_number, s.symbol_type
                FROM symbols s
                JOIN files f ON s.file_id = f.file_id
                WHERE f.file_path = ? 
                  AND s.symbol_type IN ('variable', 'message_variable', 'timer')
                  AND s.scope IN ('variables_block', 'global')
            """, (file_path,))
            
            variables = cursor.fetchall()
            
            for var_name, line_num, var_type in variables:
                # Check if it's referenced anywhere (calls, usage, assignment, output)
                ref_cursor = conn.execute("""
                    SELECT COUNT(*) FROM symbol_references sr
                    JOIN files f ON sr.file_id = f.file_id
                    WHERE sr.symbol_name = ? 
                      AND sr.reference_type IN ('call', 'usage', 'assignment', 'output')
                """, (var_name,))
                
                ref_count = ref_cursor.fetchone()[0]
                
                # Also check message_usage table for message variables
                if var_type == 'message_variable':
                    msg_usage_cursor = conn.execute("""
                        SELECT COUNT(*) FROM message_usage
                        WHERE message_name = ?
                    """, (var_name,))
                    ref_count += msg_usage_cursor.fetchone()[0]
                
                if ref_count == 0:
                    self.issues.append(LintIssue(
                        severity=Severity.WARNING,
                        file_path=file_path,
                        line_number=line_num,
                        column=0,
                        rule_id="unused-variable",
                        message=f"Variable '{var_name}' is declared but never used",
                        suggestion=f"Remove unused {var_type.replace('_', ' ')} '{var_name}'"
                    ))
    
    def _check_unused_functions(self, file_path: str):
        """Detect functions that are defined but never called"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT s.symbol_name, s.line_number
                FROM symbols s
                JOIN files f ON s.file_id = f.file_id
                WHERE f.file_path = ?
                  AND s.symbol_type = 'function'
            """, (file_path,))
            
            functions = cursor.fetchall()
            
            for func_name, line_num in functions:
                # Check if it's called anywhere
                ref_cursor = conn.execute("""
                    SELECT COUNT(*) FROM symbol_references
                    WHERE symbol_name = ? AND reference_type = 'call'
                """, (func_name,))
                
                call_count = ref_cursor.fetchone()[0]
                
                if call_count == 0:
                    # Could be an API function or entry point, so make it INFO
                    self.issues.append(LintIssue(
                        severity=Severity.INFO,
                        file_path=file_path,
                        line_number=line_num,
                        column=0,
                        rule_id="unused-function",
                        message=f"Function '{func_name}' is never called",
                        suggestion="Consider removing if not an API entry point"
                    ))
    
    def _check_undefined_references(self, file_path: str):
        """Detect references to undefined symbols"""
        with sqlite3.connect(self.db_path) as conn:
            # Get all references in this file
            cursor = conn.execute("""
                SELECT DISTINCT sr.symbol_name, sr.line_number, sr.reference_type
                FROM symbol_references sr
                JOIN files f ON sr.file_id = f.file_id
                WHERE f.file_path = ?
            """, (file_path,))
            
            references = cursor.fetchall()
            
            for symbol_name, line_num, ref_type in references:
                # Skip common CAPL built-in functions and keywords
                builtins = {
                    'write', 'output', 'setTimer', 'cancelTimer', 
                    'getValue', 'setValue', 'this',
                    'variables',  # CAPL keyword
                }
                if symbol_name in builtins:
                    continue
                
                # Skip single-letter identifiers (often loop variables)
                if len(symbol_name) == 1:
                    continue
                
                # Check if symbol is defined anywhere in the project
                def_cursor = conn.execute("""
                    SELECT COUNT(*) FROM symbols
                    WHERE symbol_name = ?
                """, (symbol_name,))
                
                def_count = def_cursor.fetchone()[0]
                
                if def_count == 0:
                    self.issues.append(LintIssue(
                        severity=Severity.ERROR,
                        file_path=file_path,
                        line_number=line_num,
                        column=0,
                        rule_id="undefined-symbol",
                        message=f"Reference to undefined symbol '{symbol_name}'",
                        suggestion="Check spelling or add #include for external definitions"
                    ))
    
    def _check_timer_misuse(self, file_path: str):
        """Check for timers that are set but have no handler"""
        with sqlite3.connect(self.db_path) as conn:
            # Find all setTimer calls
            cursor = conn.execute("""
                SELECT DISTINCT sr.symbol_name, sr.line_number
                FROM symbol_references sr
                JOIN files f ON sr.file_id = f.file_id
                WHERE f.file_path = ?
                  AND sr.context LIKE '%setTimer%'
            """, (file_path,))
            
            timers_set = cursor.fetchall()
            
            for timer_name, line_num in timers_set:
                # Check if there's an 'on timer' handler
                handler_cursor = conn.execute("""
                    SELECT COUNT(*) FROM symbols
                    WHERE symbol_name LIKE ?
                      AND symbol_type = 'event_handler'
                """, (f"%timer {timer_name}%",))
                
                handler_count = handler_cursor.fetchone()[0]
                
                if handler_count == 0:
                    self.issues.append(LintIssue(
                        severity=Severity.WARNING,
                        file_path=file_path,
                        line_number=line_num,
                        column=0,
                        rule_id="timer-no-handler",
                        message=f"Timer '{timer_name}' is set but has no 'on timer {timer_name}' handler",
                        suggestion=f"Add: on timer {timer_name} {{ ... }}"
                    ))
    
    def _check_message_handlers(self, file_path: str):
        """Check for message variables without handlers"""
        with sqlite3.connect(self.db_path) as conn:
            # Find message variables
            cursor = conn.execute("""
                SELECT s.symbol_name, s.line_number, s.signature
                FROM symbols s
                JOIN files f ON s.file_id = f.file_id
                WHERE f.file_path = ?
                  AND s.symbol_type = 'message_variable'
            """, (file_path,))
            
            msg_vars = cursor.fetchall()
            
            for msg_var, line_num, signature in msg_vars:
                # Extract message type from signature (e.g., "message EngineState msgEngine")
                if signature and 'message' in signature:
                    parts = signature.split()
                    if len(parts) >= 3 and parts[0] == 'message':
                        msg_type = parts[1]
                        
                        # Check if there's a handler for this message type
                        handler_cursor = conn.execute("""
                            SELECT COUNT(*) FROM symbols
                            WHERE symbol_name LIKE ?
                              AND symbol_type = 'event_handler'
                        """, (f"%message {msg_type}%",))
                        
                        handler_count = handler_cursor.fetchone()[0]
                        
                        if handler_count == 0:
                            self.issues.append(LintIssue(
                                severity=Severity.INFO,
                                file_path=file_path,
                                line_number=line_num,
                                column=0,
                                rule_id="message-no-handler",
                                message=f"Message variable '{msg_var}' of type '{msg_type}' has no 'on message {msg_type}' handler",
                                suggestion=f"Consider adding: on message {msg_type} {{ ... }}"
                            ))
    
    def _check_naming_conventions(self, file_path: str):
        """Check naming conventions (CAPL style guide)"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT s.symbol_name, s.line_number, s.symbol_type, s.scope
                FROM symbols s
                JOIN files f ON s.file_id = f.file_id
                WHERE f.file_path = ?
            """, (file_path,))
            
            symbols = cursor.fetchall()
            
            for symbol_name, line_num, symbol_type, scope in symbols:
                # Check for variables declared outside variables block (CAPL ERROR!)
                if symbol_type == 'variable' and scope == 'global':
                    self.issues.append(LintIssue(
                        severity=Severity.ERROR,
                        file_path=file_path,
                        line_number=line_num,
                        column=0,
                        rule_id="variable-outside-block",
                        message=f"Variable '{symbol_name}' declared outside 'variables {{}}' block",
                        suggestion=f"Move '{symbol_name}' declaration into the variables {{}} block"
                    ))
                
                # Check variables in variables block (should start with 'g' for globals)
                if symbol_type == 'variable' and scope == 'variables_block':
                    if not symbol_name.startswith('g'):
                        self.issues.append(LintIssue(
                            severity=Severity.STYLE,
                            file_path=file_path,
                            line_number=line_num,
                            column=0,
                            rule_id="naming-global-prefix",
                            message=f"Global variable '{symbol_name}' should start with 'g' prefix",
                            suggestion=f"Rename to 'g{symbol_name[0].upper()}{symbol_name[1:]}'"
                        ))
                
                # Check message variables (should start with 'msg')
                if symbol_type == 'message_variable':
                    if not symbol_name.startswith('msg'):
                        self.issues.append(LintIssue(
                            severity=Severity.STYLE,
                            file_path=file_path,
                            line_number=line_num,
                            column=0,
                            rule_id="naming-message-prefix",
                            message=f"Message variable '{symbol_name}' should start with 'msg' prefix",
                            suggestion=f"Rename to 'msg{symbol_name[0].upper()}{symbol_name[1:]}'"
                        ))
                
                # Check timer variables (should start with 't')
                if symbol_type == 'timer':
                    if not symbol_name.startswith('t'):
                        self.issues.append(LintIssue(
                            severity=Severity.STYLE,
                            file_path=file_path,
                            line_number=line_num,
                            column=0,
                            rule_id="naming-timer-prefix",
                            message=f"Timer '{symbol_name}' should start with 't' prefix",
                            suggestion=f"Rename to 't{symbol_name[0].upper()}{symbol_name[1:]}'"
                        ))
    
    def _check_duplicate_handlers(self, file_path: str):
        """Check for duplicate event handlers (e.g., multiple 'on start')"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT s.symbol_name, COUNT(*) as count, GROUP_CONCAT(s.line_number) as lines
                FROM symbols s
                JOIN files f ON s.file_id = f.file_id
                WHERE f.file_path = ?
                  AND s.symbol_type = 'event_handler'
                GROUP BY s.symbol_name
                HAVING count > 1
            """, (file_path,))
            
            duplicates = cursor.fetchall()
            
            for handler_name, count, lines_str in duplicates:
                lines = [int(l) for l in lines_str.split(',')]
                self.issues.append(LintIssue(
                    severity=Severity.ERROR,
                    file_path=file_path,
                    line_number=lines[0],
                    column=0,
                    rule_id="duplicate-handler",
                    message=f"Duplicate event handler '{handler_name}' defined {count} times (lines: {', '.join(map(str, lines))})",
                    suggestion="Remove duplicate handlers - only one handler per event is allowed"
                ))
    
    def _check_missing_setTimer_in_timer_handler(self, file_path: str):
        """Check if timer handlers forget to reset the timer"""
        with sqlite3.connect(self.db_path) as conn:
            # Find all timer handlers
            cursor = conn.execute("""
                SELECT s.symbol_name, s.line_number
                FROM symbols s
                JOIN files f ON s.file_id = f.file_id
                WHERE f.file_path = ?
                  AND s.symbol_type = 'event_handler'
                  AND s.symbol_name LIKE 'on timer %'
            """, (file_path,))
            
            timer_handlers = cursor.fetchall()
            
            for handler_name, line_num in timer_handlers:
                # Extract timer name
                timer_name = handler_name.replace('on timer ', '').strip()
                
                # Check if setTimer is called in this handler
                # (This is a simplified check - in reality, we'd need to parse function body)
                # For now, we can check if setTimer appears in references around this line
                ref_cursor = conn.execute("""
                    SELECT COUNT(*) FROM symbol_references sr
                    JOIN files f ON sr.file_id = f.file_id
                    WHERE f.file_path = ?
                      AND sr.symbol_name IN ('setTimer', ?)
                      AND sr.line_number >= ?
                      AND sr.line_number <= ?
                """, (file_path, timer_name, line_num, line_num + 20))
                
                has_reset = ref_cursor.fetchone()[0] > 0
                
                if not has_reset:
                    self.issues.append(LintIssue(
                        severity=Severity.WARNING,
                        file_path=file_path,
                        line_number=line_num,
                        column=0,
                        rule_id="timer-not-reset",
                        message=f"Timer handler '{handler_name}' may not reset the timer",
                        suggestion=f"Add: setTimer({timer_name}, <delay>); or setTimer(this, <delay>);"
                    ))
    
    def _check_circular_dependencies(self, file_path: str):
        """Check for circular include dependencies"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                WITH RECURSIVE deps(source_id, target_id, path, cycle) AS (
                    SELECT i.source_file_id, i.included_file_id,
                           i.source_file_id || ',' || i.included_file_id,
                           0
                    FROM includes i
                    WHERE i.is_resolved = 1
                    
                    UNION
                    
                    SELECT deps.source_id, i.included_file_id,
                           deps.path || ',' || i.included_file_id,
                           CASE WHEN deps.source_id = i.included_file_id THEN 1 ELSE 0 END
                    FROM deps
                    JOIN includes i ON deps.target_id = i.source_file_id
                    WHERE i.is_resolved = 1
                      AND deps.cycle = 0
                      AND length(deps.path) < 1000
                )
                SELECT path FROM deps WHERE cycle = 1
            """)
            
            cycles = cursor.fetchall()
            
            if cycles:
                self.issues.append(LintIssue(
                    severity=Severity.ERROR,
                    file_path=file_path,
                    line_number=1,
                    column=0,
                    rule_id="circular-dependency",
                    message=f"Circular include dependency detected involving this file",
                    suggestion="Refactor includes to remove circular dependencies"
                ))
    
    def _check_orphaned_messages(self):
        """Check for messages that are never handled or output"""
        with sqlite3.connect(self.db_path) as conn:
            # Find all message variables
            cursor = conn.execute("""
                SELECT DISTINCT s.symbol_name, f.file_path, s.line_number
                FROM symbols s
                JOIN files f ON s.file_id = f.file_id
                WHERE s.symbol_type = 'message_variable'
            """)
            
            messages = cursor.fetchall()
            
            for msg_name, file_path, line_num in messages:
                # Check if message is ever used (referenced or output)
                ref_cursor = conn.execute("""
                    SELECT COUNT(*) FROM symbol_references
                    WHERE symbol_name = ?
                      AND reference_type IN ('usage', 'output', 'assignment')
                """, (msg_name,))
                
                usage_count = ref_cursor.fetchone()[0]
                
                # Also check message_usage table
                msg_usage_cursor = conn.execute("""
                    SELECT COUNT(*) FROM message_usage
                    WHERE message_name = ?
                """, (msg_name,))
                
                msg_usage_count = msg_usage_cursor.fetchone()[0]
                
                if usage_count == 0 and msg_usage_count == 0:
                    self.issues.append(LintIssue(
                        severity=Severity.WARNING,
                        file_path=file_path,
                        line_number=line_num,
                        column=0,
                        rule_id="orphaned-message",
                        message=f"Message variable '{msg_name}' is never used or output",
                        suggestion=f"Remove unused message variable or add output({msg_name})"
                    ))
    
    def _check_never_output_messages(self):
        """Check for messages that are handled but never sent"""
        with sqlite3.connect(self.db_path) as conn:
            # Find all message handlers
            cursor = conn.execute("""
                SELECT s.symbol_name, f.file_path, s.line_number
                FROM symbols s
                JOIN files f ON s.file_id = f.file_id
                WHERE s.symbol_type = 'event_handler'
                  AND s.symbol_name LIKE 'on message %'
            """)
            
            handlers = cursor.fetchall()
            
            for handler_name, file_path, line_num in handlers:
                # Extract message type
                msg_type = handler_name.replace('on message ', '').strip()
                
                # Check if this message type is ever output
                output_cursor = conn.execute("""
                    SELECT COUNT(*) FROM message_usage
                    WHERE usage_type = 'output'
                      AND message_name LIKE ?
                """, (f"%{msg_type}%",))
                
                output_count = output_cursor.fetchone()[0]
                
                if output_count == 0:
                    self.issues.append(LintIssue(
                        severity=Severity.INFO,
                        file_path=file_path,
                        line_number=line_num,
                        column=0,
                        rule_id="message-never-sent",
                        message=f"Handler '{handler_name}' exists but message type is never output in project",
                        suggestion="This handler may only receive external messages (OK if intentional)"
                    ))
    
    def generate_report(self, issues: Optional[List[LintIssue]] = None) -> str:
        """Generate a formatted report of issues"""
        if issues is None:
            issues = self.issues
        
        if not issues:
            return "✅ No issues found!\n"
        
        # Group by severity
        by_severity = {s: [] for s in Severity}
        for issue in issues:
            by_severity[issue.severity].append(issue)
        
        report = []
        report.append("=" * 70)
        report.append("CAPL LINTER REPORT")
        report.append("=" * 70)
        report.append(f"\nTotal Issues: {len(issues)}")
        
        for severity in [Severity.ERROR, Severity.WARNING, Severity.INFO, Severity.STYLE]:
            count = len(by_severity[severity])
            if count > 0:
                report.append(f"  {severity.value}: {count}")
        
        report.append("\n")
        
        # Report by severity
        for severity in [Severity.ERROR, Severity.WARNING, Severity.INFO, Severity.STYLE]:
            issues_of_severity = by_severity[severity]
            if not issues_of_severity:
                continue
            
            icon = {
                Severity.ERROR: "❌",
                Severity.WARNING: "⚠️",
                Severity.INFO: "ℹ️",
                Severity.STYLE: "💅"
            }[severity]
            
            report.append(f"\n{icon} {severity.value}S ({len(issues_of_severity)})")
            report.append("-" * 70)
            
            for issue in issues_of_severity:
                file_name = Path(issue.file_path).name
                report.append(f"\n{file_name}:{issue.line_number}")
                report.append(f"  [{issue.rule_id}] {issue.message}")
                if issue.suggestion:
                    report.append(f"  💡 {issue.suggestion}")
        
        report.append("\n" + "=" * 70)
        return "\n".join(report)


def main():
    """Main entry point for capl-lint CLI"""
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description="CAPL Static Analyzer / Linter")
    parser.add_argument("files", nargs="*", help="CAPL files to analyze")
    parser.add_argument("--project", action="store_true", 
                       help="Analyze entire project in database")
    parser.add_argument("--severity", choices=["error", "warning", "info", "style"],
                       help="Only show issues of this severity or higher")
    parser.add_argument("--db", default="aic.db", help="Database path (default: aic.db)")
    parser.add_argument("--quiet", "-q", action="store_true",
                       help="Only show the report, not progress messages")
    
    args = parser.parse_args()
    
    linter = CAPLLinter(db_path=args.db)
    
    if args.project:
        if not args.quiet:
            print("Analyzing entire project...")
        issues = linter.analyze_project()
    elif args.files:
        if not args.quiet:
            print(f"Analyzing {len(args.files)} file(s)...")
            print("(First run may take longer as files are being indexed)")
            print()
        issues = []
        for file_path in args.files:
            if not args.quiet:
                print(f"  📝 {Path(file_path).name}...", end=" ", flush=True)
            try:
                file_issues = linter.analyze_file(file_path)
                issues.extend(file_issues)
                if not args.quiet:
                    print(f"✓ ({len(file_issues)} issues)")
            except Exception as e:
                if not args.quiet:
                    print(f"✗ Error: {e}")
                else:
                    print(f"Error analyzing {file_path}: {e}", file=sys.stderr)
        
        if not args.quiet:
            print()
    else:
        parser.print_help()
        sys.exit(1)
    
    # Filter by severity if requested
    if args.severity:
        severity_order = ["style", "info", "warning", "error"]
        min_level = severity_order.index(args.severity.lower())
        issues = [i for i in issues if severity_order.index(i.severity.value.lower()) >= min_level]
    
    print(linter.generate_report(issues))
    
    # Exit with non-zero if errors found
    errors = sum(1 for i in issues if i.severity == Severity.ERROR)
    sys.exit(1 if errors > 0 else 0)


if __name__ == "__main__":
    main()