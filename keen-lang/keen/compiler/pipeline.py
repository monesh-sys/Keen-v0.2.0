"""High-level entry points tying the compiler stages together.

source --Lexer--> tokens --Parser--> AST --SemanticAnalyzer--> checked AST --Interpreter--> output
"""

from keen.compiler.errors import SemanticErrors
from keen.compiler.interpreter import Interpreter
from keen.compiler.lexer import Lexer
from keen.compiler.parser import Parser
from keen.compiler.semantic import SemanticAnalyzer
from keen.runtime.builtins import BUILTIN_NAMES


def tokenize(source):
    return Lexer(source).tokenize()


def parse_source(source):
    return Parser(tokenize(source)).parse()


def analyze(program):
    """Return a list of semantic errors (empty if the program is fine)."""
    return SemanticAnalyzer(BUILTIN_NAMES).analyze(program)


def check_source(source):
    """Lex, parse and analyze. Raises KeenSyntaxError or SemanticErrors."""
    program = parse_source(source)
    errors = analyze(program)
    if errors:
        raise SemanticErrors(errors)
    return program


def run_source(source, *, write=None, read_line=None, max_call_depth=1000, tracer=None,
               interpreter=None):
    """Check and run ``source``. Pass ``interpreter`` to keep access to it after an error."""
    program = check_source(source)
    interp = interpreter or Interpreter(
        write=write, read_line=read_line, max_call_depth=max_call_depth, tracer=tracer)
    interp.run(program)
    return interp
