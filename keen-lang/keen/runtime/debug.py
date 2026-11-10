"""Execution tracing and variable inspection for KEEN.

A ``Tracer`` receives events from the interpreter and turns them into readable lines.
Lines are handed to an ``emit`` callable; the CLI sends them to stderr so they never
mix with the program's normal output on stdout.
"""

from typing import Any, Callable, List, Optional

from keen.runtime.values import to_display, type_name


class Tracer:
    def __init__(self, source: str, emit: Callable[[str], None], inspect_variables: bool = False):
        self.lines: List[str] = source.splitlines()
        self.emit = emit
        self.inspect_variables = inspect_variables
        self.steps = 0

    # -- events from the interpreter --------------------------------------
    def on_statement(self, node: Any, depth: int) -> None:
        """Called before every executed statement (current statement information)."""
        self.steps += 1
        text = ""
        if 1 <= node.line <= len(self.lines):
            text = self.lines[node.line - 1].strip()
        indent = "  " * depth
        self.emit(f"[trace] step {self.steps:<4} line {node.line:<4} {indent}{text}")

    def on_call(self, name: str, args: List[Any], depth: int) -> None:
        shown = ", ".join(to_display(a, True) for a in args)
        self.emit(f"[trace] {'':<20} {'  ' * depth}-> call {name}({shown})")

    def on_return(self, name: str, value: Any, depth: int) -> None:
        self.emit(f"[trace] {'':<20} {'  ' * depth}<- {name} returned {to_display(value, True)}")

    def on_variable(self, label: str, value: Any) -> None:
        """Called after a variable (or array element) is created or changed."""
        if self.inspect_variables:
            self.emit(f"[debug]   {label} = {to_display(value, True)}   ({type_name(value)})")

    def on_error(self, error: Exception) -> None:
        self.emit(f"[trace] error raised: {getattr(error, 'message', error)}")

    # -- inspection helpers -----------------------------------------------
    def dump_variables(self, env: Any, title: str = "Variables") -> None:
        """Print every variable in ``env`` (user-defined globals only, no builtins)."""
        self.emit(f"[debug] {title}:")
        if not env.vars:
            self.emit("[debug]   (none)")
        for name, value in env.vars.items():
            kind = "constant" if name in env.consts else type_name(value)
            self.emit(f"[debug]   {name} = {to_display(value, True)}   ({kind})")

    def summary(self) -> None:
        self.emit(f"[trace] finished: {self.steps} statement(s) executed")
