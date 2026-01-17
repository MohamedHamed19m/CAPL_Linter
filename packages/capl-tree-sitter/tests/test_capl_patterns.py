import pytest
from capl_tree_sitter import CAPLParser, CAPLPatterns, ASTWalker


def test_is_event_handler():
    parser = CAPLParser()
    result = parser.parse_string("void on start() {}")

    func_nodes = ASTWalker.find_all_by_type(result.tree.root_node, "function_definition")
    assert len(func_nodes) == 1

    is_event = CAPLPatterns.is_event_handler(func_nodes[0], result.source)
    assert is_event is True


def test_not_event_handler():
    parser = CAPLParser()
    result = parser.parse_string("void foo() {}")

    func_nodes = ASTWalker.find_all_by_type(result.tree.root_node, "function_definition")
    is_event = CAPLPatterns.is_event_handler(func_nodes[0], result.source)
    assert is_event is False


def test_has_extern_keyword():
    parser = CAPLParser()
    result = parser.parse_string("extern int x;")

    decl_nodes = ASTWalker.find_all_by_type(result.tree.root_node, "declaration")
    has_extern = CAPLPatterns.has_extern_keyword(decl_nodes[0], result.source)
    assert has_extern is True


def test_is_function_declaration():
    parser = CAPLParser()
    result = parser.parse_string("void foo();")

    decl_nodes = ASTWalker.find_all_by_type(result.tree.root_node, "declaration")
    is_decl = CAPLPatterns.is_function_declaration(decl_nodes[0])
    assert is_decl is True


def test_get_function_name():
    parser = CAPLParser()
    result = parser.parse_string("void myFunction() {}")

    func_nodes = ASTWalker.find_all_by_type(result.tree.root_node, "function_definition")
    name = CAPLPatterns.get_function_name(func_nodes[0], result.source)
    assert name == "myFunction"


def test_is_timer_declaration():
    parser = CAPLParser()
    result = parser.parse_string("timer t1;")

    decl_nodes = ASTWalker.find_all_by_type(result.tree.root_node, "declaration")
    is_timer = CAPLPatterns.is_timer_declaration(decl_nodes[0], result.source)
    assert is_timer is True


def test_ast_walker_get_text():
    parser = CAPLParser()
    result = parser.parse_string("void foo() {}")

    func_nodes = ASTWalker.find_all_by_type(result.tree.root_node, "function_definition")
    text = ASTWalker.get_text(func_nodes[0], result.source)
    assert "foo" in text


def test_is_inside_variables_block():
    parser = CAPLParser()
    result = parser.parse_string("variables { int x; }")

    decl_nodes = ASTWalker.find_all_by_type(result.tree.root_node, "declaration")
    assert len(decl_nodes) == 1

    in_vars = CAPLPatterns.is_inside_variables_block(decl_nodes[0], result.source)
    assert in_vars is True


def test_not_inside_variables_block():
    parser = CAPLParser()
    result = parser.parse_string("void foo() { int x; }")

    decl_nodes = ASTWalker.find_all_by_type(result.tree.root_node, "declaration")
    in_vars = CAPLPatterns.is_inside_variables_block(decl_nodes[0], result.source)
    assert in_vars is False
