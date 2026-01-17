from capl_tree_sitter import ASTWalker, CAPLParser, CAPLPatterns


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


def test_valid_struct_parameter():
    """Test that regular struct parameter is allowed."""
    parser = CAPLParser()

    code = """
    void MyFunc(struct Data data_obj) {
    }
    """
    result = parser.parse_string(code)
    funcs = ASTWalker.find_all_by_type(result.tree.root_node, "function_definition")

    assert len(funcs) == 1
    violations = CAPLPatterns.has_forbidden_pointer_parameter(funcs[0], result.source)
    assert len(violations) == 0  # No errors - this is correct


def test_forbidden_pointer_parameter():
    """Test that struct pointer parameter is detected as error."""
    parser = CAPLParser()

    code = """
    void MyFunc2(struct Data* data_ptr) {
    }
    """
    result = parser.parse_string(code)
    funcs = ASTWalker.find_all_by_type(result.tree.root_node, "function_definition")

    assert len(funcs) == 1
    violations = CAPLPatterns.has_forbidden_pointer_parameter(funcs[0], result.source)
    assert len(violations) == 1  # Should detect forbidden pointer
    assert violations[0]["type"] == "forbidden_pointer_param"


def test_valid_reference_parameter():
    """Test that primitive reference parameter is allowed."""
    parser = CAPLParser()

    code = """
    void MyFunc5(byte &byte_ptr) {
    }
    """
    result = parser.parse_string(code)
    funcs = ASTWalker.find_all_by_type(result.tree.root_node, "function_definition")

    assert len(funcs) == 1
    violations = CAPLPatterns.has_forbidden_pointer_parameter(funcs[0], result.source)
    # Reference on byte is OK, should have no violations
    assert len(violations) == 0


def test_ethernetpacket_pointer_allowed():
    """Test that ethernetpacket* is allowed (required type)."""
    parser = CAPLParser()

    code = """
    void MyFunc6(ethernetpacket * packet) {
    }
    """
    result = parser.parse_string(code)
    funcs = ASTWalker.find_all_by_type(result.tree.root_node, "function_definition")

    assert len(funcs) == 1
    violations = CAPLPatterns.has_forbidden_pointer_parameter(funcs[0], result.source)
    assert len(violations) == 0  # ethernetpacket REQUIRES pointer - OK


def test_someip_message_pointer_allowed():
    """Test that someipMessage* is allowed (required type)."""
    parser = CAPLParser()

    code = """
    void MyFunc7(someipMessage * msg) {
    }
    """
    result = parser.parse_string(code)
    funcs = ASTWalker.find_all_by_type(result.tree.root_node, "function_definition")

    assert len(funcs) == 1
    violations = CAPLPatterns.has_forbidden_pointer_parameter(funcs[0], result.source)
    assert len(violations) == 0  # someipMessage REQUIRES pointer - OK


def test_arrow_operator_detection():
    """Test that arrow operator usage is detected."""
    parser = CAPLParser()

    code = """
    void MyFunc3(struct Data data_ptr) {
        if (data_ptr != NULL) {
            write("Data ID: %d", data_ptr->id);
        }
    }
    """
    result = parser.parse_string(code)
    funcs = ASTWalker.find_all_by_type(result.tree.root_node, "function_definition")

    assert len(funcs) == 1
    violations = CAPLPatterns.has_arrow_operator_usage(funcs[0], result.source)
    assert len(violations) > 0  # Should detect arrow operator
    assert violations[0]["type"] == "arrow_operator_usage"


def test_dot_operator_allowed():
    """Test that dot operator is correctly allowed."""
    parser = CAPLParser()

    code = """
    void MyFunc4(struct Data data_obj) {
        write("Data ID: %d", data_obj.id);
    }
    """
    result = parser.parse_string(code)
    funcs = ASTWalker.find_all_by_type(result.tree.root_node, "function_definition")

    assert len(funcs) == 1
    violations = CAPLPatterns.has_arrow_operator_usage(funcs[0], result.source)
    assert len(violations) == 0  # Dot operator is fine


def test_comprehensive_pointer_analysis():
    """Test complete analysis with all examples."""
    parser = CAPLParser()

    code = """
    variables {
        struct Data {
            int id;
            dword name;
        };
    }
    
    void MyFunc(struct Data data_obj) { }
    void MyFunc2(struct Data* data_ptr) { }
    
    void MyFunc3(struct Data data_ptr) {
        if (data_ptr != NULL) {
            write("Data ID: %d", data_ptr->id);
        }
    }
    
    void MyFunc4(struct Data data_obj) {
        write("Data ID: %d", data_obj.id);
    }
    
    void MyFunc5(byte &byte_ptr) {
        byte_ptr = 10;
    }
    
    void MyFunc6(ethernetpacket * packet) {
        packet.udp.IsAvailable();
    }
    
    void MyFunc7(someipMessage * msg) {
        msg.ClientID = 100;
    }
    """

    result = parser.parse_string(code)
    funcs = ASTWalker.find_all_by_type(result.tree.root_node, "function_definition")

    # Analyze each function
    results = {}
    for func in funcs:
        name = CAPLPatterns.get_function_name(func, result.source)
        if name and name.startswith("MyFunc"):
            analysis = CAPLPatterns.analyze_pointer_usage(func, result.source)
            results[name] = analysis

    # Verify expected results
    assert results["MyFunc"]["has_errors"] is False  # ✅ struct Data data_obj - OK
    assert results["MyFunc2"]["has_errors"] is True  # ❌ struct Data* - ERROR
    assert results["MyFunc3"]["has_errors"] is True  # ❌ data_ptr->id - ERROR
    assert results["MyFunc4"]["has_errors"] is False  # ✅ data_obj.id - OK
    assert results["MyFunc5"]["has_errors"] is False  # ✅ byte &ref - OK
    assert results["MyFunc6"]["has_errors"] is False  # ✅ ethernetpacket* - OK (required)
    assert results["MyFunc7"]["has_errors"] is False  # ✅ someipMessage* - OK (required)
