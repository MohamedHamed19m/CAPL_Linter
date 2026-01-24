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
        texts = [c.text.decode("utf-8") for c in comments]
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
        header = next(
            v for v in comment_map.values() if "// Header" in v.comment_node.text.decode("utf-8")
        )
        assert header.attachment_type == "header"
        assert header.target_node.type == "function_definition"

        inline = next(
            v for v in comment_map.values() if "// Inline" in v.comment_node.text.decode("utf-8")
        )
        assert inline.attachment_type == "inline"

        section = next(
            v for v in comment_map.values() if "//===" in v.comment_node.text.decode("utf-8")
        )
        assert section.attachment_type == "section"

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

    def test_inline_comment_alignment(self):
        source = """
        int x; // short
        int very_long_variable; // longer
        """
        config = FormatterConfig(align_inline_comments=True, inline_comment_column=40)
        engine = FormatterEngine(config)
        result = engine.format_string(source)

        lines = [l for l in result.source.splitlines() if "//" in l]
        assert len(lines) == 2
        col1 = lines[0].find("//")
        col2 = lines[1].find("//")
        assert col1 == col2
        assert col1 >= 30  # At least some padding

    def test_comment_reflow_long_line(self):
        # A long comment with spaces that should be wrapped
        long_comment = "// " + "word " * 30
        source = f"void test() {{\n  {long_comment}\n}}"

        config = FormatterConfig(line_length=80, reflow_comments=True)
        engine = FormatterEngine(config)
        result = engine.format_string(source)

        # Should be wrapped into multiple lines
        lines = [l for l in result.source.splitlines() if "// word" in l]
        assert len(lines) >= 2
        for line in lines:
            assert len(line) <= 80

    def test_comment_reflow_single_long_word(self):
        # A single word longer than line_length should NOT be wrapped
        long_word = "A" * 120
        source = f"// {long_word}"

        config = FormatterConfig(line_length=100, reflow_comments=True)
        engine = FormatterEngine(config)
        result = engine.format_string(source)

        # Should remain a single line
        lines = [l for l in result.source.splitlines() if l.strip()]
        assert len(lines) == 1
        assert long_word in lines[0]

    def test_doxygen_preservation(self):
        source = """
        /**
         * @param x The value
         * This line is very very very very very very very very very very very very very very very very very very long
         */
        """
        config = FormatterConfig(line_length=50, reflow_comments=True)
        engine = FormatterEngine(config)
        result = engine.format_string(source)

        assert "This line is very very" in result.source

    def test_ascii_art_preservation(self):
        source = """
        /*
         * +---------+
         * | Diagram |
         * +---------+
         * This line is very very very very very very very very very very very very very very very very very very long
         */
        """
        config = FormatterConfig(line_length=50, reflow_comments=True)
        engine = FormatterEngine(config)
        result = engine.format_string(source)

        assert "+---------+" in result.source
        assert "This line is very very" in result.source
