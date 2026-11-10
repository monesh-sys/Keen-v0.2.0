import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def keen(*args):
    return subprocess.run([sys.executable, "-m", "keen", *args], cwd=ROOT,
                          capture_output=True, text=True, timeout=60)


class CliTests(unittest.TestCase):
    def test_hello_exact_output(self):
        r = keen("run", "examples/hello.keen")
        self.assertEqual(r.returncode, 0)
        self.assertEqual(r.stdout, "Hello from KEEN!\nCreated by MoneshSys Technologies.\n")

    def test_version(self):
        expected = "KEEN Programming Language\nVersion 0.2.0\nDeveloped by Monesh K.K."
        for args in (["version"], ["--version"], ["-V"]):
            r = keen(*args)
            self.assertEqual(r.returncode, 0)
            self.assertEqual(r.stdout.strip().replace("\r\n", "\n"), expected)

    def test_help(self):
        for args in (["help"], []):
            r = keen(*args)
            self.assertEqual(r.returncode, 0)
            self.assertIn("keen run <file.keen>", r.stdout)

    def test_missing_file(self):
        r = keen("run", "does_not_exist.keen")
        self.assertEqual(r.returncode, 2)
        self.assertIn("cannot find file", r.stderr)

    def test_unknown_command(self):
        self.assertNotEqual(keen("frobnicate").returncode, 0)

    def test_check_ok_and_failure(self):
        self.assertEqual(keen("check", "examples/hello.keen").returncode, 0)
        r = keen("check", "examples/errors_demo.keen")
        self.assertEqual(r.returncode, 1)
        self.assertIn("Cannot assign to constant 'limit'", r.stderr)
        self.assertIn("Did you mean 'limit'?", r.stderr)
        self.assertIn("3 errors found", r.stderr)

    def _tmp(self, text):
        f = tempfile.NamedTemporaryFile("w", suffix=".keen", delete=False, encoding="utf-8")
        f.write(text)
        f.close()
        self.addCleanup(os.unlink, f.name)
        return f.name

    def test_syntax_error_reported_with_caret(self):
        r = keen("run", self._tmp("let x = \n"))
        self.assertEqual(r.returncode, 1)
        self.assertIn("Type: Syntax Error", r.stderr)
        self.assertIn("^", r.stderr)

    def test_runtime_error_exit_code_and_partial_output(self):
        r = keen("run", self._tmp('print("ok")\nprint(1 / 0)\n'))
        self.assertEqual(r.returncode, 1)
        self.assertEqual(r.stdout, "ok\n")
        self.assertIn("Division by zero", r.stderr)

    def test_deep_recursion_works_in_cli(self):
        r = keen("run", self._tmp("fn s(n) { if n == 0 { return 0 }\nreturn n + s(n - 1) }\nprint(s(900))\n"))
        self.assertEqual(r.stdout.strip(), "405450")

    def test_runaway_recursion_clean_error(self):
        r = keen("run", self._tmp("fn f() { return f() }\nf()\n"))
        self.assertEqual(r.returncode, 1)
        self.assertIn("Maximum call depth", r.stderr)


