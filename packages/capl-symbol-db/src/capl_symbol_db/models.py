from dataclasses import dataclass
from typing import Optional, List, Any


@dataclass
class SymbolInfo:
    """Represents a symbol found in CAPL code"""

    name: str
    symbol_type: str  # 'function', 'event_handler', 'variable', etc.
    line_number: int
    signature: Optional[str] = None
    scope: Optional[str] = None
    declaration_position: Optional[str] = None
    parent_symbol: Optional[str] = None
    context: Optional[str] = None


@dataclass
class VariableDeclaration(SymbolInfo):
    """Specific info for variable declarations"""

    var_type: Optional[str] = None
    is_global: bool = False


@dataclass
class FunctionDefinition(SymbolInfo):
    """Specific info for function definitions"""

    return_type: Optional[str] = None
    parameters: Optional[List[str]] = None


@dataclass
class TypeDefinition:
    """Represents an enum or struct definition"""

    name: str
    kind: str  # 'enum' or 'struct'
    line_number: int
    members: List[str]
    scope: str
