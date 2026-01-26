import hashlib
import sqlite3
from pathlib import Path

from .models import SymbolInfo


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
                        param_count INTEGER,
                        has_body BOOLEAN,
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
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_includes_source ON includes(source_file_id)"
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_includes_target ON includes(included_file_id)"
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_types_name ON type_definitions(type_name)"
                )
        finally:
            conn.close()

    def store_file(self, file_path: Path, source_code: bytes) -> int:
        """Store file info and return its ID"""
        file_path_abs = str(file_path.resolve())
        file_hash = hashlib.md5(source_code).hexdigest()

        conn = sqlite3.connect(self.db_path)
        try:
            with conn:
                cursor = conn.execute(
                    """
                    INSERT INTO files (file_path, parse_success, file_hash)
                    VALUES (?, 1, ?)
                    ON CONFLICT(file_path) DO UPDATE SET 
                        last_parsed = CURRENT_TIMESTAMP,
                        file_hash = excluded.file_hash
                    RETURNING file_id
                """,
                    (file_path_abs, file_hash),
                )
                return cursor.fetchone()[0]
        finally:
            conn.close()

    def get_or_create_file_id(self, file_path: Path) -> int:
        """Get ID for a file, creating a placeholder entry if needed"""
        file_path_abs = str(file_path.resolve())
        conn = sqlite3.connect(self.db_path)
        try:
            with conn:
                # Try insert with NULL hash
                # We use parse_success=0 as it's not parsed yet
                try:
                    cursor = conn.execute(
                        """
                        INSERT INTO files (file_path, parse_success, file_hash)
                        VALUES (?, 0, NULL)
                        RETURNING file_id
                        """,
                        (file_path_abs,),
                    )
                    return cursor.fetchone()[0]
                except sqlite3.IntegrityError:
                    # Already exists
                    cursor = conn.execute(
                        "SELECT file_id FROM files WHERE file_path = ?", (file_path_abs,)
                    )
                    return cursor.fetchone()[0]
        finally:
            conn.close()

    def store_symbols(self, file_id: int, symbols: list[SymbolInfo]):
        """Store symbols for a specific file"""
        conn = sqlite3.connect(self.db_path)
        try:
            with conn:
                conn.execute("DELETE FROM symbols WHERE file_id = ?", (file_id,))
                for sym in symbols:
                    conn.execute(
                        """
                        INSERT INTO symbols (file_id, symbol_name, symbol_type, line_number, 
                                          signature, scope, declaration_position, parent_symbol, 
                                          context, param_count, has_body)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                        (
                            file_id,
                            sym.name,
                            sym.symbol_type,
                            sym.line_number,
                            sym.signature,
                            sym.scope,
                            sym.declaration_position,
                            sym.parent_symbol,
                            sym.context,
                            sym.param_count,
                            sym.has_body,
                        ),
                    )
        finally:
            conn.close()

    def clear_file_data(self, file_path: Path):
        """Remove all data related to a specific file (symbols, types, etc.)"""
        file_path_abs = str(file_path.resolve())
        conn = sqlite3.connect(self.db_path)
        try:
            with conn:
                # Find file_id first
                cursor = conn.execute(
                    "SELECT file_id FROM files WHERE file_path = ?", (file_path_abs,)
                )
                res = cursor.fetchone()
                if res:
                    file_id = res[0]
                    conn.execute("DELETE FROM symbols WHERE file_id = ?", (file_id,))
                    conn.execute("DELETE FROM type_definitions WHERE file_id = ?", (file_id,))
                    conn.execute("DELETE FROM symbol_references WHERE file_id = ?", (file_id,))
                    conn.execute("DELETE FROM message_usage WHERE file_id = ?", (file_id,))
                    # We don't delete the file entry itself, just its facts
        finally:
            conn.close()

    def get_file_hash(self, file_path: Path) -> str | None:
        """Get stored hash for a file"""
        file_path_abs = str(file_path.resolve())
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.execute(
                "SELECT file_hash FROM files WHERE file_path = ?", (file_path_abs,)
            )
            result = cursor.fetchone()
            return result[0] if result else None
        finally:
            conn.close()

    def get_transitive_includes(self, file_path: Path) -> list[int]:
        """Get IDs of all files included by this file (transitively)"""
        file_path_abs = str(file_path.resolve())
        conn = sqlite3.connect(self.db_path)
        try:
            # Recursive CTE to find all included files
            cursor = conn.execute(
                """
                WITH RECURSIVE transitive_includes(id) AS (
                    SELECT included_file_id 
                    FROM includes 
                    JOIN files ON includes.source_file_id = files.file_id
                    WHERE files.file_path = ? AND included_file_id IS NOT NULL
                    
                    UNION
                    
                    SELECT i.included_file_id
                    FROM includes i
                    JOIN transitive_includes ti ON i.source_file_id = ti.id
                    WHERE i.included_file_id IS NOT NULL
                )
                SELECT id FROM transitive_includes
                """,
                (file_path_abs,),
            )
            return [row[0] for row in cursor.fetchall()]
        finally:
            conn.close()

    def get_visible_symbols(self, file_path: Path) -> dict[str, list[dict]]:
        """Get all symbols visible to this file (own symbols + transitively included)"""
        file_path_abs = str(file_path.resolve())
        include_ids = self.get_transitive_includes(file_path)

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            # Get file_id of current file
            cursor = conn.execute("SELECT file_id FROM files WHERE file_path = ?", (file_path_abs,))
            res = cursor.fetchone()
            if not res:
                return {"functions": [], "variables": [], "constants": [], "event_handlers": []}
            file_id = res[0]

            all_ids = [file_id] + include_ids
            placeholders = ",".join("?" * len(all_ids))

            cursor = conn.execute(
                f"""
                SELECT symbol_name, symbol_type, scope, parent_symbol, context, param_count
                FROM symbols
                WHERE file_id IN ({placeholders})
                """,
                all_ids,
            )

            symbols = {"functions": [], "variables": [], "constants": [], "event_handlers": []}
            for row in cursor.fetchall():
                s_type = row["symbol_type"]
                s_data = dict(row)
                if s_type == "function":
                    symbols["functions"].append(s_data)
                elif s_type == "variable":
                    symbols["variables"].append(s_data)
                elif s_type == "constant":
                    symbols["constants"].append(s_data)
                elif s_type == "event_handler":
                    symbols["event_handlers"].append(s_data)

            return symbols
        finally:
            conn.close()

    def detect_circular_includes(self, file_path: Path) -> list[list[str]]:
        """Detect circular include dependencies starting from a file"""
        file_path_abs = str(file_path.resolve())
        conn = sqlite3.connect(self.db_path)
        try:
            # Query all includes to build a graph
            cursor = conn.execute("""
                SELECT f1.file_path, f2.file_path
                FROM includes i
                JOIN files f1 ON i.source_file_id = f1.file_id
                JOIN files f2 ON i.included_file_id = f2.file_id
            """)
            edges = cursor.fetchall()

            adj = {}
            for src, dst in edges:
                if src not in adj:
                    adj[src] = []
                adj[src].append(dst)

            cycles = []
            visited = set()
            path = []

            def find_cycles(u):
                visited.add(u)
                path.append(u)

                for v in adj.get(u, []):
                    if v in path:
                        idx = path.index(v)
                        cycles.append(path[idx:] + [v])
                    elif v not in visited:
                        find_cycles(v)

                path.pop()

            find_cycles(file_path_abs)
            return cycles
        finally:
            conn.close()
