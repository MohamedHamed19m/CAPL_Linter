"""
CAPL Symbol Extractor using Tree-sitter
Extracts functions, event handlers, variables, and CAPL-specific constructs
"""

from dataclasses import dataclass
from typing import List, Optional
from pathlib import Path
import sqlite3
import tree_sitter_c as tsc
from tree_sitter import Language, Parser, Query, QueryCursor, Node


@dataclass
class Symbol:
    """Represents a symbol found in CAPL code"""
    name: str
    symbol_type: str  # 'function', 'event_handler', 'variable', 'message', 'timer'
    line_number: int
    signature: Optional[str] = None
    scope: Optional[str] = None  # 'global', 'variables_block', 'local'
    

class CAPLSymbolExtractor:
    """Extract symbols from CAPL files"""
    
    def __init__(self, db_path: str = "aic.db"):
        self.db_path = db_path
        self.language = Language(tsc.language())
        self.parser = Parser(self.language)
        self._init_database()
    
    def _init_database(self):
        """Create required tables if they don't exist"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS files (
                    file_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_path TEXT UNIQUE NOT NULL,
                    last_parsed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    parse_success BOOLEAN,
                    file_hash TEXT
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS symbols (
                    symbol_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_id INTEGER NOT NULL,
                    symbol_name TEXT NOT NULL,
                    symbol_type TEXT,
                    line_number INTEGER,
                    signature TEXT,
                    scope TEXT,
                    FOREIGN KEY (file_id) REFERENCES files(file_id)
                )
            """)
            conn.commit()

    def extract_symbols(self, file_path: str) -> List[Symbol]:
        """
        Extract all symbols from a CAPL file
        
        Args:
            file_path: Path to the CAPL file
            
        Returns:
            List of Symbol objects
        """
        with open(file_path, 'rb') as f:
            source_code = f.read()
        
        source_text = source_code.decode('utf8')
        tree = self.parser.parse(source_code)
        root = tree.root_node
        
        symbols = []
        
        # Extract different types of symbols
        symbols.extend(self._extract_event_handlers(root, source_text))
        symbols.extend(self._extract_functions(root, source_text))
        symbols.extend(self._extract_variables_block(root, source_text))
        symbols.extend(self._extract_global_variables(root, source_text))
        
        return symbols
    
    def _extract_event_handlers(self, root: Node, source: str) -> List[Symbol]:
        """
        Extract CAPL event handlers like 'on message', 'on signal', 'on timer'
        
        These appear as function-like structures but start with 'on' keyword
        """
        symbols = []
        
        # Query for function definitions (CAPL events look like functions to C parser)
        query = Query(self.language, """
            (function_definition
              declarator: (function_declarator
                declarator: (identifier) @func_name
                parameters: (parameter_list) @params)?) @func
        """)
        
        cursor = QueryCursor(query)
        cursor.set_byte_range(0, len(source.encode('utf8')))
        matches = cursor.matches(root)
        
        for pattern_index, captures_dict in matches:
            if "func" in captures_dict:
                for func_node in captures_dict["func"]:
                    # Get the full text of the function definition
                    func_text = source[func_node.start_byte:func_node.end_byte]
                    first_line = func_text.split('\n')[0].strip()
                    
                    # Check if it starts with 'on' - CAPL event handler
                    if first_line.startswith('on '):
                        event_info = self._parse_event_handler(first_line, func_node)
                        if event_info:
                            symbols.append(event_info)
        
        return symbols
    
    def _parse_event_handler(self, first_line: str, node: Node) -> Optional[Symbol]:
        """
        Parse CAPL event handler syntax:
        - on start
        - on message <MessageName>
        - on signal <SignalName>
        - on timer <TimerName>
        - on key <Key>
        - on preStart
        - on stopMeasurement
        """
        line_num = node.start_point[0] + 1
        
        # Remove 'on' and get the rest
        parts = first_line.split()
        if len(parts) < 2:
            return None
        
        event_type = parts[1]  # 'message', 'signal', 'timer', 'start', etc.
        
        # Determine the event name
        if event_type in ('start', 'preStart', 'stopMeasurement', 'preStop'):
            # No additional identifier
            name = f"on {event_type}"
            signature = first_line.split('{')[0].strip()
        elif len(parts) >= 3:
            # Has an identifier: on message EngineState
            identifier = parts[2]
            name = f"on {event_type} {identifier}"
            signature = first_line.split('{')[0].strip()
        else:
            name = f"on {event_type}"
            signature = first_line.split('{')[0].strip()
        
        return Symbol(
            name=name,
            symbol_type='event_handler',
            line_number=line_num,
            signature=signature,
            scope='global'
        )
    
    def _extract_functions(self, root: Node, source: str) -> List[Symbol]:
        """Extract regular function definitions (not event handlers)"""
        symbols = []
        
        query = Query(self.language, """
            (function_definition
              type: (_) @return_type
              declarator: (function_declarator
                declarator: (identifier) @func_name
                parameters: (parameter_list) @params)) @func
        """)
        
        cursor = QueryCursor(query)
        cursor.set_byte_range(0, len(source.encode('utf8')))
        matches = cursor.matches(root)
        
        for pattern_index, captures_dict in matches:
            if "func" in captures_dict and "func_name" in captures_dict:
                for i, func_node in enumerate(captures_dict["func"]):
                    # Get function text
                    func_text = source[func_node.start_byte:func_node.end_byte]
                    first_line = func_text.split('\n')[0].strip()
                    
                    # Skip if it's an event handler (starts with 'on')
                    if first_line.startswith('on '):
                        continue
                    
                    # Get function name
                    func_name_nodes = captures_dict.get("func_name", [])
                    if i < len(func_name_nodes):
                        name_node = func_name_nodes[i]
                        func_name = source[name_node.start_byte:name_node.end_byte]
                        
                        # Extract signature (everything before the opening brace)
                        signature = first_line
                        if '{' in func_text:
                            signature = func_text.split('{')[0].strip()
                        
                        symbols.append(Symbol(
                            name=func_name,
                            symbol_type='function',
                            line_number=func_node.start_point[0] + 1,
                            signature=signature,
                            scope='global'
                        ))
        
        return symbols
    
    def _extract_variables_block(self, root: Node, source: str) -> List[Symbol]:
        """
        Extract CAPL 'variables { ... }' block
        This is CAPL-specific syntax that won't be parsed correctly by C grammar
        """
        symbols = []
        
        # Use a simple text-based approach since C grammar doesn't understand
        # CAPL's 'variables' keyword
        lines = source.split('\n')
        in_variables_block = False
        block_start_line = 0
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            
            # Detect start of variables block
            if stripped.startswith('variables') and '{' in line:
                in_variables_block = True
                block_start_line = i + 1
                continue
            
            # Detect end of variables block
            if in_variables_block and '}' in stripped:
                in_variables_block = False
                continue
            
            # Extract variable declarations inside the block
            if in_variables_block and stripped and not stripped.startswith('//'):
                var_info = self._parse_variable_declaration(stripped, i + 1)
                if var_info:
                    var_info.scope = 'variables_block'
                    symbols.append(var_info)
        
        return symbols
    
    def _parse_variable_declaration(self, line: str, line_num: int) -> Optional[Symbol]:
        """
        Parse a variable declaration line
        Examples:
          - message EngineState msgEngine;
          - msTimer tCycle;
          - int gIsRunning = 0;
          - DWORD counter;
        """
        # Remove semicolon and trailing comments
        line = line.split(';')[0].strip()
        if '//' in line:
            line = line.split('//')[0].strip()
        
        parts = line.split()
        if len(parts) < 2:
            return None
        
        var_type = parts[0]
        
        # For CAPL message declarations, the format is: message <MessageType> <varName>
        # We want to extract <varName>, not <MessageType>
        if var_type == 'message' and len(parts) >= 3:
            # parts[1] is the message type (e.g., "EngineState")
            # parts[2] is the variable name (e.g., "msgEngine")
            var_name = parts[2]
        else:
            # Regular variable: <type> <name>
            var_name = parts[1]
        
        # Handle assignments (int x = 5)
        if '=' in var_name:
            var_name = var_name.split('=')[0].strip()
        
        # Determine if it's a special CAPL type
        symbol_type = 'variable'
        if var_type == 'message':
            symbol_type = 'message_variable'
        elif var_type == 'msTimer':
            symbol_type = 'timer'
        elif var_type == 'signal':
            symbol_type = 'signal_variable'
        
        return Symbol(
            name=var_name,
            symbol_type=symbol_type,
            line_number=line_num,
            signature=line,
            scope=None  # Will be set by caller
        )
    
    def _extract_global_variables(self, root: Node, source: str) -> List[Symbol]:
        """
        Extract global variable declarations (outside variables block)
        NOTE: In CAPL, this is typically an ERROR - all globals should be in variables {}
        """
        symbols = []
        
        # Query for top-level declarations
        query = Query(self.language, """
            (declaration
              declarator: (init_declarator
                declarator: (identifier) @var_name)) @decl
        """)
        
        cursor = QueryCursor(query)
        cursor.set_byte_range(0, len(source.encode('utf8')))
        matches = cursor.matches(root)
        
        for pattern_index, captures_dict in matches:
            if "decl" in captures_dict and "var_name" in captures_dict:
                for i, decl_node in enumerate(captures_dict["decl"]):
                    # Check if this is a top-level declaration (not in a function)
                    if self._is_global_scope(decl_node):
                        var_name_nodes = captures_dict.get("var_name", [])
                        if i < len(var_name_nodes):
                            name_node = var_name_nodes[i]
                            var_name = source[name_node.start_byte:name_node.end_byte]
                            
                            # Get the full declaration line
                            decl_text = source[decl_node.start_byte:decl_node.end_byte]
                            decl_line = decl_text.split('\n')[0].strip()
                            
                            # Skip if inside variables block (we handled those separately)
                            if not self._is_in_variables_block(decl_node, source):
                                # This is likely an ERROR in CAPL - variables outside the block
                                symbols.append(Symbol(
                                    name=var_name,
                                    symbol_type='variable',
                                    line_number=decl_node.start_point[0] + 1,
                                    signature=decl_line,
                                    scope='global'  # Mark as global (outside variables block)
                                ))
        
        return symbols
    
    def _is_global_scope(self, node: Node) -> bool:
        """Check if a node is at global scope (not inside a function)"""
        parent = node.parent
        while parent:
            if parent.type == 'function_definition':
                return False
            parent = parent.parent
        return True
    
    def _is_in_variables_block(self, node: Node, source: str) -> bool:
        """Check if a node is inside a variables { } block"""
        # Simple heuristic: check if 'variables' appears before this node
        # and there's a closing brace after it
        before_text = source[:node.start_byte]
        
        # Find the last occurrence of 'variables {'
        if 'variables' not in before_text:
            return False
        
        # Count braces to see if we're still inside
        last_var_pos = before_text.rfind('variables')
        text_after_var = before_text[last_var_pos:]
        
        open_braces = text_after_var.count('{')
        close_braces = text_after_var.count('}')
        
        # If more open than closed, we're inside the block
        return open_braces > close_braces
    
    def store_symbols(self, file_path: str) -> int:
        """
        Extract symbols from a file and store them in the database
        
        Returns:
            Number of symbols stored
        """
        file_path = str(Path(file_path).resolve())
        symbols = self.extract_symbols(file_path)
        
        with sqlite3.connect(self.db_path) as conn:
            # Get or create file_id
            cursor = conn.execute("""
                INSERT INTO files (file_path, parse_success)
                VALUES (?, 1)
                ON CONFLICT(file_path) DO UPDATE SET
                    last_parsed = CURRENT_TIMESTAMP
                RETURNING file_id
            """, (file_path,))
            
            file_id = cursor.fetchone()[0]
            
            # Clear old symbols for this file
            conn.execute("DELETE FROM symbols WHERE file_id = ?", (file_id,))
            
            # Insert new symbols
            for symbol in symbols:
                conn.execute("""
                    INSERT INTO symbols 
                    (file_id, symbol_name, symbol_type, line_number, signature, scope)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (file_id, symbol.name, symbol.symbol_type, 
                      symbol.line_number, symbol.signature, symbol.scope))
            
            conn.commit()
        
        return len(symbols)
    
    def find_symbol(self, symbol_name: str, symbol_type: Optional[str] = None) -> List[tuple]:
        """
        Find all occurrences of a symbol across all files
        
        Args:
            symbol_name: Name of the symbol to find
            symbol_type: Optional filter by symbol type
            
        Returns:
            List of tuples: (file_path, symbol_type, line_number, signature)
        """
        with sqlite3.connect(self.db_path) as conn:
            if symbol_type:
                cursor = conn.execute("""
                    SELECT f.file_path, s.symbol_type, s.line_number, s.signature
                    FROM symbols s
                    JOIN files f ON s.file_id = f.file_id
                    WHERE s.symbol_name = ? AND s.symbol_type = ?
                    ORDER BY f.file_path, s.line_number
                """, (symbol_name, symbol_type))
            else:
                cursor = conn.execute("""
                    SELECT f.file_path, s.symbol_type, s.line_number, s.signature
                    FROM symbols s
                    JOIN files f ON s.file_id = f.file_id
                    WHERE s.symbol_name = ?
                    ORDER BY f.file_path, s.line_number
                """, (symbol_name,))
            
            return cursor.fetchall()
    
    def list_symbols_in_file(self, file_path: str) -> List[tuple]:
        """
        List all symbols in a specific file
        
        Returns:
            List of tuples: (symbol_name, symbol_type, line_number, signature)
        """
        file_path = str(Path(file_path).resolve())
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT s.symbol_name, s.symbol_type, s.line_number, s.signature
                FROM symbols s
                JOIN files f ON s.file_id = f.file_id
                WHERE f.file_path = ?
                ORDER BY s.line_number
            """, (file_path,))
            
            return cursor.fetchall()
    
    def get_event_handlers(self) -> List[tuple]:
        """Get all CAPL event handlers across the project"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT f.file_path, s.symbol_name, s.line_number
                FROM symbols s
                JOIN files f ON s.file_id = f.file_id
                WHERE s.symbol_type = 'event_handler'
                ORDER BY s.symbol_name, f.file_path
            """)
            
            return cursor.fetchall()


