import re
from capl_formatter.rules.base import BaseFormattingRule, FormattingContext
from capl_formatter.models import FormatterConfig
from capl_formatter.utils import apply_text_transformation

class DefinitionWrappingRule(BaseFormattingRule):
    def __init__(self, config: FormatterConfig):
        self.config = config

    def apply(self, context: FormattingContext) -> None:
        def transform(code: str) -> str:
            # Match function definitions
            # type name ( args ) {
            types = r'(void|int|float|byte|word|dword|qword|long|short|char|double|message|msTimer|timer)'
            # Use non-capturing group for types OR adjust indices.
            # Here: group(1) matches type keyword.
            pattern = rf'(\b{types}\s+\w+)\s*\(([^)]*)\)\s*{{'
            
            def repl(match):
                header = match.group(1) # type name (e.g. "void Func")
                # match.group(2) is the type keyword (e.g. "void") because of nested parens in regex string
                args_str = match.group(3) # args
                
                # Check length (approx)
                signature = f"{header}({args_str})"
                
                if len(signature) <= self.config.line_length:
                    return match.group(0) # No change
                    
                # Chop down
                args = [a.strip() for a in args_str.split(',')]
                if not args or (len(args) == 1 and not args[0]):
                    return match.group(0)
                    
                indent = " " * self.config.indent_size
                new_args = ",\n".join([f"{indent}{a}" for a in args])
                
                return f"{header}(\n{new_args}\n) {{ "
                
            return re.sub(pattern, repl, code)

        context.source = apply_text_transformation(context.source, transform)

class CallWrappingRule(BaseFormattingRule):
    def __init__(self, config: FormatterConfig):
        self.config = config

    def apply(self, context: FormattingContext) -> None:
        def transform(code: str) -> str:
            # Match function calls ending with ;
            # name ( args ) ;
            # Heuristic regex avoiding nested calls for now
            pattern = r'(\b\w+)\s*\(([^;{}()]*)\)\s*;' # Corrected pattern to escape special regex characters
            
            def repl(match):
                name = match.group(1)
                args_str = match.group(2)
                full = match.group(0)
                
                if len(full) <= self.config.line_length:
                    return full
                    
                # Wrap
                args = [a.strip() for a in args_str.split(',')]
                if not args: return full
                
                # Fit as many as possible? Or chop?
                # Simple chop for now as proof of concept
                indent = " " * self.config.indent_size
                new_args = ",\n".join([f"{indent}{a}" for a in args])
                
                return f"{name}(\n{new_args}\n);"
                
            return re.sub(pattern, repl, code)

        context.source = apply_text_transformation(context.source, transform)

class InitializerWrappingRule(BaseFormattingRule):
    def __init__(self, config: FormatterConfig):
        self.config = config

    def apply(self, context: FormattingContext) -> None:
        def transform(code: str) -> str:
            # Match simple initializers: = { content }
            # Avoid nested braces for simplicity regex
            pattern = r'=\s*\{([^}{]*)\}'
            
            def repl(match):
                content = match.group(1)
                full = match.group(0)
                
                # If already expanded by BlockExpansionRule, content might have newlines.
                # If length <= limit, maybe we want to collapse?
                # "Smart wrapping".
                # But BlockExpansionRule FORCE expands blocks.
                # So we likely have newlines.
                
                # If line is too long (even with newlines?), wrap items.
                # Content might be "1, 2, 3, 4".
                items = [i.strip() for i in content.split(',')]
                items = [i for i in items if i] # Remove empty
                
                if not items: return full
                
                # Calculate approximate length of content on one line
                single_line_len = sum(len(i) for i in items) + len(items)*2 # items + ", "
                
                if single_line_len > self.config.line_length:
                    new_content = ",\n".join(items)
                    return f"= {{\n{new_content}\n}}"
                
                return full

            return re.sub(pattern, repl, code)

        context.source = apply_text_transformation(context.source, transform)