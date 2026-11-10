import unittest

from keen.compiler.pipeline import analyze, parse_source


def errors(src):
    return [e.message for e in analyze(parse_source(src))]


class SemanticTests(unittest.TestCase):
    def test_clean_program(self):
        self.assertEqual(errors("let a = 1\nfn f(x) { return x + a }\nprint(f(2))"), [])

    def test_undefined(self):
        self.assertEqual(errors("print(nope)"), ["Undefined variable 'nope'"])

    def test_use_before_declaration(self):
        self.assertEqual(len(errors("print(x)\nlet x = 1")), 1)

    def test_duplicate_declaration(self):
        self.assertIn("already declared", errors("let a = 1\nlet a = 2")[0])

    def test_duplicate_function(self):
        self.assertIn("already declared", errors("fn f() { }\nfn f() { }")[0])

    def test_duplicate_param(self):
        self.assertIn("Duplicate parameter", errors("fn f(a, a) { }")[0])

    def test_param_redeclared_in_body(self):
        self.assertIn("already declared", errors("fn f(a) { let a = 1 }")[0])

    def test_const_assign(self):
        self.assertIn("constant", errors("const a = 1\na += 1")[0])

    def test_builtin_assign(self):
        self.assertIn("constant", errors("print = 5")[0])

    def test_builtin_can_be_shadowed(self):
        self.assertEqual(errors("let len = 3\nprint(len)"), [])

    def test_break_outside_loop(self):
        self.assertIn("'break'", errors("break")[0])

    def test_continue_in_function_inside_loop_is_invalid(self):
        self.assertIn("'continue'", errors("while true { fn f() { continue } }")[0])

    def test_return_outside_function(self):
        self.assertIn("'return'", errors("return 1")[0])

    def test_recursion_and_mutual_recursion(self):
        self.assertEqual(errors("fn a(n) { return b(n) }\nfn b(n) { return a(n) }"), [])

    def test_loop_variable_scope(self):
        self.assertEqual(len(errors("for i in range(3) { }\nprint(i)")), 1)

    def test_multiple_errors_reported(self):
        self.assertEqual(len(errors("const x = 1\nx = 2\nprint(y)\nbreak")), 3)

    def test_closure_variable_visible(self):
        self.assertEqual(errors("fn mk() { let c = 0\nfn n() { c += 1 }\nreturn n }"), [])


if __name__ == "__main__":
    unittest.main()