# Update the database schema to include signature and scope
def update_database_schema(db_path: str = "aic.db"):
    """Add signature and scope columns to symbols table if they don't exist"""
    with sqlite3.connect(db_path) as conn:
        # First check if symbols table exists
        cursor = conn.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='symbols'
        """)
        
        if not cursor.fetchone():
            # Table doesn't exist yet, it will be created by the extractors
            return
        
        # Check if columns exist
        cursor = conn.execute("PRAGMA table_info(symbols)")
        columns = {row[1] for row in cursor.fetchall()}
        
        if 'signature' not in columns:
            conn.execute("ALTER TABLE symbols ADD COLUMN signature TEXT")
            print("Added 'signature' column to symbols table")
        
        if 'scope' not in columns:
            conn.execute("ALTER TABLE symbols ADD COLUMN scope TEXT")
            print("Added 'scope' column to symbols table")
        
        conn.commit()


# Example usage and testing
if __name__ == "__main__":
    import sys
    
    # Update schema first
    update_database_schema()
    
    extractor = CAPLSymbolExtractor()
    
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        
        print(f"Extracting symbols from: {file_path}")
        print("=" * 60)
        
        num_symbols = extractor.store_symbols(file_path)
        print(f"✓ Extracted and stored {num_symbols} symbols")
        
        print("\nSymbols found:")
        print("-" * 60)
        
        symbols = extractor.list_symbols_in_file(file_path)
        for name, sym_type, line, sig in symbols:
            print(f"Line {line:4d} | {sym_type:15s} | {name}")
            if sig:
                print(f"           {sig[:60]}...")
    else:
        print("Usage: python script.py <capl_file.can>")
        print("\nOr import and use programmatically:")
        print("  extractor = CAPLSymbolExtractor()")
        print("  extractor.store_symbols('MyNode.can')")
        print("  symbols = extractor.list_symbols_in_file('MyNode.can')")