from dataclasses import dataclass


@dataclass
class SymbolInfo:
    """Represents a symbol found in CAPL code"""

    name: str
    symbol_type: str  # 'function', 'event_handler', 'variable', etc.
    line_number: int
    signature: str | None = None
    scope: str | None = None
    declaration_position: str | None = None
    parent_symbol: str | None = None
    context: str | None = None
    param_count: int | None = None
    has_body: bool | None = None


@dataclass
class VariableDeclaration(SymbolInfo):
    """Specific info for variable declarations"""

    var_type: str | None = None
    is_global: bool = False


@dataclass
class FunctionDefinition(SymbolInfo):
    """Specific info for function definitions"""

    return_type: str | None = None
    parameters: list[str] | None = None


@dataclass
class TypeDefinition:
    """Represents an enum or struct definition"""

    name: str
    kind: str  # 'enum' or 'struct'
    line_number: int
    members: list[str]
    scope: str
