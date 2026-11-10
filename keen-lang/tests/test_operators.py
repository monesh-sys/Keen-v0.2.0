"""Operator behaviour: precedence, associativity, comparison, logic (KEEN 0.2.0)."""

import unittest

from keen.compiler.errors import KeenRuntimeError
from tests.helpers import run


def ev(expr):
    return run(f"print({expr})").strip()


class ArithmeticTests(unittest.TestCase):
    def test_precedence_examples_from_spec(self):
        self.assertEqual(ev("10 + 5 * 2"), "20")
        self.assertEqual(ev("(10 + 5) * 2"), "30")
        self.assertEqual(ev("2 + 3 * 4 - 1"), "13")
        self.assertEqual(ev("-2 * -3"), "6")

    def test_left_associativity(self):
        self.assertEqual(ev("10 - 3 - 2"), "5")
        self.assertEqual(ev("100 / 10 / 2"), "5.0")
        self.assertEqual(ev("20 % 7 % 4"), "2")
        self.assertEqual(ev("2 - 3 - 4"), "-5")

    def test_all_arithmetic(self):
        self.assertEqual(run("print(7 + 3, 7 - 3, 7 * 3, 7 / 2, 7 % 3)"), "10 4 21 3.5 1\n")

    def test_float_arithmetic(self):
        self.assertEqual(ev("0.5 + 0.25"), "0.75")


class ComparisonTests(unittest.TestCase):
    def test_numbers(self):
        self.assertEqual(run("print(10 > 5, 10 < 5, 10 >= 10, 10 <= 9, 10 == 10, 10 != 10)"),
                         "true false true false true false\n")

    def test_mixed_int_float(self):
        self.assertEqual(run("print(1 == 1.0, 2 > 1.5)"), "true true\n")

    def test_strings(self):
        self.assertEqual(run('print("a" == "a", "a" != "b", "a" < "b")'), "true true true\n")

    def test_different_types_are_not_equal(self):
        self.assertEqual(run('print(1 == "1", null == false, 0 == false)'), "false false false\n")

    def test_comparison_precedence_vs_arithmetic(self):
        self.assertEqual(ev("1 + 2 > 2 * 1"), "true")

    def test_chained_comparison_is_a_type_error(self):
        with self.assertRaises(KeenRuntimeError) as cm:
            run("print(1 < 2 < 3)")
        self.assertIn("Cannot compare boolean with integer", cm.exception.message)
        self.assertIn("&&", cm.exception.hint)


class LogicalTests(unittest.TestCase):
    def test_spec_examples(self):
        self.assertEqual(run("print(true && false)\nprint(true || false)\nprint(!false)"),
                         "false\ntrue\ntrue\n")

    def test_word_operators_still_work(self):
        self.assertEqual(run("print(true and false, true or false, not true)"), "false true false\n")

    def test_results_are_always_boolean(self):
        out = run('print(1 && "a", 0 || "", "x" || 0, null && 5, type(1 && 2), type("" || "y"))')
        self.assertEqual(out, "true false true false boolean boolean\n")

    def test_short_circuit(self):
        src = 'fn boom() { print("boom"); return true }\nprint(false && boom(), true || boom())'
        self.assertEqual(run(src), "false true\n")

    def test_not_is_right_associative(self):
        self.assertEqual(ev("!!true"), "true")
        self.assertEqual(ev("!!!true"), "false")

    def test_precedence_not_and_or(self):
        self.assertEqual(ev("true || false && false"), "true")      # && binds tighter than ||
        self.assertEqual(ev("(true || false) && false"), "false")
        self.assertEqual(ev("!true || true"), "true")               # ! binds tighter than ||
        self.assertEqual(ev("!1 == 2"), "false")                    # (!1) == 2 -> false == 2 -> false

    def test_comparison_inside_logic(self):
        self.assertEqual(ev("5 > 3 && 2 > 1 || false"), "true")


class AssignmentTests(unittest.TestCase):
    def test_assignment(self):
        self.assertEqual(run("let x = 1\nx = x + 1\nprint(x)"), "2\n")

    def test_assignment_returns_nothing_usable_in_expression(self):
        from keen.compiler.errors import KeenSyntaxError
        with self.assertRaises(KeenSyntaxError):
            run("let x = 1\nprint(x = 2)")


class InvalidOperatorTests(unittest.TestCase):
    def check(self, src, text):
        with self.assertRaises(KeenRuntimeError) as cm:
            run(src)
        self.assertIn(text, cm.exception.message)
        return cm.exception

    def test_string_minus_number(self):
        e = self.check('print("a" - 1)', "Operator '-' needs two numbers, got string and integer")
        self.assertIn("int()", e.hint)

    def test_bool_arithmetic(self):
        self.check("print(true + 1)", "Cannot add boolean and integer")
        self.check("print(true * 2)", "needs two numbers")

    def test_null_arithmetic(self):
        self.check("let n = null\nprint(n + 1)", "Cannot add null and integer")

    def test_negate_string(self):
        self.check('print(-"x")', "Cannot negate a value of type string")

    def test_compare_mixed(self):
        self.check('print("a" > 1)', "Cannot compare string with integer")
        self.check("print(null < 1)", "Cannot compare null with integer")

    def test_zero_division_forms(self):
        self.check("print(1 / 0)", "Division by zero")
        self.check("print(1.5 / 0.0)", "Division by zero")
        self.check("print(5 % 0)", "Modulo by zero")


if __name__ == "__main__":
    unittest.main()
