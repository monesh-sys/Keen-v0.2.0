"""Error types and the KEEN error report format."""

from typing import List, Optional, Tuple


class KeenError(Exception):
    """Base class for all errors raised while processing KEEN source.

    Report format (see ``format``)::

        KEEN Error:
          Type: Runtime Error
          File: example.keen
          Line: 5
          Column: 10
          Message: Undefined variable 'total'
          Suggestion: Did you mean 'totals'?
    """

    kind = "Error"

    def __init__(self, message: str, line: Optional[int] = None, col: Optional[int] = None,
                 hint: Optional[str] = None):
        super().__init__(message)
        self.message = message
        self.line = line
        self.col = col
        self.hint = hint
        # Call stack at the moment of a runtime error: [(function, call_line, call_col), ...]
        self.stack: Optional[List[Tuple[str, int, int]]] = None

    def format(self, source: Optional[str] = None, filename: str = "<input>") -> str:
        out = ["KEEN Error:", f"  Type: {self.kind}", f"  File: {filename}"]
        if self.line is not None:
            out.append(f"  Line: {self.line}")
            out.append(f"  Column: {self.col or 1}")
        out.append(f"  Message: {self.message}")
        if self.hint:
            out.append(f"  Suggestion: {self.hint}")
        if self.stack:
            out.append("  Call stack (most recent call last):")
            for name, line, col in self.stack:
                out.append(f"    {name}() called at line {line}, column {col}")
        excerpt = self._excerpt(source)
        if excerpt:
            out.append("")
            out.extend(excerpt)
        return "\n".join(out)

    def _excerpt(self, source: Optional[str]) -> List[str]:
        if source is None or self.line is None:
            return []
        lines = source.splitlines()
        if not 1 <= self.line <= len(lines):
            return []
        text = lines[self.line - 1].replace("\t", " ")
        gutter = str(self.line)
        pad = " " * len(gutter)
        col = self.col or 1
        return [
            f"  {pad} |",
            f"  {gutter} | {text}",
            f"  {pad} | {' ' * (col - 1)}^",
        ]


class KeenSyntaxError(KeenError):
    kind = "Syntax Error"


class KeenLexError(KeenSyntaxError):
    """Raised by the lexer (bad characters, unterminated strings, bad numbers)."""
    kind = "Lexer Error"


class KeenSemanticError(KeenError):
    kind = "Semantic Error"


class KeenRuntimeError(KeenError):
    kind = "Runtime Error"


class SemanticErrors(Exception):
    """Raised when the semantic analyzer finds one or more problems."""

    def __init__(self, errors: List[KeenError]):
        super().__init__(f"{len(errors)} semantic error(s)")
        self.errors = errors

    def format(self, source: Optional[str] = None, filename: str = "<input>") -> str:
        parts = [e.format(source, filename) for e in self.errors]
        n = len(self.errors)
        summary = f"{n} error{'s' if n != 1 else ''} found. Nothing was run."
        return "\n\n".join(parts) + "\n\n" + summary


class BuiltinError(Exception):
    """Raised by built-in functions; the interpreter attaches a source position."""
