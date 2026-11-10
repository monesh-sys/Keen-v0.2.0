import unittest

from keen.compiler.errors import KeenRuntimeError, SemanticErrors
from tests.helpers import run


class ValueTests(unittest.TestCase):
    def test_variables_and_constants(self):
        self.assertEqual(run('let a = 5\nconst b = "x"\nprint(a, b)'), "5 x\n")

    def test_data_types_display(self):
        self.assertEqual(run('print(1, 2.5, "s", true, false, null, [1, "a"])'),
                         '1 2.5 s true false null [1, "a"]\n')

    def test_type_function(self):
        out = run('print(type(1), type(1.5), type("a"), type(true), type(null), type([]), type(print))')
        self.assertEqual(out, "integer float string boolean null array function\n")

    def test_bool_is_not_integer(self):
        self.assertEqual(run("print(true == 1, 1 == 1.0, [1,2] == [1,2], null == null)"),
                         "false true true true\n")


class ArithmeticTests(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(run("print(10 + 20, 10 - 4, 3 * 4, 7 % 3)"), "30 6 12 1\n")

    def test_precedence(self):
        self.assertEqual(run("print(2 + 3 * 4, (2 + 3) * 4, -2 * 3)"), "14 20 -6\n")

    def test_division_is_float(self):
        self.assertEqual(run("print(7 / 2, 10 / 2)"), "3.5 5.0\n")

    def test_float(self):
        self.assertEqual(run("print(1.5 + 2)"), "3.5\n")

    def test_big_integers(self):
        self.assertEqual(run("print(2 * 1000000000000 * 1000000000000)"), "2000000000000000000000000\n")

    def test_compound_assignment(self):
        self.assertEqual(run("let x = 10\nx += 5\nx -= 3\nx *= 2\nx /= 4\nprint(x)"), "6.0\n")

    def test_division_by_zero(self):
        with self.assertRaises(KeenRuntimeError) as cm:
            run("print(1 / 0)")
        self.assertEqual(cm.exception.message, "Division by zero")
        self.assertEqual(cm.exception.line, 1)

    def test_modulo_by_zero(self):
        with self.assertRaises(KeenRuntimeError):
            run("print(1 % 0)")


class StringTests(unittest.TestCase):
    def test_concat(self):
        self.assertEqual(run('print("a" + "b")'), "ab\n")

    def test_string_plus_number_error_has_hint(self):
        with self.assertRaises(KeenRuntimeError) as cm:
            run('print("n: " + 5)')
        self.assertIn("Cannot add string and integer", cm.exception.message)
        self.assertIn("str(", cm.exception.hint)

    def test_str_conversion(self):
        self.assertEqual(run('print("n: " + str(5) + str(true))'), "n: 5true\n")

    def test_index_and_len(self):
        self.assertEqual(run('print("hello"[1], len("hello"))'), "e 5\n")

    def test_string_comparison(self):
        self.assertEqual(run('print("a" < "b", "b" <= "a")'), "true false\n")


class ConditionTests(unittest.TestCase):
    def test_if_else(self):
        src = 'let age = %d\nif age >= 18 { print("Adult") } else { print("Minor") }'
        self.assertEqual(run(src % 20), "Adult\n")
        self.assertEqual(run(src % 10), "Minor\n")

    def test_else_if_chain(self):
        src = "fn f(n) {\n if n < 0 { return \"neg\" } else if n == 0 { return \"zero\" } else { return \"pos\" }\n}\nprint(f(-1), f(0), f(1))"
        self.assertEqual(run(src), "neg zero pos\n")

    def test_logical_short_circuit(self):
        src = "fn boom() { print(\"boom\"); return true }\nprint(false and boom(), true or boom())"
        self.assertEqual(run(src), "false true\n")

    def test_truthiness(self):
        self.assertEqual(run('print(not 0, not "", not [], not null, not 1, not "a")'),
                         "true true true true false false\n")

    def test_block_scoping(self):
        with self.assertRaises(SemanticErrors):
            run("if true { let inner = 1 }\nprint(inner)")

    def test_shadowing_in_inner_scope(self):
        self.assertEqual(run("let x = 1\nif true { let x = 2\nprint(x) }\nprint(x)"), "2\n1\n")

    def test_comparison_type_error(self):
        with self.assertRaises(KeenRuntimeError):
            run('print(1 < "a")')


class LoopTests(unittest.TestCase):
    def test_while(self):
        self.assertEqual(run("let i = 0\nwhile i < 3 { print(i)\ni += 1 }"), "0\n1\n2\n")

    def test_for_range_array_string(self):
        self.assertEqual(run("for i in range(3) { print(i) }"), "0\n1\n2\n")
        self.assertEqual(run("for x in [1, 2] { print(x) }"), "1\n2\n")
        self.assertEqual(run('for c in "ab" { print(c) }'), "a\nb\n")

    def test_break_continue(self):
        src = "for i in range(10) {\n if i == 1 { continue }\n if i == 4 { break }\n print(i)\n}"
        self.assertEqual(run(src), "0\n2\n3\n")

    def test_nested_break_only_inner(self):
        src = "for i in range(2) { for j in range(5) { if j == 1 { break }\nprint(i, j) } }"
        self.assertEqual(run(src), "0 0\n1 0\n")

    def test_range_step(self):
        self.assertEqual(run("print(range(10, 0, -3), range(2, 5))"), "[10, 7, 4, 1] [2, 3, 4]\n")

    def test_for_non_iterable(self):
        with self.assertRaises(KeenRuntimeError) as cm:
            run("for i in 5 { }")
        self.assertIn("range()", cm.exception.hint)


class FunctionTests(unittest.TestCase):
    def test_add(self):
        self.assertEqual(run("fn add(a, b) { return a + b }\nprint(add(10, 20))"), "30\n")

    def test_no_return_is_null(self):
        self.assertEqual(run("fn f() { }\nprint(f())"), "null\n")

    def test_recursion(self):
        self.assertEqual(run("fn fact(n) { if n <= 1 { return 1 }\nreturn n * fact(n - 1) }\nprint(fact(10))"),
                         "3628800\n")

    def test_hoisting(self):
        self.assertEqual(run("print(later())\nfn later() { return 7 }"), "7\n")

    def test_function_uses_later_global(self):
        self.assertEqual(run("fn f() { return x }\nlet x = 3\nprint(f())"), "3\n")

    def test_closure_counter(self):
        src = ("fn mk() { let c = 0\nfn nxt() { c += 1\nreturn c }\nreturn nxt }\n"
               "let a = mk()\nlet b = mk()\na()\na()\nprint(a(), b())")
        self.assertEqual(run(src), "3 1\n")

    def test_functions_are_values(self):
        self.assertEqual(run("fn sq(x) { return x * x }\nlet f = sq\nprint(f(4))"), "16\n")

    def test_return_exits_loop(self):
        self.assertEqual(run("fn f() { for i in range(10) { if i == 3 { return i } } }\nprint(f())"), "3\n")

    def test_wrong_arg_count(self):
        with self.assertRaises(KeenRuntimeError) as cm:
            run("fn f(a, b) { return a }\nf(1)")
        self.assertIn("expects 2 argument(s) but got 1", cm.exception.message)

    def test_call_non_function(self):
        with self.assertRaises(KeenRuntimeError) as cm:
            run("let x = 5\nx()")
        self.assertIn("'x' is not a function", cm.exception.message)

    def test_runaway_recursion_is_caught(self):
        with self.assertRaises(KeenRuntimeError) as cm:
            run("fn f() { return f() }\nf()", max_call_depth=50)
        self.assertIn("Maximum call depth", cm.exception.message)


class ArrayTests(unittest.TestCase):
    def test_index_and_assign(self):
        self.assertEqual(run("let a = [1, 2, 3]\na[0] = 9\na[1] += 5\nprint(a, a[-1])"), "[9, 7, 3] 3\n")

    def test_push_len_concat(self):
        self.assertEqual(run("let a = [1]\npush(a, 2)\nprint(len(a), a + [3])"), "2 [1, 2, 3]\n")

    def test_out_of_range(self):
        with self.assertRaises(KeenRuntimeError) as cm:
            run("let a = [1]\nprint(a[5])")
        self.assertIn("out of range", cm.exception.message)

    def test_non_integer_index(self):
        with self.assertRaises(KeenRuntimeError):
            run('print([1]["a"])')

    def test_string_immutable(self):
        with self.assertRaises(KeenRuntimeError):
            run('let s = "abc"\ns[0] = "x"')


class ErrorTests(unittest.TestCase):
    def test_undefined_variable_with_suggestion(self):
        with self.assertRaises(SemanticErrors) as cm:
            run("let counter = 1\nprint(countr)")
        e = cm.exception.errors[0]
        self.assertIn("Undefined variable 'countr'", e.message)
        self.assertIn("counter", e.hint)
        self.assertEqual((e.line, e.col), (2, 7))

    def test_const_reassignment(self):
        with self.assertRaises(SemanticErrors) as cm:
            run("const x = 1\nx = 2")
        self.assertIn("Cannot assign to constant 'x'", cm.exception.errors[0].message)

    def test_runtime_const_protection_without_checker(self):
        from keen.compiler.interpreter import Interpreter
        from keen.compiler.pipeline import parse_source
        with self.assertRaises(KeenRuntimeError):
            Interpreter(write=lambda s: None).run(parse_source("const x = 1\nx = 2"))

    def test_builtin_errors_positioned(self):
        with self.assertRaises(KeenRuntimeError) as cm:
            run('print(1)\nprint(int("abc"))')
        self.assertEqual(cm.exception.line, 2)
        self.assertIn('cannot convert the string "abc"', cm.exception.message)

    def test_error_formatting(self):
        with self.assertRaises(KeenRuntimeError) as cm:
            run("let a = 1\nprint(a / 0)")
        text = cm.exception.format("let a = 1\nprint(a / 0)", "t.keen")
        self.assertIn("KEEN Error:", text)
        self.assertIn("Type: Runtime Error", text)
        self.assertIn("File: t.keen", text)
        self.assertIn("Line: 2", text)
        self.assertIn("Column: 9", text)
        self.assertIn("Message: Division by zero", text)
        self.assertIn("2 | print(a / 0)", text)

    def test_output_before_runtime_error_is_kept(self):
        import io
        from keen.compiler.pipeline import run_source
        out = io.StringIO()
        with self.assertRaises(KeenRuntimeError):
            run_source('print("before")\nprint(1 / 0)', write=out.write)
        self.assertEqual(out.getvalue(), "before\n")


class BuiltinTests(unittest.TestCase):
    def test_int_float(self):
        self.assertEqual(run('print(int("42"), int(3.9), float("2.5"), float(2))'), "42 3 2.5 2.0\n")

    def test_input(self):
        out = run('let n = input("name? ")\nprint("hi " + n)', read_line=lambda: "Ada")
        self.assertEqual(out, "name? hi Ada\n")

    def test_len_error(self):
        with self.assertRaises(KeenRuntimeError):
            run("len(5)")

    def test_print_no_args(self):
        self.assertEqual(run("print()"), "\n")


if __name__ == "__main__":
    unittest.main()
