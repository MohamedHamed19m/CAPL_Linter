import re
from typing import List, Tuple
from capl_formatter.rules.base import BaseFormattingRule, FormattingContext
from capl_formatter.models import FormatterConfig

class IncludeSortingRule(BaseFormattingRule):
    def __init__(self, config: FormatterConfig):
        self.config = config

    def apply(self, context: FormattingContext) -> None:
        # Regex to match #include "path"
        # Matches optional leading whitespace, #include, whitespace, "path", optional comment/trailing
        pattern = r'^\s*#include\s+"([^"]+)"(.*)$'
        
        matches = list(re.finditer(pattern, context.source, re.MULTILINE))
        if not matches:
            return
            
        # Extract includes
        includes: List[Tuple[str, str]] = []
        seen_paths = set()
        
        for m in matches:
            path = m.group(1)
            full_line = m.group(0).strip()
            
            if path in seen_paths:
                continue
            seen_paths.add(path)
            includes.append((path, full_line))
            
        # Remove includes from source
        # We assume they are lines. re.sub line by line.
        context.source = re.sub(pattern, '', context.source, flags=re.MULTILINE)
        
        # Sort
        # Group 0: .cin, Group 1: .can (or others)
        def sort_key(item):
            path = item[0]
            is_cin = path.lower().endswith('.cin')
            group = 0 if is_cin else 1
            return (group, path.lower())
            
        includes.sort(key=sort_key)
        
        # Group logic
        cin_includes = [line for path, line in includes if path.lower().endswith('.cin')]
        can_includes = [line for path, line in includes if not path.lower().endswith('.cin')]
        
        result_lines = []
        if cin_includes:
            result_lines.extend(cin_includes)
        
        if cin_includes and can_includes:
            result_lines.append("") # Blank line between groups
            
        if can_includes:
            result_lines.extend(can_includes)
            
        block = "\n".join(result_lines)
        
        # Prepend to source
        # If source has leading newlines, trim them?
        # Pragma rule might have added newlines.
        # Ideally, we want Includes -> (newline) -> Source.
        
        # context.source might start with Pragmas.
        # If we prepend, Includes -> Pragmas.
        # But we want Includes -> Pragmas? Yes. "Pragmas should appear after includes".
        
        context.source = block + "\n\n" + context.source.lstrip()

class VariableOrderingRule(BaseFormattingRule):
    def __init__(self, config: FormatterConfig):
        self.config = config

    def apply(self, context: FormattingContext) -> None:
        # Regex to find variables { ... } block
        # Assumption: only one variables block? Or multiple?
        # CAPL usually has one global variables block. But can be inside implementation? No.
        # But maybe multiples?
        # We'll use re.sub with function to handle all matches.
        
        # Matches variables { content }
        # DOTALL to match newlines
        pattern = r'(\bvariables\s*\{)(.*?)(\})'
        # Note: This regex is naive for nested braces.
        # But variables block usually doesn't contain nested braces unless struct definition?
        # If user defines struct inside variables: struct S { int x; };
        # Then .*? stops at first }.
        # This breaks.
        
        # Proper brace matching is hard with regex.
        # Assuming Phase 2 BlockExpansionRule ran, block is expanded.
        # But nested braces?
        # Ideally, we parse.
        # For now, I'll assume simple variables block (no nested structs defined INSIDE variables block - usually structs are defined outside, or types used).
        # "Variables declared outside variables {} block" is error.
        # "Missing enum or struct keywords" -> warnings.
        # Struct definitions usually outside.
        
        def process_block(match):
            header = match.group(1)
            content = match.group(2)
            footer = match.group(3)
            
            lines = content.splitlines()
            declarations = []
            
            for line in lines:
                stripped = line.strip()
                if not stripped: continue
                declarations.append(line) # Keep original line with indentation/comments
                
            # Categorize
            messages = []
            timers = []
            sysvars = []
            primitives = []
            
            for decl in declarations:
                stripped = decl.strip()
                if stripped.startswith("message"):
                    messages.append(decl)
                elif stripped.startswith("msTimer") or stripped.startswith("timer"):
                    timers.append(decl)
                elif stripped.startswith("sysvar"):
                    sysvars.append(decl)
                else:
                    primitives.append(decl)
                    
            # Sort function
            def get_name(decl):
                # Heuristic: Find name.
                # Remove comments
                code = decl.split("//")[0].strip()
                # Remove ;
                code = code.rstrip(";")
                # Remove = ...
                code = code.split("=")[0].strip()
                # Remove array [...]
                code = code.split("[")[0].strip()
                # Last token is name
                tokens = code.split()
                if tokens:
                    return tokens[-1]
                return ""
                
            messages.sort(key=get_name)
            timers.sort(key=get_name)
            sysvars.sort(key=get_name)
            primitives.sort(key=get_name)
            
            # Rebuild
            result_lines = []
            
            indent = " " * self.config.indent_size
            
            def add_group(group):
                if group:
                    if result_lines: result_lines.append("")
                    for item in group:
                        # Ensure indentation
                        # If item already has indentation, use it? Or enforce?
                        # VariableOrderingRule rewrites structure. Enforce indent.
                        item_stripped = item.strip()
                        result_lines.append(indent + item_stripped)
                        
            add_group(messages)
            add_group(timers)
            add_group(sysvars)
            add_group(primitives)
            
            new_content = "\n".join(result_lines)
            return f"{header}\n{new_content}\n{footer}"

        context.source = re.sub(pattern, process_block, context.source, flags=re.DOTALL)
