import tree_sitter_c as tsc
from tree_sitter import Language, Parser


def dump_tree(node, source, indent=0):
    text = source[node.start_byte : node.end_byte].split("\n")[0][:30]
    print("  " * indent + f'{node.type} [{node.start_point} - {node.end_point}] "{text}"')
    for child in node.children:
        dump_tree(child, source, indent + 1)


with open("examples/EnumStructTest.can") as f:
    code = f.read()

language = Language(tsc.language())
parser = Parser(language)
tree = parser.parse(code.encode("utf8"))
dump_tree(tree.root_node, code)
