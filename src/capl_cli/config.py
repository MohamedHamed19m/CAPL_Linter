import tomllib
from pathlib import Path
from typing import Any


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
