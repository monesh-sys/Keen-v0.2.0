import unittest

from keen.compiler import ast_nodes as ast
from keen.compiler.errors import KeenSyntaxError
from keen.compiler.pipeline import parse_source


def first(src):
    return parse_source(src).body[0]


class ParserTests(unittest.TestCase):
    def test_var_and_const(self):
        n = first("let a = 1")
        self.assertIsInstance(n, ast.VarDecl)
        self.assertFalse(n.is_const)
        self.assertTrue(first("const b = 2").is_const)

    def test_precedence(self):
        e = first("1 + 2 * 3").expr
        self.assertEqual(e.op, "+")
        self.assertEqual(e.right.op, "*")

    def test_parentheses(self):
        e = first("(1 + 2) * 3").expr
        self.assertEqual(e.op, "*")
        self.assertEqual(e.left.op, "+")

    def test_unary_binds_tighter_than_mul(self):
        e = first("-2 * 3").expr
        self.assertEqual(e.op, "*")
        self.assertIsInstance(e.left, ast.Unary)

    def test_not_lower_than_equality(self):
        e = first("not a == b").expr
        self.assertIsInstance(e, ast.Unary)
        self.assertEqual(e.operand.op, "==")

    def test_function(self):
        f = first("fn add(a, b) { return a + b }")
        self.assertEqual((f.name, f.params), ("add", ["a", "b"]))
        self.assertIsInstance(f.body[0], ast.Return)

    def test_if_else_if_else(self):
        n = first("if a { x() } else if b { y() } else { z() }")
        self.assertIsInstance(n.else_body[0], ast.If)
        self.assertIsNotNone(n.else_body[0].else_body)

    def test_for_while(self):
        self.assertIsInstance(first("while x { break }"), ast.While)
        self.assertIsInstance(first("for i in range(3) { continue }"), ast.For)

    def test_assignment_forms(self):
        self.assertEqual(first("x += 1").op, "+=")
        self.assertIsInstance(first("a[0] = 5").target, ast.Index)

    def test_call_chain_and_index(self):
        e = first("f(1)(2)[0]").expr
        self.assertIsInstance(e, ast.Index)
        self.assertIsInstance(e.obj, ast.Call)

    def test_array_trailing_comma_multiline(self):
        e = first("[1,\n 2,\n]").expr
        self.assertEqual(len(e.elements), 2)

    def test_app_declaration(self):
        n = first('app "Demo"')
        self.assertIsInstance(n, ast.AppDecl)
        self.assertEqual(n.name, "Demo")

    def test_app_usable_as_variable_name(self):
        self.assertIsInstance(first("let app = 1"), ast.VarDecl)

    def test_semicolons(self):
        self.assertEqual(len(parse_source("let a = 1; let b = 2").body), 2)

    # --- errors
    def assertSyntax(self, src, text):
        with self.assertRaises(KeenSyntaxError) as cm:
            parse_source(src)
        self.assertIn(text, cm.exception.message)
        return cm.exception

    def test_missing_value(self):
        self.assertSyntax("let x", "must be given a value")

    def test_const_without_value(self):
        self.assertSyntax("const x", "Constant 'x' must be given a value")

    def test_missing_name(self):
        self.assertSyntax("let = 5", "Expected a name after 'let'")

    def test_two_statements_one_line(self):
        self.assertSyntax("let a = 1 let b = 2", "Expected end of statement")

    def test_unclosed_block(self):
        e = self.assertSyntax("fn f() {\n print(1)\n", "Unclosed block")
        self.assertEqual(e.line, 1)

    def test_unclosed_paren(self):
        self.assertSyntax("print(1", "Expected ')'")

    def test_assignment_in_condition_hint(self):
        e = self.assertSyntax("if x = 1 { }", "Expected '{' after if condition")
        self.assertIn("==", e.hint)

    def test_else_on_new_line(self):
        self.assertSyntax("if a { }\nelse { }", "'else' without a matching 'if'")

    def test_bad_assignment_target(self):
        self.assertSyntax("1 + 2 = 3", "Invalid assignment target")

    def test_missing_expression(self):
        self.assertSyntax("let x = ", "Incomplete expression")

    def test_error_position(self):
        e = self.assertSyntax("let x = 1\nlet = 2", "Expected a name")
        self.assertEqual((e.line, e.col), (2, 5))

    # --- 0.2.0 additions
    def test_symbolic_logic_parses_like_words(self):
        e = first("a && b || c").expr
        self.assertEqual((e.op, e.left.op), ("or", "and"))

    def test_bang_binds_tighter_than_equality(self):
        e = first("!a == b").expr
        self.assertEqual(e.op, "==")
        self.assertIsInstance(e.left, ast.Unary)

    def test_multiline_binary_expression(self):
        e = first("let x = 1 +\n    2 +\n    3").value
        self.assertEqual(e.op, "+")
        self.assertEqual(e.left.op, "+")

    def test_multiline_logic_and_assignment(self):
        self.assertIsInstance(first("let ok = a &&\n  b").value, ast.Logical)
        self.assertIsInstance(first("let x =\n  5").value, ast.Literal)

    def test_multiline_call_arguments(self):
        self.assertEqual(len(first("f(1,\n  2,\n  3)").expr.args), 3)

    def test_newline_before_operator_ends_statement(self):
        # A line that STARTS with an operator is a new statement, never a continuation.
        with self.assertRaises(KeenSyntaxError):
            parse_source("let a = 1\n+ 2")

    def test_nested_conditions(self):
        n = first("if a { if b { x() } else { y() } } else { z() }")
        self.assertIsInstance(n.then_body[0], ast.If)
        self.assertIsNotNone(n.then_body[0].else_body)

    def test_deeply_nested_blocks(self):
        src = "if a {\n" * 20 + "x()\n" + "}\n" * 20
        self.assertIsInstance(first(src), ast.If)

    def test_empty_block_and_empty_program(self):
        self.assertEqual(first("if a { }").then_body, [])
        self.assertEqual(parse_source("// only a comment\n\n").body, [])

    def test_comments_between_statements(self):
        src = "let a = 1 // one\n// whole line\nlet b = 2"
        self.assertEqual(len(parse_source(src).body), 2)


if __name__ == "__main__":
    unittest.main()
