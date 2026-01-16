import sqlite3
import hashlib
from pathlib import Path
from typing import List, Optional
from .models import SymbolInfo, TypeDefinition

class SymbolDatabase:
    """Manages SQLite database for CAPL symbols and files"""

    def __init__(self, db_path: str = "aic.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize database schema"""
        conn = sqlite3.connect(self.db_path)
        try:
            with conn:
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
                        declaration_position TEXT,
                        parent_symbol TEXT,
                        context TEXT,
                        FOREIGN KEY (file_id) REFERENCES files(file_id)
                    )
                """)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS includes (
                        include_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        source_file_id INTEGER NOT NULL,
                        included_file_id INTEGER,
                        include_path TEXT NOT NULL,
                        line_number INTEGER,
                        is_resolved BOOLEAN,
                        FOREIGN KEY (source_file_id) REFERENCES files(file_id),
                        FOREIGN KEY (included_file_id) REFERENCES files(file_id)
                    )
                """)

                conn.execute("""
                    CREATE TABLE IF NOT EXISTS type_definitions (
                        type_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        file_id INTEGER NOT NULL,
                        type_name TEXT NOT NULL,
                        type_kind TEXT NOT NULL,
                        line_number INTEGER,
                        members TEXT,
                        scope TEXT,
                        FOREIGN KEY (file_id) REFERENCES files(file_id)
                    )
                """)

                conn.execute("""
                    CREATE TABLE IF NOT EXISTS symbol_references (
                        ref_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        file_id INTEGER NOT NULL,
                        symbol_name TEXT NOT NULL,
                        line_number INTEGER,
                        column_number INTEGER,
                        reference_type TEXT,
                        context TEXT,
                        FOREIGN KEY (file_id) REFERENCES files(file_id)
                    )
                """)

                conn.execute("""
                    CREATE TABLE IF NOT EXISTS message_usage (
                        usage_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        file_id INTEGER NOT NULL,
                        message_name TEXT NOT NULL,
                        usage_type TEXT,
                        line_number INTEGER,
                        FOREIGN KEY (file_id) REFERENCES files(file_id)
                    )
                """)

                # Indexes
                conn.execute("CREATE INDEX IF NOT EXISTS idx_files_path ON files(file_path)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_symbols_file ON symbols(file_id)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_symbols_name ON symbols(symbol_name)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_includes_source ON includes(source_file_id)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_includes_target ON includes(included_file_id)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_types_name ON type_definitions(type_name)")
        finally:
            conn.close()

    def store_file(self, file_path: Path, source_code: bytes) -> int:
        """Store file info and return its ID"""
        file_path_abs = str(file_path.resolve())
        file_hash = hashlib.md5(source_code).hexdigest()
        
        conn = sqlite3.connect(self.db_path)
        try:
            with conn:
                cursor = conn.execute("""
                    INSERT INTO files (file_path, parse_success, file_hash)
                    VALUES (?, 1, ?)
                    ON CONFLICT(file_path) DO UPDATE SET 
                        last_parsed = CURRENT_TIMESTAMP,
                        file_hash = excluded.file_hash
                    RETURNING file_id
                """, (file_path_abs, file_hash))
                return cursor.fetchone()[0]
        finally:
            conn.close()

    def store_symbols(self, file_id: int, symbols: List[SymbolInfo]):
        """Store symbols for a specific file"""
        conn = sqlite3.connect(self.db_path)
        try:
            with conn:
                conn.execute("DELETE FROM symbols WHERE file_id = ?", (file_id,))
                for sym in symbols:
                    conn.execute("""
                        INSERT INTO symbols (file_id, symbol_name, symbol_type, line_number, 
                                          signature, scope, declaration_position, parent_symbol, context)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        file_id, sym.name, sym.symbol_type, sym.line_number,
                        sym.signature, sym.scope, sym.declaration_position,
                        sym.parent_symbol, sym.context
                    ))
        finally:
            conn.close()

    def get_file_hash(self, file_path: Path) -> Optional[str]:
        """Get stored hash for a file"""
        file_path_abs = str(file_path.resolve())
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.execute("SELECT file_hash FROM files WHERE file_path = ?", (file_path_abs,))
            result = cursor.fetchone()
            return result[0] if result else None
        finally:
            conn.close()
