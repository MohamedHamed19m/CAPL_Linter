"""
Command-line interface for CAPL Analyzer
"""

import argparse
import sys
from pathlib import Path

from capl_analyzer.dependency_analyzer import CAPLDependencyAnalyzer
from capl_analyzer.symbol_extractor import CAPLSymbolExtractor
from capl_analyzer.cross_reference import CAPLCrossReferenceBuilder
from capl_analyzer.linter import CAPLLinter


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="CAPL Static Analyzer - Analyze CAPL code for issues and dependencies"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Lint command
    lint_parser = subparsers.add_parser("lint", help="Run linter on CAPL files")
    lint_parser.add_argument("files", nargs="*", help="Files to lint")
    lint_parser.add_argument("--project", action="store_true", help="Lint entire project")
    lint_parser.add_argument(
        "--severity",
        choices=["error", "warning", "info", "style"],
        help="Minimum severity to show"
    )
    
    # Analyze command
    analyze_parser = subparsers.add_parser("analyze", help="Analyze dependencies and symbols")
    analyze_parser.add_argument("files", nargs="+", help="Files to analyze")
    analyze_parser.add_argument("--db", default="aic.db", help="Database path")
    
    # Refs command
    refs_parser = subparsers.add_parser("refs", help="Find references to a symbol")
    refs_parser.add_argument("symbol", help="Symbol name to find")
    refs_parser.add_argument("--db", default="aic.db", help="Database path")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    if args.command == "lint":
        return run_lint(args)
    elif args.command == "analyze":
        return run_analyze(args)
    elif args.command == "refs":
        return run_refs(args)
    
    return 0


def run_lint(args):
    """Run linter"""
    linter = CAPLLinter()
    
    if args.project:
        issues = linter.analyze_project()
    elif args.files:
        issues = []
        for file_path in args.files:
            issues.extend(linter.analyze_file(file_path))
    else:
        print("Error: Provide files or use --project")
        return 1
    
    print(linter.generate_report(issues))
    
    # Return non-zero if errors found
    errors = sum(1 for i in issues if i.severity.value == "ERROR")
    return 1 if errors > 0 else 0


def run_analyze(args):
    """Run full analysis"""
    print("Analyzing files...")
    
    for file_path in args.files:
        print(f"\n📝 {file_path}")
        
        # Extract symbols
        extractor = CAPLSymbolExtractor(args.db)
        num_symbols = extractor.store_symbols(file_path)
        print(f"  ✓ {num_symbols} symbols")
        
        # Build cross-references
        xref = CAPLCrossReferenceBuilder(args.db)
        num_refs = xref.analyze_file_references(file_path)
        print(f"  ✓ {num_refs} references")
    
    print("\n✅ Analysis complete!")
    return 0


def run_refs(args):
    """Find references to a symbol"""
    xref = CAPLCrossReferenceBuilder(args.db)
    refs = xref.find_all_references(args.symbol)
    
    if not refs:
        print(f"No references found for '{args.symbol}'")
        return 1
    
    print(f"References to '{args.symbol}':")
    for ref in refs:
        print(f"  {Path(ref.file_path).name}:{ref.line_number} [{ref.reference_type}]")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
