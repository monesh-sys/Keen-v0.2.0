import unittest

from keen.compiler.errors import KeenSyntaxError
from keen.compiler.lexer import Lexer
from keen.compiler.tokens import TokenType as T


def types(src):
    return [t.type for t in Lexer(src).tokenize()]


class LexerTests(unittest.TestCase):
    def test_numbers(self):
        toks = Lexer("42 3.14 1_000").tokenize()
        self.assertEqual([t.value for t in toks[:3]], [42, 3.14, 1000])
        self.assertIsInstance(toks[0].value, int)
        self.assertIsInstance(toks[1].value, float)

    def test_strings_and_escapes(self):
        toks = Lexer(r'"a\nb" ' + "'it\\'s'").tokenize()
        self.assertEqual(toks[0].value, "a\nb")
        self.assertEqual(toks[1].value, "it's")

    def test_keywords_vs_identifiers(self):
        self.assertEqual(types("let letter")[:2], [T.LET, T.IDENT])

    def test_operators(self):
        self.assertEqual(
            types("== != <= >= += -= *= /= + - * / % = < >")[:-2],
            [T.EQ, T.NE, T.LE, T.GE, T.PLUS_ASSIGN, T.MINUS_ASSIGN, T.STAR_ASSIGN,
             T.SLASH_ASSIGN, T.PLUS, T.MINUS, T.STAR, T.SLASH, T.PERCENT, T.ASSIGN, T.LT, T.GT])

    def test_bang_is_not(self):
        self.assertEqual(types("!x")[:2], [T.NOT, T.IDENT])

    def test_comments_ignored(self):
        self.assertEqual(types("1 // hi there\n2")[:3], [T.NUMBER, T.NEWLINE, T.NUMBER])

    def test_newlines_collapsed_and_ignored_in_parens(self):
        self.assertEqual(types("f(1,\n2)\n\n\nx")[:-1].count(T.NEWLINE), 2)

    def test_line_and_column(self):
        toks = Lexer("let x\n  y").tokenize()
        y = [t for t in toks if t.text == "y"][0]
        self.assertEqual((y.line, y.col), (2, 3))

    def test_unterminated_string(self):
        with self.assertRaises(KeenSyntaxError) as cm:
            Lexer('"abc').tokenize()
        self.assertIn("Unterminated string", cm.exception.message)

    def test_unknown_character(self):
        with self.assertRaises(KeenSyntaxError) as cm:
            Lexer("let x = 5 @").tokenize()
        self.assertEqual(cm.exception.col, 11)

    def test_bad_escape(self):
        with self.assertRaises(KeenSyntaxError):
            Lexer(r'"\q"').tokenize()

    def test_number_followed_by_letters(self):
        with self.assertRaises(KeenSyntaxError):
            Lexer("12abc").tokenize()

    def test_logical_symbols(self):
        self.assertEqual(types("a && b || !c")[:-2],
                         [T.IDENT, T.AND, T.IDENT, T.OR, T.NOT, T.IDENT])

    def test_double_char_ops_do_not_swallow_neighbours(self):
        self.assertEqual(types("a<=b")[:3], [T.IDENT, T.LE, T.IDENT])
        self.assertEqual(types("a!=b")[:3], [T.IDENT, T.NE, T.IDENT])

    def test_unicode_escape(self):
        self.assertEqual(Lexer(r'"\u00e9\u0041"').tokenize()[0].value, "\u00e9A")

    def test_crlf_line_endings(self):
        toks = Lexer("let a = 1\r\nlet b = 2\r\n").tokenize()
        b = [t for t in toks if t.text == "b"][0]
        self.assertEqual((b.line, b.col), (2, 5))

    def test_comment_at_end_of_file_without_newline(self):
        self.assertEqual(types("1 // done")[:2], [T.NUMBER, T.NEWLINE])

    def test_slash_is_not_a_comment_start(self):
        self.assertEqual(types("4 / 2")[:3], [T.NUMBER, T.SLASH, T.NUMBER])

    def test_empty_source(self):
        self.assertEqual(types(""), [T.EOF])

    def test_empty_string_literal(self):
        self.assertEqual(Lexer('""').tokenize()[0].value, "")

    def test_unterminated_at_newline(self):
        with self.assertRaises(KeenSyntaxError):
            Lexer('"abc\ndef"').tokenize()


if __name__ == "__main__":
    unittest.main()
