from pathlib import Path

import typer
from capl_linter.autofix import AutoFixEngine
from capl_linter.engine import LinterEngine
from capl_linter.registry import registry
from capl_symbol_db.database import SymbolDatabase
from capl_symbol_db.extractor import SymbolExtractor
from capl_symbol_db.xref import CrossReferenceBuilder

from .config import LintConfig, FormatConfig
from .converters import internal_issue_to_lint_issue

from capl_formatter.engine import FormatterEngine
from capl_formatter.models import FormatterConfig
from capl_formatter.rules import (
    QuoteNormalizationRule,
    BlockExpansionRule,
    BraceStyleRule,
    SpacingRule,
    IndentationRule,
    BlankLineRule,
    IncludeSortingRule,
    VariableOrderingRule,
    DefinitionWrappingRule,
    CallWrappingRule,
    InitializerWrappingRule,
    WhitespaceCleanupRule
)

app = typer.Typer(help="CAPL Static Analyzer - Analyze CAPL code for issues and dependencies")


@app.command()
def lint(
    files: list[Path] = typer.Argument(None, help="Files to lint"),
    project: bool = typer.Option(False, help="Lint entire project"),
    config_file: Path = typer.Option(Path(".capl-lint.toml"), help="Path to config file"),
    severity: str = typer.Option("STYLE", help="Minimum severity to show"),
    db: str = typer.Option("aic.db", help="Database path"),
    fix: bool = typer.Option(False, help="Automatically fix issues"),
):
    """Run linter on CAPL files"""
    config = LintConfig(config_file)
    engine = LinterEngine(db_path=db, custom_builtins=config.builtins)
    enabled_rules = config.apply_to_registry(registry)
    all_issues = []

    if project:
        # If no files provided, scan current directory
        root = Path.cwd()
        typer.echo(f"Scanning project at {root}...")
        engine.analyze_project(root)
        files = list(root.glob("**/*.can")) + list(root.glob("**/*.cin"))
    elif files:
        # Even for single files, scan surrounding folder for better context
        # (Heuristic: scan same directory to find local includes/definitions)
        for f in files:
            engine.analyze_project(f.parent)

    if not files:
        typer.echo("Error: Provide files or use --project")
        raise typer.Exit(code=1)

    for file_path in files:
        max_passes = 10
        passes = 0
        current_issues = []

        while passes < max_passes:
            passes += 1
            current_issues = engine.analyze_file(file_path, force=(passes > 1), rules=enabled_rules)

            if not fix:
                break

            fixable = [i for i in current_issues if i.auto_fixable]
            if not fixable:
                break

            autofix = AutoFixEngine()

            # Priority list for fixes (updated with new IDs if they changed)
            priority = ["E004", "E005", "E002", "E003", "E006", "E007", "E008"]

            target_rule = None
            for r in priority:
                if any(i.rule_id == r for i in fixable):
                    target_rule = r
                    break

            if not target_rule:
                target_rule = fixable[0].rule_id

            rule_issues = [i for i in fixable if i.rule_id == target_rule]
            typer.echo(
                f"  🔧 Applying fixes for {target_rule} ({len(rule_issues)} issues) in {file_path.name}..."
            )

            new_content = autofix.apply_fixes(file_path, rule_issues)
            file_path.write_text(new_content, encoding="utf-8")

            if passes == max_passes:
                typer.echo(f"Warning: Reached max fix passes for {file_path}")

        all_issues.extend(current_issues)

    # Convert to external models and print (simplified report for now)
    external_issues = [internal_issue_to_lint_issue(i) for i in all_issues]

    # Sort and filter by severity
    severity_rank = {"ERROR": 3, "WARNING": 2, "STYLE": 1}
    min_rank = severity_rank.get(severity.upper(), 1)

    reported_count = 0
    for issue in sorted(external_issues, key=lambda x: (x.file_path, x.line_number)):
        if severity_rank.get(issue.severity, 0) >= min_rank:
            typer.echo(
                f"{issue.severity}: {issue.file_path}:{issue.line_number} [{issue.rule_id}] - {issue.message}"
            )
            reported_count += 1

    typer.echo(f"\nTotal issues found: {len(external_issues)} ({reported_count} reported)")

    errors = sum(1 for i in external_issues if i.severity == "ERROR")
    if errors > 0:
        raise typer.Exit(code=1)


@app.command()
def format(
    paths: list[Path] = typer.Argument(None, help="Files or directories to format"),
    check: bool = typer.Option(False, "--check", help="Check for formatting violations without modifying files"),
    json_output: bool = typer.Option(False, "--json", help="Output results in JSON format"),
    config_file: Path = typer.Option(Path(".capl-format.toml"), help="Path to formatter config file"),
):
    """Format CAPL files according to opinionated standards."""
    # 1. Collect files
    files = []
    if not paths:
        # Default to current directory if no paths provided
        paths = [Path.cwd()]
        
    for p in paths:
        if p.is_file():
            if p.suffix.lower() in [".can", ".cin"]:
                files.append(p)
        elif p.is_dir():
            files.extend(p.glob("**/*.can"))
            files.extend(p.glob("**/*.cin"))

    if not files:
        if not json_output:
            typer.echo("No CAPL files found to format.")
        raise typer.Exit(code=0)

    # 2. Setup Formatter
    fmt_config = FormatConfig(config_file)
    config = fmt_config.to_formatter_config()
    engine = FormatterEngine(config)
    
    # Recommended Rule Order
    engine.add_rule(QuoteNormalizationRule(config))
    engine.add_rule(BlockExpansionRule(config))
    engine.add_rule(BraceStyleRule(config))
    engine.add_rule(SpacingRule(config))
    engine.add_rule(DefinitionWrappingRule(config))
    engine.add_rule(CallWrappingRule(config))
    engine.add_rule(InitializerWrappingRule(config))
    engine.add_rule(IndentationRule(config))
    engine.add_rule(BlankLineRule(config))
    engine.add_rule(IncludeSortingRule(config))
    engine.add_rule(WhitespaceCleanupRule(config))

    # 3. Process files
    results = []
    modified_count = 0
    error_count = 0
    
    for f in files:
        try:
            source = f.read_text(encoding="utf-8")
            result = engine.format_string(source, str(f))
            
            if result.errors:
                error_count += 1
            elif result.modified:
                modified_count += 1
                if not check:
                    f.write_text(result.source, encoding="utf-8")
            
            results.append({
                "file": str(f),
                "modified": result.modified,
                "errors": result.errors
            })
        except Exception as e:
            error_count += 1
            results.append({
                "file": str(f),
                "modified": False,
                "errors": [str(e)]
            })

    # 4. Report
    if json_output:
        import json
        typer.echo(json.dumps({
            "results": results,
            "total_files": len(files),
            "modified_files": modified_count,
            "error_files": error_count
        }, indent=2))
    else:
        for r in results:
            status = "MODIFIED" if r["modified"] else "UNCHANGED"
            if check and r["modified"]:
                status = "WOULD BE MODIFIED"
            
            if r["errors"]:
                status = "ERROR"
                typer.echo(f"{status}: {r['file']} - {r['errors'][0]}")
            else:
                if r["modified"] or not check:
                    typer.echo(f"{status}: {r['file']}")

        typer.echo(f"\nSummary: {len(files)} files processed. {modified_count} modified, {error_count} errors.")

    # 5. Exit code
    if error_count > 0:
        raise typer.Exit(code=1)
    if check and modified_count > 0:
        raise typer.Exit(code=1)


@app.command()
def analyze(
    files: list[Path] = typer.Argument(..., help="Files to analyze"),
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
