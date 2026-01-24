import re
from typing import Callable


def apply_text_transformation(source: str, transform_func: Callable[[str], str]) -> str:
    """
    Splits source into tokens (code, comments, strings) and applies
    transform_func ONLY to code segments.
    """
    # Regex to capture:
    # 1. Line comments: //...
    # 2. Block comments: /* ... */
    # 3. Strings: "..."
    # 4. Char literals: '...'

    # Using triple quotes to avoid escaping hell
    pattern = r"""(//.*|/[*][\s\S]*?[*]/|"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*')"""

    parts = re.split(pattern, source)

    for i in range(0, len(parts), 2):
        # Even indices are code (because split matches are at odd indices)
        parts[i] = transform_func(parts[i])

    return "".join(parts)
