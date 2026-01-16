
import tree_sitter_c as tsc
from tree_sitter import Language, Parser

def dump_tree(node, source, indent=0):
    print("  " * indent + f"{node.type} [{node.start_point} - {node.end_point}]")
    if node.type == "ERROR":
        print("  " * (indent + 1) + f"ERROR TEXT: {source[node.start_byte:node.end_byte]}")
    for child in node.children:
        dump_tree(child, source, indent + 1)

code = """
variables {
  int gVar;
}

on start {
  int lVar;
  write("Hi");
}
"""

language = Language(tsc.language())
parser = Parser(language)
tree = parser.parse(code.encode("utf8"))
dump_tree(tree.root_node, code)
