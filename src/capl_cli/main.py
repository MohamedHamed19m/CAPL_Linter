from pathlib import Path

import typer
from capl_linter.autofix import AutoFixEngine
from capl_linter.engine import LinterEngine
from capl_linter.registry import registry
from capl_symbol_db.database import SymbolDatabase
from capl_symbol_db.extractor import SymbolExtractor
from capl_symbol_db.xref import CrossReferenceBuilder

from .config import LintConfig
from .converters import internal_issue_to_lint_issue

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
