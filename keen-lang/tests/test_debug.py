"""Debugging system: tracing, variable inspection, error call stacks."""

import io
import unittest

from keen.compiler.errors import KeenRuntimeError
from keen.compiler.interpreter import Interpreter
from keen.compiler.pipeline import run_source
from keen.runtime.debug import Tracer

PROGRAM = """let total = 0
const rate = 2
fn double(n) {
    return n * rate
}
for i in range(1, 3) {
    total += double(i)
}
print("total =", total)
"""


def traced(source, inspect=False):
    out, events = io.StringIO(), []
    tracer = Tracer(source, events.append, inspect_variables=inspect)
    interp = Interpreter(write=out.write, tracer=tracer)
    try:
        run_source(source, interpreter=interp)
        error = None
    except KeenRuntimeError as e:
        error = e
    return out.getvalue(), events, interp, tracer, error


class TraceTests(unittest.TestCase):
    def test_statements_are_traced_with_line_numbers_and_source(self):
        _, events, *_ = traced(PROGRAM)
        self.assertTrue(events[0].startswith("[trace] step 1"))
        self.assertIn("line 1", events[0])
        self.assertTrue(events[0].endswith("let total = 0"))
        self.assertTrue(any("line 9" in e and 'print("total =", total)' in e for e in events))

    def test_function_calls_and_returns_are_traced(self):
        _, events, *_ = traced(PROGRAM)
        self.assertIn("-> call double(1)", "\n".join(events))
        self.assertIn("<- double returned 2", "\n".join(events))
        self.assertIn("-> call double(2)", "\n".join(events))

    def test_statements_inside_functions_are_indented(self):
        _, events, *_ = traced(PROGRAM)
        inner = [e for e in events if "return n * rate" in e][0]
        outer = [e for e in events if "let total = 0" in e][0]
        self.assertGreater(inner.index("return n"), outer.index("let total"))

    def test_function_declaration_is_not_traced_as_a_step(self):
        _, events, *_ = traced(PROGRAM)
        self.assertFalse(any(e.endswith("fn double(n) {") for e in events))

    def test_step_count(self):
        *_, tracer, _ = traced(PROGRAM)
        # let, const, for, 2x(total +=, return), print = 8
        self.assertEqual(tracer.steps, 8)

    def test_program_output_is_unchanged_by_tracing(self):
        plain = io.StringIO()
        run_source(PROGRAM, write=plain.write)
        out, *_ = traced(PROGRAM, inspect=True)
        self.assertEqual(out, plain.getvalue())
        self.assertEqual(out, "total = 6\n")

    def test_trace_lines_never_contain_program_output(self):
        _, events, *_ = traced(PROGRAM)
        self.assertFalse(any(e == "total = 6" for e in events))


class InspectionTests(unittest.TestCase):
    def test_variable_changes_reported_in_debug_mode(self):
        _, events, *_ = traced(PROGRAM, inspect=True)
        text = "\n".join(events)
        self.assertIn("[debug]   total = 0   (integer)", text)
        self.assertIn("[debug]   total = 2   (integer)", text)
        self.assertIn("[debug]   total = 6   (integer)", text)

    def test_no_inspection_without_debug(self):
        _, events, *_ = traced(PROGRAM, inspect=False)
        self.assertFalse(any(e.startswith("[debug]") for e in events))

    def test_array_element_assignment(self):
        _, events, *_ = traced("let a = [1, 2]\na[1] = 9", inspect=True)
        self.assertIn("[debug]   a[1] = 9   (integer)", events)

    def test_dump_variables(self):
        _, events, interp, tracer, _ = traced(PROGRAM)
        events.clear()
        tracer.dump_variables(interp.globals, "Variables at exit")
        text = "\n".join(events)
        self.assertIn("total = 6   (integer)", text)
        self.assertIn("rate = 2   (constant)", text)
        self.assertIn("double = <fn double>   (function)", text)
        self.assertNotIn("print", text)  # built-ins are not listed

    def test_dump_when_empty(self):
        _, events, interp, tracer, _ = traced("print(1)")
        events.clear()
        tracer.dump_variables(interp.globals)
        self.assertIn("(none)", events[-1])


class ErrorTracingTests(unittest.TestCase):
    SRC = "let x = 5\nfn bad(n) {\n    return n / 0\n}\nfn outer() {\n    return bad(x)\n}\nouter()\n"

    def test_error_event_and_call_stack(self):
        out, events, interp, _, error = traced(self.SRC)
        self.assertIsNotNone(error)
        self.assertTrue(any(e.startswith("[trace] error raised: Division by zero") for e in events))
        self.assertEqual([f[0] for f in error.stack], ["outer", "bad"])

    def test_state_is_inspectable_after_error(self):
        *_, interp, _, error = traced(self.SRC)
        self.assertEqual(interp.globals.vars["x"], 5)
        self.assertEqual(interp.call_stack, [])  # fully unwound

    def test_depth_limit_still_reports_with_tracer(self):
        out, events = io.StringIO(), []
        interp = Interpreter(write=out.write, tracer=Tracer("", events.append), max_call_depth=20)
        with self.assertRaises(KeenRuntimeError):
            run_source("fn f() { return f() }\nf()", interpreter=interp)


if __name__ == "__main__":
    unittest.main()
