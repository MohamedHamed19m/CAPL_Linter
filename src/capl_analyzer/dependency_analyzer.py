"""
CAPL Include Dependency Analyzer using Tree-sitter
Builds a dependency graph of #include relationships for aic.db
"""

import sqlite3
from pathlib import Path
from typing import Dict, List, Set, Optional
from dataclasses import dataclass
import tree_sitter_c as tsc
from tree_sitter import Language, Parser, Node, Tree, Query, QueryCursor


@dataclass
class IncludeInfo:
    """Information about an include directive"""
    including_file: str  # File that contains the #include
    included_file: str   # File being included
    line_number: int
    is_resolved: bool    # Whether we found the actual file
    resolved_path: Optional[str] = None


class CAPLDependencyAnalyzer:
    def __init__(self, db_path: str, search_paths: List[str] = None):
        """
        Initialize the dependency analyzer
        
        Args:
            db_path: Path to aic.db SQLite database
            search_paths: List of directories to search for includes
        """
        self.db_path = db_path
        self.search_paths = search_paths or []
        
        # Tree-sitter v0.25+ API
        self.language = Language(tsc.language())
        self.parser = Parser(self.language)
        
        self._init_database()
    
    def _init_database(self):
        """Create tables for dependency tracking"""
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
                CREATE TABLE IF NOT EXISTS symbols (
                    symbol_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_id INTEGER NOT NULL,
                    symbol_name TEXT NOT NULL,
                    symbol_type TEXT,  -- 'function', 'variable', 'message', 'signal'
                    line_number INTEGER,
                    FOREIGN KEY (file_id) REFERENCES files(file_id)
                )
            """)
            
            # Indexes for fast lookups
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_includes_source 
                ON includes(source_file_id)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_includes_target 
                ON includes(included_file_id)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_symbols_name 
                ON symbols(symbol_name)
            """)
            
            conn.commit()
    
    def extract_includes(self, file_path: str) -> List[IncludeInfo]:
        """
        Extract all #include directives from a CAPL file using tree-sitter
        
        Args:
            file_path: Path to the CAPL file
            
        Returns:
            List of IncludeInfo objects
        """
        with open(file_path, 'rb') as f:
            source_code = f.read()
        
        tree = self.parser.parse(source_code)
        root = tree.root_node
        
        includes = []
        
        # Query for preprocessor includes (v0.25+ API with QueryCursor)
        query = Query(self.language, """
            (preproc_include
              path: [(string_literal) (system_lib_string)] @path) @include
        """)
        
        # Use QueryCursor to execute the query (query is passed to constructor)
        cursor = QueryCursor(query)
        cursor.set_byte_range(0, len(source_code))
        matches = cursor.matches(root)
        
        for match in matches:
            pattern_index, captures_dict = match
            # Look for captures named "include"
            if "include" in captures_dict:
                for node in captures_dict["include"]:
                    include_info = self._process_include_node(
                        node, source_code.decode('utf8'), file_path
                    )
                    if include_info:
                        includes.append(include_info)
        
        return includes
    
    def _process_include_node(self, node: Node, source: str, 
                               source_file: str) -> Optional[IncludeInfo]:
        """Process a single include node and resolve the path"""
        # Find the path node (child of preproc_include)
        path_node = None
        for child in node.children:
            if child.type in ('string_literal', 'system_lib_string'):
                path_node = child
                break
        
        if not path_node:
            return None
        
        # Extract the include path (remove quotes or <>)
        include_text = source[path_node.start_byte:path_node.end_byte]
        include_path = include_text.strip('"<>')
        
        # Resolve the actual file location
        resolved_path = self._resolve_include_path(include_path, source_file)
        
        return IncludeInfo(
            including_file=source_file,
            included_file=include_path,
            line_number=node.start_point[0] + 1,  # 1-indexed
            is_resolved=resolved_path is not None,
            resolved_path=resolved_path
        )
    
    def _resolve_include_path(self, include_path: str, 
                              source_file: str) -> Optional[str]:
        """
        Resolve an include path to an actual file
        
        Search order:
        1. Relative to the source file
        2. In configured search paths
        3. Standard CAPL include paths (if configured)
        """
        # Try relative to source file first
        source_dir = Path(source_file).parent
        candidate = source_dir / include_path
        if candidate.exists():
            return str(candidate.resolve())
        
        # Try search paths
        for search_path in self.search_paths:
            candidate = Path(search_path) / include_path
            if candidate.exists():
                return str(candidate.resolve())
        
        return None
    
    def analyze_file(self, file_path: str) -> int:
        """
        Analyze a file and store its dependencies in the database
        
        Returns:
            file_id of the analyzed file
        """
        file_path = str(Path(file_path).resolve())
        
        with sqlite3.connect(self.db_path) as conn:
            # Register or update the file
            cursor = conn.execute("""
                INSERT INTO files (file_path, parse_success)
                VALUES (?, 1)
                ON CONFLICT(file_path) DO UPDATE SET
                    last_parsed = CURRENT_TIMESTAMP,
                    parse_success = 1
                RETURNING file_id
            """, (file_path,))
            
            file_id = cursor.fetchone()[0]
            
            # Clear old includes for this file
            conn.execute("""
                DELETE FROM includes WHERE source_file_id = ?
            """, (file_id,))
            
            # Extract and store includes
            includes = self.extract_includes(file_path)
            
            for inc in includes:
                included_file_id = None
                
                if inc.is_resolved:
                    # Register the included file
                    cursor = conn.execute("""
                        INSERT INTO files (file_path, parse_success)
                        VALUES (?, NULL)
                        ON CONFLICT(file_path) DO UPDATE SET
                            last_parsed = last_parsed
                        RETURNING file_id
                    """, (inc.resolved_path,))
                    included_file_id = cursor.fetchone()[0]
                
                # Store the include relationship
                conn.execute("""
                    INSERT INTO includes 
                    (source_file_id, included_file_id, include_path, 
                     line_number, is_resolved)
                    VALUES (?, ?, ?, ?, ?)
                """, (file_id, included_file_id, inc.included_file,
                      inc.line_number, inc.is_resolved))
            
            conn.commit()
            
        return file_id
    
    def analyze_directory(self, directory: str, pattern: str = "*.can"):
        """
        Recursively analyze all CAPL files in a directory
        
        Args:
            directory: Root directory to scan
            pattern: File pattern to match (default: *.can)
        """
        root_path = Path(directory)
        
        for file_path in root_path.rglob(pattern):
            try:
                print(f"Analyzing: {file_path}")
                self.analyze_file(str(file_path))
            except Exception as e:
                print(f"Error analyzing {file_path}: {e}")
    
    def get_dependencies(self, file_path: str, 
                        recursive: bool = False) -> List[str]:
        """
        Get all files that a given file depends on (includes)
        
        Args:
            file_path: The source file
            recursive: If True, get transitive dependencies
            
        Returns:
            List of file paths that are dependencies
        """
        file_path = str(Path(file_path).resolve())
        
        with sqlite3.connect(self.db_path) as conn:
            if not recursive:
                cursor = conn.execute("""
                    SELECT f2.file_path
                    FROM files f1
                    JOIN includes i ON f1.file_id = i.source_file_id
                    JOIN files f2 ON i.included_file_id = f2.file_id
                    WHERE f1.file_path = ? AND i.is_resolved = 1
                """, (file_path,))
            else:
                # Recursive CTE for transitive dependencies
                cursor = conn.execute("""
                    WITH RECURSIVE deps(file_id, file_path, depth) AS (
                        SELECT file_id, file_path, 0
                        FROM files
                        WHERE file_path = ?
                        
                        UNION
                        
                        SELECT f.file_id, f.file_path, deps.depth + 1
                        FROM deps
                        JOIN includes i ON deps.file_id = i.source_file_id
                        JOIN files f ON i.included_file_id = f.file_id
                        WHERE i.is_resolved = 1 AND deps.depth < 10
                    )
                    SELECT DISTINCT file_path FROM deps WHERE depth > 0
                """, (file_path,))
            
            return [row[0] for row in cursor.fetchall()]
    
    def get_dependents(self, file_path: str) -> List[str]:
        """
        Get all files that depend on (include) the given file
        
        Args:
            file_path: The file to find dependents for
            
        Returns:
            List of file paths that include this file
        """
        file_path = str(Path(file_path).resolve())
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT f1.file_path
                FROM files f1
                JOIN includes i ON f1.file_id = i.source_file_id
                JOIN files f2 ON i.included_file_id = f2.file_id
                WHERE f2.file_path = ? AND i.is_resolved = 1
            """, (file_path,))
            
            return [row[0] for row in cursor.fetchall()]
    
    def find_circular_dependencies(self) -> List[List[str]]:
        """
        Detect circular include dependencies
        
        Returns:
            List of circular dependency chains
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                WITH RECURSIVE deps(source_id, target_id, path) AS (
                    SELECT source_file_id, included_file_id, 
                           source_file_id || ',' || included_file_id
                    FROM includes
                    WHERE is_resolved = 1
                    
                    UNION
                    
                    SELECT deps.source_id, i.included_file_id,
                           deps.path || ',' || i.included_file_id
                    FROM deps
                    JOIN includes i ON deps.target_id = i.source_file_id
                    WHERE i.is_resolved = 1
                      AND instr(deps.path, ',' || i.included_file_id || ',') = 0
                      AND length(deps.path) < 1000
                )
                SELECT path FROM deps
                WHERE source_id = target_id
            """)
            
            # Convert file IDs back to paths
            cycles = []
            for (path_str,) in cursor.fetchall():
                file_ids = path_str.split(',')
                file_paths = self._ids_to_paths(conn, file_ids)
                cycles.append(file_paths)
            
            return cycles
    
    def _ids_to_paths(self, conn, file_ids: List[str]) -> List[str]:
        """Convert file IDs to file paths"""
        placeholders = ','.join('?' * len(file_ids))
        cursor = conn.execute(f"""
            SELECT file_path FROM files WHERE file_id IN ({placeholders})
        """, file_ids)
        
        id_to_path = {row[0]: row[0] for row in cursor.fetchall()}
        return [id_to_path.get(fid, f"<unknown:{fid}>") for fid in file_ids]
    
    def generate_dependency_graph(self, output_file: str = "dependencies.dot"):
        """
        Generate a GraphViz DOT file of the dependency graph
        
        Args:
            output_file: Path to output .dot file
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT f1.file_path, f2.file_path
                FROM includes i
                JOIN files f1 ON i.source_file_id = f1.file_id
                JOIN files f2 ON i.included_file_id = f2.file_id
                WHERE i.is_resolved = 1
            """)
            
            edges = cursor.fetchall()
        
        with open(output_file, 'w') as f:
            f.write("digraph Dependencies {\n")
            f.write("  rankdir=LR;\n")
            f.write("  node [shape=box];\n\n")
            
            for source, target in edges:
                source_name = Path(source).name
                target_name = Path(target).name
                f.write(f'  "{source_name}" -> "{target_name}";\n')
            
            f.write("}\n")
        
        print(f"Dependency graph written to {output_file}")
        print(f"Generate image with: dot -Tpng {output_file} -o dependencies.png")


# Example usage
if __name__ == "__main__":
    # Initialize analyzer
    analyzer = CAPLDependencyAnalyzer(
        db_path="aic.db",
        search_paths=[
            "/path/to/capl/includes",
            "/path/to/project/common"
        ]
    )
    
    # Analyze a single file
    file_id = analyzer.analyze_file("AdvancedNode.can")
    
    # Or analyze an entire directory
    analyzer.analyze_directory("/path/to/capl/project")
    
    # Query dependencies
    deps = analyzer.get_dependencies("AdvancedNode.can", recursive=True)
    print(f"Dependencies: {deps}")
    
    # Find who depends on this file
    dependents = analyzer.get_dependents("CommonDefinitions.cin")
    print(f"Dependents: {dependents}")
    
    # Check for circular dependencies
    cycles = analyzer.find_circular_dependencies()
    if cycles:
        print("Warning: Circular dependencies detected!")
        for cycle in cycles:
            print(" -> ".join(cycle))
    
    # Generate visualization
    analyzer.generate_dependency_graph("project_deps.dot")