class CliOptionTests(unittest.TestCase):
    def _tmp(self, data, suffix=".keen"):
        f = tempfile.NamedTemporaryFile("wb", suffix=suffix, delete=False)
        f.write(data if isinstance(data, bytes) else data.encode("utf-8"))
        f.close()
        self.addCleanup(os.unlink, f.name)
        return f.name

    PROGRAM = "let x = 2\nfn sq(n) {\n    return n * n\n}\nprint(sq(x))\n"

    def test_help_shows_banner_and_all_commands(self):
        for args in (["--help"], ["-h"]):
            r = keen(*args)
            self.assertEqual(r.returncode, 0)
            self.assertIn("KEEN Programming Language", r.stdout)
            self.assertIn("Developed by Monesh K.K.", r.stdout)
            for text in ("keen run <file.keen>", "--trace", "--debug", "--verbose", "keen check"):
                self.assertIn(text, r.stdout)

    def test_version_flag_exact(self):
        r = keen("--version")
        self.assertEqual(r.stdout.splitlines(),
                         ["KEEN Programming Language", "Version 0.2.0", "Developed by Monesh K.K."])
        self.assertEqual(r.stderr, "")

    def test_run_plain_has_no_diagnostics(self):
        r = keen("run", self._tmp(self.PROGRAM))
        self.assertEqual((r.returncode, r.stdout.strip(), r.stderr), (0, "4", ""))

    def test_trace_goes_to_stderr_only(self):
        path = self._tmp(self.PROGRAM)
        plain = keen("run", path)
        r = keen("run", path, "--trace")
        self.assertEqual(r.returncode, 0)
        self.assertEqual(r.stdout, plain.stdout)           # program output untouched
        self.assertIn("[trace] step 1", r.stderr)
        self.assertIn("-> call sq(2)", r.stderr)
        self.assertIn("<- sq returned 4", r.stderr)
        self.assertNotIn("[debug]", r.stderr)               # no variable inspection in --trace

    def test_debug_adds_variable_inspection_and_dump(self):
        path = self._tmp(self.PROGRAM)
        r = keen("run", path, "--debug")
        self.assertEqual(r.stdout.strip(), "4")
        self.assertIn("[debug]   x = 2   (integer)", r.stderr)
        self.assertIn("Variables at exit (globals):", r.stderr)
        self.assertIn("[trace] finished: 3 statement(s) executed", r.stderr)

    def test_verbose_shows_stages(self):
        r = keen("run", self._tmp(self.PROGRAM), "--verbose")
        self.assertEqual(r.stdout.strip(), "4")
        for text in ("[verbose] lexer:", "[verbose] parser:", "semantic analysis: OK",
                     "[verbose] finished in", "exit code 0"):
            self.assertIn(text, r.stderr)

    def test_debug_on_runtime_error_shows_stack_and_variables(self):
        path = self._tmp("let n = 0\nfn bad() {\n    return 1 / n\n}\nprint(\"start\")\nbad()\n")
        r = keen("run", path, "--debug")
        self.assertEqual(r.returncode, 1)
        self.assertEqual(r.stdout.strip(), "start")
        self.assertIn("KEEN Error:", r.stderr)
        self.assertIn("Type: Runtime Error", r.stderr)
        self.assertIn("Line: 3", r.stderr)
        self.assertIn("Call stack (most recent call last):", r.stderr)
        self.assertIn("bad() called at line 6", r.stderr)
        self.assertIn("[debug]   n = 0", r.stderr)

    def test_error_report_format_for_all_error_types(self):
        cases = {
            "Lexer Error": "let a = 1 @ 2\n",
            "Syntax Error": "let a = (1 + 2\n",
            "Semantic Error": "print(missing)\n",
            "Runtime Error": "print(1 / 0)\n",
        }
        for kind, src in cases.items():
            with self.subTest(kind=kind):
                path = self._tmp(src)
                r = keen("run", path)
                self.assertEqual(r.returncode, 1)
                self.assertTrue(r.stderr.startswith("KEEN Error:"))
                self.assertIn(f"  Type: {kind}", r.stderr)
                self.assertIn("  File: ", r.stderr)
                self.assertIn("  Line: 1", r.stderr)
                self.assertIn("  Column: ", r.stderr)
                self.assertIn("  Message: ", r.stderr)

    def test_check_reports_without_running(self):
        path = self._tmp('print("should not print")\nprint(oops)\n')
        r = keen("check", path)
        self.assertEqual(r.returncode, 1)
        self.assertEqual(r.stdout, "")
        self.assertIn("Undefined variable 'oops'", r.stderr)

    def test_check_syntax_error_and_ok(self):
        self.assertEqual(keen("check", self._tmp("let = 1\n")).returncode, 1)
        r = keen("check", self._tmp(self.PROGRAM))
        self.assertEqual(r.returncode, 0)
        self.assertIn("OK - no errors found", r.stdout)

    def test_missing_argument_is_usage_error(self):
        r = keen("run")
        self.assertEqual(r.returncode, 2)
        self.assertNotEqual(r.stderr, "")

    def test_empty_program(self):
        r = keen("run", self._tmp(""))
        self.assertEqual((r.returncode, r.stdout, r.stderr), (0, "", ""))


