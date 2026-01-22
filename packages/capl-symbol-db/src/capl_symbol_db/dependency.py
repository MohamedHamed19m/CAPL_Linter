import sqlite3
from pathlib import Path

from capl_tree_sitter.parser import CAPLParser
from capl_tree_sitter.queries import CAPLQueryHelper

from .database import SymbolDatabase


class DependencyAnalyzer:
    """Analyzes #include dependencies in CAPL files"""

    def __init__(self, db: SymbolDatabase, search_paths: list[str] = None):
        self.db = db
        self.search_paths = search_paths or []
        self.parser = CAPLParser()
        self.query_helper = CAPLQueryHelper()

    def analyze_file(self, file_path: Path) -> int:
        """Extract and store dependencies for a file"""
        file_path = file_path.resolve()

        result = self.parser.parse_file(file_path)
        root = result.tree.root_node
        source = result.source

        # Register file in DB (using existing DB instance)
        with open(file_path, "rb") as f:
            file_id = self.db.store_file(file_path, f.read())

        # Extract includes
        query = """
            (preproc_include
              path: [(string_literal) (system_lib_string)] @path) @include
        """
        matches = self.query_helper.query(query, root)

        # Pre-resolve and pre-store files to avoid locking issues
        include_data = []
        for m in matches:
            if "path" in m.captures:
                path_node = m.captures["path"]
                include_text = source[path_node.start_byte : path_node.end_byte]
                include_path = include_text.strip('"<>')
                resolved_path = self._resolve_path(include_path, file_path)

                included_file_id = None
                if resolved_path:
                    included_file_id = self.db.get_or_create_file_id(resolved_path)

                include_data.append(
                    {
                        "path_node": path_node,
                        "include_path": include_path,
                        "included_file_id": included_file_id,
                        "is_resolved": resolved_path is not None,
                    }
                )

        conn = sqlite3.connect(self.db.db_path)
        try:
            with conn:
                conn.execute("DELETE FROM includes WHERE source_file_id = ?", (file_id,))

                for data in include_data:
                    conn.execute(
                        """
                        INSERT INTO includes (source_file_id, included_file_id, include_path, 
                                           line_number, is_resolved)
                        VALUES (?, ?, ?, ?, ?)
                    """,
                        (
                            file_id,
                            data["included_file_id"],
                            data["include_path"],
                            data["path_node"].start_point[0] + 1,
                            data["is_resolved"],
                        ),
                    )
        finally:
            conn.close()

        return file_id

    def _resolve_path(self, include_path: str, source_file: Path) -> Path | None:
        # Relative to source
        candidate = source_file.parent / include_path
        if candidate.exists():
            return candidate.resolve()

        # Search paths
        for p in self.search_paths:
            candidate = Path(p) / include_path
            if candidate.exists():
                return candidate.resolve()

        return None
