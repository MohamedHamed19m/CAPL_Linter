from pathlib import Path
from typing import Any

import tomllib


class LintConfig:
    """Handles loading and validation of .capl-lint.toml configuration"""

    def __init__(self, config_path: Path | None = None):
        self.select: list[str] = ["E", "W"]
        self.ignore: list[str] = []
        self.builtins: list[str] = []

        if config_path and config_path.exists():
            self._load_from_file(config_path)

    def _load_from_file(self, path: Path):
        try:
            with open(path, "rb") as f:
                data = tomllib.load(f)

            lint_data = data.get("tool", {}).get("capl-lint", {})
            self.select = lint_data.get("select", self.select)
            self.ignore = lint_data.get("ignore", self.ignore)

            # Additional built-ins from config
            self.builtins = lint_data.get("builtins", {}).get("custom", [])
        except Exception:
            # Fallback to defaults if parsing fails
            pass

    def apply_to_registry(self, registry: Any) -> list[Any]:
        """Return list of enabled rules based on this config"""
        return registry.get_enabled_rules(select=self.select, ignore=self.ignore)


class FormatConfig:
    """Handles loading and validation of .capl-format.toml configuration"""

    def __init__(self, config_path: Path | None = None):
        self.indent_size: int = 2
        self.line_length: int = 100
        self.brace_style: str = "k&r"
        self.quote_style: str = "double"
        self.reorder_top_level: bool = False

        if config_path and config_path.exists():
            self._load_from_file(config_path)

    def _load_from_file(self, path: Path):
        try:
            with open(path, "rb") as f:
                data = tomllib.load(f)

            fmt_data = data.get("tool", {}).get("capl-format", {})
            self.indent_size = fmt_data.get("indent-size", self.indent_size)
            self.line_length = fmt_data.get("line-length", self.line_length)
            self.brace_style = fmt_data.get("brace-style", self.brace_style)
            self.quote_style = fmt_data.get("quote-style", self.quote_style)
            self.reorder_top_level = fmt_data.get("reorder-top-level", self.reorder_top_level)
        except Exception:
            pass

    def to_formatter_config(self) -> Any:
        from capl_formatter.models import FormatterConfig

        return FormatterConfig(
            indent_size=self.indent_size,
            line_length=self.line_length,
            brace_style=self.brace_style,
            quote_style=self.quote_style,
            reorder_top_level=self.reorder_top_level,
        )
