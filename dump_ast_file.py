import sys
import tree_sitter_c as tsc
from tree_sitter import Language, Parser
from pathlib import Path


def dump_tree(node, source, indent=0):
    print("  " * indent + f"{node.type} [{node.start_point} - {node.end_point}]")
    if node.type == "ERROR":
        print("  " * (indent + 1) + f"ERROR TEXT: {source[node.start_byte : node.end_byte]}")
    for child in node.children:
        dump_tree(child, source, indent + 1)


if len(sys.argv) < 2:
    print("Usage: python dump_ast_file.py <file>")
    sys.exit(1)

file_path = Path(sys.argv[1])
code = file_path.read_text(encoding="utf-8")

language = Language(tsc.language())
parser = Parser(language)
tree = parser.parse(code.encode("utf8"))
dump_tree(tree.root_node, code)
