"""Debug script to see how tree-sitter-c parses struct/enum inside variables {} block"""

from pathlib import Path
from capl_tree_sitter import CAPLParser, ASTWalker

# Sample CAPL code with struct/enum inside variables
test_code = """
variables {
  int x;
  struct MyStruct {
    int a;
  };
  enum MyEnum { VAL };
}
"""

def print_tree(node, source, indent=0):
    """Recursively print the AST structure"""
    text = ASTWalker.get_text(node, source).replace('\n', '\\n')[:50]
    print(f"{'  ' * indent}{node.type}: {repr(text)}")
    for child in node.children:
        print_tree(child, source, indent + 1)

def analyze_ast(source_code):
    """Analyze how the variables block is parsed"""
    parser = CAPLParser()
    result = parser.parse_string(source_code)
    
    print("=== Full AST ===")
    print_tree(result.tree.root_node, result.source)
    
    print("\n=== Checking Nodes ===")
    # Look for struct_specifier and enum_specifier
    structs = ASTWalker.find_all_by_type(result.tree.root_node, "struct_specifier")
    enums = ASTWalker.find_all_by_type(result.tree.root_node, "enum_specifier")
    
    for node in structs + enums:
        node_text = ASTWalker.get_text(node, result.source).strip()[:30]
        print(f"\nNode {node.type}: {repr(node_text)}")
        
        # Check is_inside_variables_block logic manually
        current = node
        found = False
        while current:
            if current.type == "compound_statement":
                print(f"  Found compound_statement parent")
                if current.parent:
                    siblings = current.parent.children
                    try:
                        idx = siblings.index(current)
                        print(f"  Compound is sibling {idx}")
                        for i in range(idx):
                            sib_text = ASTWalker.get_text(siblings[i], result.source).strip()
                            print(f"    Previous sibling {i}: {repr(sib_text)}")
                            if "variables" in sib_text:
                                found = True
                                print("    MATCH FOUND!")
                    except ValueError:
                        pass
            current = current.parent
        print(f"  Final decision: {'INSIDE' if found else 'OUTSIDE'}")

if __name__ == "__main__":
    analyze_ast(test_code)
