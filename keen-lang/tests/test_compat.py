"""Backward compatibility: KEEN 0.1.0 programs must behave exactly as before.

tests/golden/*.out hold the output recorded from the 0.1.0 release.
"""

import io
import os
import unittest

from keen.compiler.pipeline import run_source

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GOLDEN = os.path.join(ROOT, "tests", "golden")


class GoldenTests(unittest.TestCase):
    def test_all_0_1_0_examples_unchanged(self):
        names = sorted(f[:-4] for f in os.listdir(GOLDEN) if f.endswith(".out"))
        self.assertGreaterEqual(len(names), 6)
        for name in names:
            with self.subTest(example=name):
                with open(os.path.join(ROOT, "examples", name + ".keen"), encoding="utf-8") as f:
                    source = f.read()
                with open(os.path.join(GOLDEN, name + ".out"), encoding="utf-8") as f:
                    expected = f.read()
                out = io.StringIO()
                run_source(source, write=out.write)
                self.assertEqual(out.getvalue(), expected)


class SyntaxStillSupportedTests(unittest.TestCase):
    def run_(self, src):
        out = io.StringIO()
        run_source(src, write=out.write)
        return out.getvalue()

    def test_word_operators(self):
        self.assertEqual(self.run_("print(true and false, true or false, not false)"), "false true true\n")

    def test_not_keyword_keeps_low_precedence(self):
        self.assertEqual(self.run_("print(not 1 == 2)"), "true\n")

    def test_semicolons_and_single_quotes(self):
        self.assertEqual(self.run_("let a = 1; let b = 'x'; print(a, b)"), "1 x\n")

    def test_public_api_names_still_exist(self):
        import keen
        from keen.compiler.interpreter import Interpreter, Environment  # noqa: F401
        from keen.compiler.pipeline import check_source, parse_source, tokenize  # noqa: F401
        self.assertEqual(keen.__version__, keen.KEEN_VERSION)

    def test_semantic_error_class_names_kept(self):
        from keen.compiler.errors import KeenSemanticError, SemanticErrors  # noqa: F401


if __name__ == "__main__":
    unittest.main()
