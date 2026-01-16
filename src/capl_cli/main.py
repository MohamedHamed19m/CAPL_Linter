import typer
from typing import List, Optional
from pathlib import Path
import sys

from capl_linter.engine import LinterEngine
from capl_linter.autofix import AutoFixEngine
from capl_symbol_db.extractor import SymbolExtractor
from capl_symbol_db.database import SymbolDatabase
from capl_symbol_db.xref import CrossReferenceBuilder

from .converters import internal_issue_to_lint_issue

app = typer.Typer(help="CAPL Static Analyzer - Analyze CAPL code for issues and dependencies")

@app.command()
def lint(
    files: List[Path] = typer.Argument(None, help="Files to lint"),
    project: bool = typer.Option(False, help="Lint entire project"),
    severity: str = typer.Option("STYLE", help="Minimum severity to show"),
    db: str = typer.Option("aic.db", help="Database path"),
    fix: bool = typer.Option(False, help="Automatically fix issues"),
):
    """Run linter on CAPL files"""
    engine = LinterEngine(db_path=db)
    all_issues = []
    
    if project:
        # To be implemented: analyze_project in engine
        typer.echo("Project linting not fully implemented in workspace yet")
        raise typer.Exit(code=1)
    
    if not files:
        typer.echo("Error: Provide files or use --project")
        raise typer.Exit(code=1)
        
    for file_path in files:
        max_passes = 10
        passes = 0
        
        while passes < max_passes:
            passes += 1
            issues = engine.analyze_file(file_path, force=(passes > 1))
            all_issues.extend(issues) if passes == 1 else None # Only collect once for final report if needed, or handle differently
            
            if not fix:
                break
                
            fixable = [i for i in issues if i.auto_fixable]
            if not fixable:
                break
                
            autofix = AutoFixEngine()
            
            # Pick one rule type to fix at a time
            # Priority list for fixes
            priority = [
                "missing-enum-keyword",
                "missing-struct-keyword",
                "function-declaration",
                "global-enum-definition",
                "global-struct-definition",
                "variable-outside-block",
                "variable-mid-block",
            ]
            
            target_rule = None
            for r in priority:
                if any(i.rule_id == r for i in fixable):
                    target_rule = r
                    break
            
            if not target_rule:
                target_rule = fixable[0].rule_id
                
            rule_issues = [i for i in fixable if i.rule_id == target_rule]
            typer.echo(f"  🔧 Applying fixes for {target_rule} ({len(rule_issues)} issues)...")
            
            new_content = autofix.apply_fixes(file_path, rule_issues)
            file_path.write_text(new_content, encoding="utf-8")
            
            # Re-collect all issues for the global accumulator after final pass?
            # For simplicity, we just break here if we were not fixing.
            # But we ARE fixing, so we loop.
            if passes == max_passes:
                typer.echo(f"Warning: Reached max fix passes for {file_path}")

        # Re-analyze one last time to get final issues
        final_issues = engine.analyze_file(file_path, force=True)
        all_issues.extend(final_issues)

    # Convert to external models and print (simplified report for now)
    external_issues = [internal_issue_to_lint_issue(i) for i in all_issues]
    for issue in external_issues:
        typer.echo(f"{issue.severity}: {issue.file_path}:{issue.line_number} [{issue.rule_id}] - {issue.message}")

    errors = sum(1 for i in external_issues if i.severity == "ERROR")
    if errors > 0:
        raise typer.Exit(code=1)

@app.command()
def analyze(
    files: List[Path] = typer.Argument(..., help="Files to analyze"),
    db: str = typer.Option("aic.db", help="Database path"),
):
    """Analyze dependencies and symbols"""
    database = SymbolDatabase(db)
    extractor = SymbolExtractor()
    xref = CrossReferenceBuilder(database)
    
    for file_path in files:
        typer.echo(f"Analyzing {file_path}...")
        syms = extractor.extract_all(file_path)
        
        with open(file_path, "rb") as f:
            file_id = database.store_file(file_path, f.read())
        database.store_symbols(file_id, syms)
        
        num_refs = xref.analyze_file_references(file_path)
        typer.echo(f"  ✓ {len(syms)} symbols, {num_refs} references")

@app.command()
def refs(
    symbol: str = typer.Argument(..., help="Symbol name to find"),
    db: str = typer.Option("aic.db", help="Database path"),
):
    """Find references to a symbol"""
    # To be implemented in CrossReferenceBuilder
    typer.echo(f"Searching for references to '{symbol}' (To be implemented)")

if __name__ == "__main__":
    app()
