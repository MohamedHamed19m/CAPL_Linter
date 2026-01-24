import pytest
import difflib
from pathlib import Path
from capl_formatter.engine import FormatterEngine
from capl_formatter.models import FormatterConfig

FIXTURES_DIR = Path(__file__).parent / "fixtures"
INPUT_DIR = FIXTURES_DIR / "input"
EXPECTED_DIR = FIXTURES_DIR / "expected"


def get_test_cases():
    """Find all input files."""
    return [f.stem for f in INPUT_DIR.glob("*.can")]


@pytest.mark.parametrize("test_name", get_test_cases())
def test_golden_file(test_name):
    """Test formatter against golden files."""

    # Read input
    input_file = INPUT_DIR / f"{test_name}.can"
    input_source = input_file.read_text(encoding="utf-8")

    # Read expected output
    expected_file = EXPECTED_DIR / f"{test_name}.can"
    expected_source = expected_file.read_text(encoding="utf-8")

    # Format
    config = FormatterConfig()
    if test_name == "reorder_complex":
        config.reorder_top_level = True

    engine = FormatterEngine(config)
    engine.add_default_rules()
    result = engine.format_string(input_source)

    # Compare
    if result.source != expected_source:
        # Show diff for debugging
        diff = difflib.unified_diff(
            expected_source.splitlines(keepends=True),
            result.source.splitlines(keepends=True),
            fromfile="expected",
            tofile="actual",
        )
        diff_text = "".join(diff)
        msg = f"Formatting mismatch for {test_name}:\n{diff_text}\n"
        msg += f"Expected: {repr(expected_source)}\n"
        msg += f"Actual:   {repr(result.source)}"
        pytest.fail(msg)
