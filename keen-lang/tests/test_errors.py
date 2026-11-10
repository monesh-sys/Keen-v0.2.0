"""Every error category required by the 0.2.0 spec, with exact positions and suggestions."""

import unittest

from keen.compiler.errors import (
    KeenError, KeenLexError, KeenRuntimeError, KeenSyntaxError, SemanticErrors,
)
from keen.compiler.pipeline import run_source
from tests.helpers import run


def catch(src):
    try:
        run(src)
    except SemanticErrors as e:
        return e.errors[0]
    except KeenError as e:
        return e
    raise AssertionError("expected an error")


class LexerErrorTests(unittest.TestCase):
    def test_unexpected_character(self):
        e = catch("let a = 1\nlet b = 2 @ 3")
        self.assertIsInstance(e, KeenLexError)
        self.assertEqual((e.line, e.col), (2, 11))
        self.assertEqual(e.kind, "Lexer Error")

    def test_unterminated_string_position_is_string_start(self):
        e = catch('let a = 1\nprint("oops)')
        self.assertIsInstance(e, KeenLexError)
        self.assertEqual((e.line, e.col), (2, 7))
        self.assertIn("closing", e.hint)

    def test_single_ampersand_and_pipe_suggest_double(self):
        e = catch("print(true & false)")
        self.assertIn("Invalid operator '&'", e.message)
        self.assertIn("&&", e.hint)
        self.assertIn("||", catch("print(true | false)").hint)

    def test_bad_number(self):
        self.assertIsInstance(catch("let x = 12abc"), KeenLexError)

    def test_bad_unicode_escape(self):
        self.assertIn("unicode", catch(r'print("\u12")').message.lower())

    def test_lexer_error_is_a_syntax_error(self):
        self.assertTrue(issubclass(KeenLexError, KeenSyntaxError))


class ParserErrorTests(unittest.TestCase):
    def test_missing_closing_paren_points_at_opening(self):
        e = catch("print(1, 2")
        self.assertIsInstance(e, KeenSyntaxError)
        self.assertIn("Expected ')'", e.message)
        self.assertIn("line 1, column 6", e.hint)

    def test_missing_closing_brace(self):
        e = catch("fn f() {\n    print(1)\n")
        self.assertIn("Unclosed block", e.message)
        self.assertEqual((e.line, e.col), (1, 8))

    def test_stray_closing_brace_and_paren(self):
        e = catch("print(1)\n}")
        self.assertEqual((e.line, e.col, e.message), (2, 1, "Unexpected '}'"))
        self.assertEqual(catch("let x = 1)").message, "Expected end of statement but found ')'")

    def test_unexpected_token(self):
        e = catch("let x = 1 2")
        self.assertIn("Expected end of statement but found '2'", e.message)
        self.assertEqual((e.line, e.col), (1, 11))

    def test_incomplete_expression(self):
        for src, op in (("let x = 5 +", "+"), ("let y = 2 *\n", "*"), ("print(1 &&)", "&&"),
                        ("let z =", "=")):
            with self.subTest(src=src):
                e = catch(src)
                self.assertIn(f"Incomplete expression: expected a value after '{op}'", e.message)
                self.assertTrue(e.hint)

    def test_incomplete_expression_position_is_the_operator(self):
        e = catch("let a = 1\nlet x = 5 +")
        self.assertEqual((e.line, e.col), (2, 11))

    def test_missing_condition(self):
        self.assertIn("Missing condition after 'if'", catch("if { }").message)
        self.assertIn("Missing condition after 'while'", catch("while { }").message)

    def test_missing_brace_after_condition(self):
        e = catch("if x > 1 print(x)")
        self.assertIn("Expected '{' after if condition", e.message)

    def test_missing_function_body_brace(self):
        self.assertIn("start the body of function 'f'", catch("fn f()\nprint(1)").message)

    def test_block_validation_else_misplaced(self):
        self.assertIn("'else' without a matching 'if'", catch("let x = 1\nif x == 1 { }\nelse { }").message)

    def test_equals_in_condition_suggests_double_equals(self):
        self.assertIn("==", catch("let x = 1\nif x = 1 { }").hint)


