import pytest
from capl_formatter.engine import FormatterEngine
from capl_formatter.models import FormatterConfig
from capl_tree_sitter.parser import CAPLParser

class TestCommentLogic:
    def test_find_all_comments(self):
        source = """
        // Header
        void test() {
            int x; // Inline
            /* Block */
        }
        """
        config = FormatterConfig()
        engine = FormatterEngine(config)
        parser = CAPLParser()
        res = parser.parse_string(source)
        
        comments = engine._find_all_comments(res.tree)
        assert len(comments) == 3
        texts = [c.text.decode('utf-8') for c in comments]
        assert "// Header" in texts
        assert "// Inline" in texts
        assert "/* Block */" in texts

    def test_classify_comment(self):
        source = """
        // Header
        void test() {
            int x; // Inline
        }
        //===
        """
        config = FormatterConfig()
        engine = FormatterEngine(config)
        parser = CAPLParser()
        res = parser.parse_string(source)
        
        comment_map = engine._build_comment_attachment_map(source, res.tree)
        
        # Verify
        header = next(v for v in comment_map.values() if "// Header" in v.comment_node.text.decode('utf-8'))
        assert header.attachment_type == 'header'
        assert header.target_node.type == 'function_definition'
        
        inline = next(v for v in comment_map.values() if "// Inline" in v.comment_node.text.decode('utf-8'))
        assert inline.attachment_type == 'inline'
        
        section = next(v for v in comment_map.values() if "//===" in v.comment_node.text.decode('utf-8'))
        assert section.attachment_type == 'section'

    def test_header_comment_proximity(self):
        source = """
        // Header
        
        void func() {}
        """
        config = FormatterConfig(preserve_comment_proximity=True)
        engine = FormatterEngine(config)
        result = engine.format_string(source)
        
        # Expectation: No blank line between header comment and function
        # Note: indentation might apply
        assert "// Header\n  void func" in result.source or "// Header\nvoid func" in result.source

    def test_block_expansion_with_inline_comment(self):
        source = "void test() { int x; } // Comment"
        config = FormatterConfig()
        engine = FormatterEngine(config)
        engine.add_default_rules()
        result = engine.format_string(source)
        assert "// Comment" in result.source

    def test_inline_comment_preservation(self):
        source = "int x; int y; // Comment"
        config = FormatterConfig()
        engine = FormatterEngine(config)
        engine.add_default_rules()
        result = engine.format_string(source)
        
        assert "// Comment" in result.source
        lines = result.source.splitlines()
        y_line = next(l for l in lines if "int y;" in l)
        assert "// Comment" in y_line

    def test_statement_split_with_intervening_comment(self):
        source = "int x; /* c */ int y;"
        config = FormatterConfig()
        engine = FormatterEngine(config)
        engine.add_default_rules()
        result = engine.format_string(source)
        
        # It should split. 
        # Ideally: int x; /* c */ \n int y;
        assert "int x; /* c */\n" in result.source or "/* c */\n" in result.source
        assert "int y;" in result.source
