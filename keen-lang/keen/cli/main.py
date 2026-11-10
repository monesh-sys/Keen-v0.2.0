"""The `keen` command-line interface.

Commands:
    keen --version | --help
    keen run <file> [--trace] [--debug] [--verbose]
    keen check <file>
    keen version | help          (kept from 0.1.0)

Diagnostics (errors, --trace, --debug, --verbose) go to stderr; only the program's own
output goes to stdout. Works on Windows PowerShell / Command Prompt, macOS and Linux.
"""

import argparse
import codecs
import os
import sys
import threading
import time
from typing import Callable, Optional

from keen import KEEN_DEVELOPER, KEEN_VERSION
from keen.compiler.errors import KeenError, SemanticErrors
from keen.compiler.interpreter import Interpreter
from keen.compiler.pipeline import analyze, parse_source, tokenize
from keen.runtime.debug import Tracer

BANNER = f"KEEN Programming Language\nVersion {KEEN_VERSION}\nDeveloped by {KEEN_DEVELOPER}"

HELP_EPILOG = """\
commands:
  keen run <file.keen>             Check and run a program
  keen run <file.keen> --trace     Run and print every executed statement (to stderr)
  keen run <file.keen> --debug     Trace + variable inspection + error call stack (to stderr)
  keen run <file.keen> --verbose   Also show compiler stages and timing (to stderr)
  keen check <file.keen>           Report all errors without running the program
  keen version                     Show version information

options:
  -V, --version                    Show version information
  -h, --help                       Show this help message

Exit codes: 0 success, 1 program error (syntax/semantic/runtime), 2 usage or file error.
"""


# ---------------------------------------------------------------------------
# Console and file helpers (Windows friendly)
# ---------------------------------------------------------------------------
def _configure_console() -> None:
    """Never crash on characters the console encoding cannot display."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="replace")
        except (AttributeError, ValueError):
            pass


def _err(message: str) -> None:
    print(message, file=sys.stderr)


def _decode(data: bytes) -> str:
    """Decode a source file. Handles UTF-8 (with/without BOM) and UTF-16 (Windows PowerShell)."""
    if data.startswith(codecs.BOM_UTF16_LE) or data.startswith(codecs.BOM_UTF16_BE):
        return data.decode("utf-16")
    return data.decode("utf-8-sig")


def _read(path: str) -> Optional[str]:
    if not os.path.isfile(path):
        _err(f"error: cannot find file '{path}'")
        return None
    try:
        with open(path, "rb") as f:
            return _decode(f.read())
    except UnicodeDecodeError:
        _err(f"error: '{path}' is not valid UTF-8 text. Save the file as UTF-8 and try again.")
    except OSError as e:
        _err(f"error: cannot read '{path}': {e.strerror or e}")
    return None


def _with_big_stack(fn: Callable[[], None]) -> None:
    """Run fn in a thread with a large stack so deep KEEN recursion cannot crash Python."""
    result = {}

    def target() -> None:
        sys.setrecursionlimit(60000)
        try:
            fn()
        except BaseException as e:  # re-raised in the calling thread
            result["error"] = e

    for size in (256, 64, 16):
        try:
            threading.stack_size(size * 1024 * 1024)
            break
        except (ValueError, RuntimeError):
            continue
    t = threading.Thread(target=target)
    t.start()
    t.join()
    if "error" in result:
        raise result["error"]


def _report(err, source: str, path: str) -> None:
    _err(err.format(source, path))


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------
def cmd_run(path: str, trace: bool = False, debug: bool = False, verbose: bool = False) -> int:
    source = _read(path)
    if source is None:
        return 2

    def diag(line: str) -> None:
        sys.stdout.flush()  # keep stdout and stderr in a sensible order on a terminal
        _err(line)

    def write(text: str) -> None:
        sys.stdout.write(text)
        if trace or debug:
            sys.stdout.flush()

    tracer = Tracer(source, diag, inspect_variables=debug) if (trace or debug) else None
    interp = Interpreter(write=write, tracer=tracer)
    started = time.perf_counter()

    def pipeline() -> None:
        tokens = tokenize(source)
        if verbose:
            diag(f"[verbose] lexer: {len(tokens)} tokens")
        program = parse_source(source)
        if verbose:
            diag(f"[verbose] parser: {len(program.body)} top-level statement(s)")
        errors = analyze(program)
        if errors:
            raise SemanticErrors(errors)
        if verbose:
            diag("[verbose] semantic analysis: OK")
            diag("[verbose] running program")
        interp.run(program)

    status = 0
    try:
        _with_big_stack(pipeline)
    except (KeenError, SemanticErrors) as e:
        sys.stdout.flush()
        _report(e, source, path)
        status = 1
    except KeyboardInterrupt:
        sys.stdout.flush()
        status = 130
    sys.stdout.flush()
    if tracer is not None:
        tracer.summary()
    if debug:
        tracer.dump_variables(interp.globals, "Variables at exit (globals)")
    if verbose:
        diag(f"[verbose] finished in {(time.perf_counter() - started) * 1000:.1f} ms, exit code {status}")
    return status


def cmd_check(path: str) -> int:
    source = _read(path)
    if source is None:
        return 2
    try:
        program = parse_source(source)
        errors = analyze(program)
        if errors:
            raise SemanticErrors(errors)
    except (KeenError, SemanticErrors) as e:
        _report(e, source, path)
        return 1
    print(f"{path}: OK - no errors found")
    return 0


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="keen",
        description="KEEN Programming Language - Write less. Build more.",
        epilog=HELP_EPILOG, formatter_class=argparse.RawDescriptionHelpFormatter, add_help=False)
    p.add_argument("-V", "--version", action="store_true", help="show version information")
    p.add_argument("-h", "--help", action="store_true", help="show this help message")
    sub = p.add_subparsers(dest="command", metavar="command")
    run = sub.add_parser("run", help="run a KEEN program")
    run.add_argument("file")
    run.add_argument("--trace", action="store_true", help="print each executed statement (stderr)")
    run.add_argument("--debug", action="store_true", help="trace + variable inspection (stderr)")
    run.add_argument("--verbose", action="store_true", help="show compiler stages and timing (stderr)")
    chk = sub.add_parser("check", help="check a KEEN program without running it")
    chk.add_argument("file")
    sub.add_parser("version", help="show version information")
    sub.add_parser("help", help="show help")
    return p


def main(argv=None) -> int:
    _configure_console()
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as e:
        return 2 if e.code else 0
    if args.version or args.command == "version":
        print(BANNER)
        return 0
    if args.help or args.command in (None, "help"):
        print(BANNER)
        print()
        parser.print_help()
        return 0
    if args.command == "run":
        return cmd_run(args.file, args.trace, args.debug, args.verbose)
    if args.command == "check":
        return cmd_check(args.file)
    return 2


if __name__ == "__main__":
    sys.exit(main())
