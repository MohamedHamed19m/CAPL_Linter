from capl_tree_sitter.parser import CAPLParser
from capl_tree_sitter.queries import CAPLQueryHelper


def test_basic_parse():
    parser = CAPLParser()
    code = """
    variables {
      int x = 5;
    }
    on start {
      write("Hello");
    }
    """
    result = parser.parse_string(code)
    assert result.tree.root_node.type == "translation_unit"
    # We expect some errors because we are using tree-sitter-c for CAPL
    assert len(result.errors) > 0


def test_parse_with_error():
    parser = CAPLParser()
    code = "variables { int x = ; }"  # Syntax error
    result = parser.parse_string(code)
    assert len(result.errors) > 0


def test_query():
    parser = CAPLParser()
    helper = CAPLQueryHelper()
    code = """
    variables {
      int myVar = 10;
    }
    """
    result = parser.parse_string(code)

    # Query for variable declarations
    # In tree-sitter-c, variables in variables{} are often field_declaration or declaration
    # depending on how the grammar treats the block.
    # CAPL uses C grammar, and variables{} is not standard C, but tree-sitter-c often
    # handles it as a labeled_statement or similar if not customized.
    # Actually, tree-sitter-c sees "variables {" as a function or block if it doesn't know it.

    query = "(declaration) @decl"
    matches = helper.query(query, result.tree.root_node)
    assert len(matches) > 0
