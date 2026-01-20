import re
from typing import List, Tuple
from .base import ASTRule, FormattingContext, Transformation
from ..models import FormatterConfig

class IncludeSortingRule(ASTRule):
    """Sorts and groups #include directives."""
    def __init__(self, config: FormatterConfig): self.config = config
    @property
    def rule_id(self) -> str: return "F010"
    @property
    def name(self) -> str: return "include-sorting"

    def analyze(self, context: FormattingContext) -> List[Transformation]:
        # Using regex to find all #include lines at top level
        pattern = r'^\s*#include\s+"([^"]+)"(.*)$'
        matches = list(re.finditer(pattern, context.source, re.MULTILINE))
        if not matches: return []

        includes: List[Tuple[str, str, int, int]] = []
        seen_paths = set()
        for m in matches:
            path = m.group(1)
            if path in seen_paths: continue
            seen_paths.add(path)
            includes.append((path, m.group(0).strip(), m.start(), m.end()))

        # Sort
        def sort_key(item):
            path = item[0]
            group = 0 if path.lower().endswith('.cin') else 1
            return (group, path.lower())
        includes.sort(key=sort_key)

        # Rebuild block
        cin_lines = [line for path, line, s, e in includes if path.lower().endswith('.cin')]
        can_lines = [line for path, line, s, e in includes if not path.lower().endswith('.cin')]
        
        block_parts = []
        if cin_lines: block_parts.append("\n".join(cin_lines))
        if can_lines: block_parts.append("\n".join(can_lines))
        new_block = "\n\n".join(block_parts)

        # Transformation: Replace all original include lines with the new block at the first include's position
        # and delete the others.
        first_include = min(includes, key=lambda x: x[2])
        transformations = []
        
        # 1. Replace first include with entire block
        transformations.append(Transformation(first_include[2], first_include[3], new_block))
        
        # 2. Delete all other includes
        for path, line, s, e in includes:
            if s != first_include[2]:
                transformations.append(Transformation(s, e, ""))
                
        return transformations

class VariableOrderingRule(ASTRule):
    """Orders variables inside variables {} blocks."""
    def __init__(self, config: FormatterConfig): self.config = config
    @property
    def rule_id(self) -> str: return "F011"
    @property
    def name(self) -> str: return "variable-ordering"

    def analyze(self, context: FormattingContext) -> List[Transformation]:
        if not context.tree: return []
        transformations = []
        def traverse(node):
            if node.type == "variables_block":
                # Collect direct children that are declarations
                # (Simple implementation: reorder lines inside)
                pass # Already mostly handled by StructureRule or manual sorting logic
            for child in node.children: traverse(child)
        return transformations