class WindowsCompatibilityTests(unittest.TestCase):
    """Files created on Windows (CRLF, BOM, UTF-16) must work. Checked from any OS."""

    def _tmp(self, data):
        f = tempfile.NamedTemporaryFile("wb", suffix=".keen", delete=False)
        f.write(data)
        f.close()
        self.addCleanup(os.unlink, f.name)
        return f.name

    SRC = 'let name = "Monesh"\r\nprint("Hello " + name)\r\nif name == "Monesh" {\r\n    print("ok")\r\n}\r\n'

    def test_crlf_line_endings(self):
        r = keen("run", self._tmp(self.SRC.encode("utf-8")))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.replace("\r\n", "\n"), "Hello Monesh\nok\n")

    def test_utf8_bom_from_notepad(self):
        r = keen("run", self._tmp(b"\xef\xbb\xbf" + self.SRC.encode("utf-8")))
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_utf16_from_powershell_redirect(self):
        r = keen("run", self._tmp(self.SRC.encode("utf-16")))
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_invalid_encoding_gives_clear_message(self):
        r = keen("run", self._tmp(b"print('\xff\xfe\xfa')\n"))
        self.assertEqual(r.returncode, 2)
        self.assertIn("not valid UTF-8", r.stderr)

    def test_unicode_output_never_crashes(self):
        env = dict(os.environ, PYTHONIOENCODING="cp1252")
        path = self._tmp('print("caf\u00e9 \u2713 \u4e2d\u6587")\n'.encode("utf-8"))
        r = subprocess.run([sys.executable, "-m", "keen", "run", path], cwd=ROOT,
                           capture_output=True, env=env, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_paths_with_spaces_and_backslash_style(self):
        d = tempfile.mkdtemp(prefix="keen test ")
        path = os.path.join(d, "my program.keen")
        with open(path, "w", encoding="utf-8") as f:
            f.write('print("spaces ok")\n')
        self.addCleanup(lambda: (os.unlink(path), os.rmdir(d)))
        r = keen("run", path)
        self.assertEqual(r.stdout.strip(), "spaces ok")


class ExampleTests(unittest.TestCase):
    """Every example (except the intentional error demo) must run successfully."""

    def test_examples_run(self):
        folder = os.path.join(ROOT, "examples")
        for name in sorted(os.listdir(folder)):
            if name.endswith(".keen") and name != "errors_demo.keen":
                with self.subTest(example=name):
                    r = keen("run", f"examples/{name}")
                    self.assertEqual(r.returncode, 0, r.stderr)

    def test_new_examples_output(self):
        out = keen("run", "examples/operators.keen").stdout.splitlines()
        self.assertEqual(out[:5], ["20", "30", "5", "5.0", "2"])
        self.assertEqual(out[-3:], ["true", "false", "true"])
        calc = keen("run", "examples/calculator.keen").stdout
        self.assertIn("12 / 0 = cannot divide by zero", calc)
        cond = keen("run", "examples/condition.keen").stdout
        self.assertEqual(cond.splitlines(), ["Monesh", "KEEN is improving", "Teen ticket accepted"])
        multi = keen("run", "examples/multiline.keen").stdout
        self.assertIn("subtotal: 60", multi)
        self.assertIn("ready: true", multi)

    def test_functions_example_values(self):
        out = keen("run", "examples/functions.keen").stdout
        self.assertIn("10! = 3628800", out)
        self.assertIn("fib(20) = 6765", out)
        self.assertIn("counter: 3", out)


if __name__ == "__main__":
    unittest.main()