class SemanticAndRuntimeErrorTests(unittest.TestCase):
    def test_undefined_variable_with_suggestion(self):
        e = catch("let total = 1\nprint(totl)")
        self.assertEqual((e.kind, e.line, e.col), ("Semantic Error", 2, 7))
        self.assertIn("Undefined variable 'totl'", e.message)
        self.assertIn("Did you mean 'total'?", e.hint)

    def test_undefined_variable_at_runtime_is_runtime_error(self):
        from keen.compiler.interpreter import Interpreter
        from keen.compiler.pipeline import parse_source
        with self.assertRaises(KeenRuntimeError) as cm:
            Interpreter(write=lambda s: None).run(parse_source("print(nothing)"))
        self.assertEqual(cm.exception.kind, "Runtime Error")

    def test_duplicate_declaration(self):
        e = catch("let a = 1\nlet a = 2")
        self.assertIn("'a' is already declared in this scope", e.message)
        self.assertEqual(e.line, 2)

    def test_constant_reassignment(self):
        e = catch("const pi = 3\npi = 4")
        self.assertIn("Cannot assign to constant 'pi'", e.message)
        self.assertIn("let", e.hint)

    def test_type_mismatch_has_suggestion(self):
        e = catch('print("Age: " + 17)')
        self.assertIsInstance(e, KeenRuntimeError)
        self.assertEqual((e.line, e.col), (1, 15))
        self.assertIn("str(", e.hint)

    def test_division_by_zero_position(self):
        e = catch("let a = 10\nlet b = 0\nprint(a / b)")
        self.assertEqual((e.line, e.col), (3, 9))

    def test_call_stack_recorded(self):
        src = "fn inner() { return 1 / 0 }\nfn outer() { return inner() }\nouter()"
        e = catch(src)
        self.assertEqual([f[0] for f in e.stack], ["outer", "inner"])
        self.assertEqual(e.stack[0][1], 3)

    def test_top_level_error_has_empty_stack(self):
        self.assertEqual(catch("print(1 / 0)").stack, [])


class FormatTests(unittest.TestCase):
    def test_report_layout(self):
        src = "let a = 1\nprint(a / 0)"
        text = catch(src).format(src, "example.keen")
        lines = text.splitlines()
        self.assertEqual(lines[:6], [
            "KEEN Error:", "  Type: Runtime Error", "  File: example.keen",
            "  Line: 2", "  Column: 9", "  Message: Division by zero"])
        self.assertIn("  2 | print(a / 0)", text)
        self.assertIn("^", text)

    def test_suggestion_line(self):
        src = "let total = 1\nprint(totl)"
        self.assertIn("  Suggestion: Did you mean 'total'?", catch(src).format(src, "x.keen"))

    def test_call_stack_in_report(self):
        src = "fn f() { return 1 / 0 }\nf()"
        text = catch(src).format(src, "x.keen")
        self.assertIn("Call stack (most recent call last):", text)
        self.assertIn("f() called at line 2, column 2", text)

    def test_multiple_semantic_errors_summary(self):
        with self.assertRaises(SemanticErrors) as cm:
            run("const a = 1\na = 2\nprint(zzz)")
        text = cm.exception.format("", "x.keen")
        self.assertEqual(text.count("KEEN Error:"), 2)
        self.assertTrue(text.endswith("2 errors found. Nothing was run."))

    def test_format_without_source_or_position(self):
        text = KeenRuntimeError("boom").format()
        self.assertEqual(text, "KEEN Error:\n  Type: Runtime Error\n  File: <input>\n  Message: boom")


if __name__ == "__main__":
    unittest.main()
