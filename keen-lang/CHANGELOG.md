# Changelog

## 0.2.0 - Core Improvements

### Error handling
- New report format: `KEEN Error:` with `Type`, `File`, `Line`, `Column`, `Message`, optional `Suggestion`,
  a call stack for errors inside functions, and a source excerpt with a caret.
- Four error types: Lexer Error, Syntax Error, Semantic Error, Runtime Error (new `KeenLexError`).
- Exact line/column for every error. Errors at the end of a file now point at the last real token.
- Clearer parser messages: incomplete expressions ("expected a value after '+'"), missing or stray
  `)`, `]`, `}` (the suggestion names the opening bracket's line and column), missing conditions,
  missing function body braces.
- Single `&` / `|` now suggest `&&` / `||`. Type-mismatch errors suggest `str()`, `int()` or `float()`.

### Debugging (`keen run`)
- `--trace`: every executed statement (step, line, source text) plus function calls and returns.
- `--debug`: trace + variable inspection (every variable/array-element change, variables at exit) + error call stack.
- `--verbose`: lexer/parser/semantic stages and timing.
- All diagnostics go to stderr; program output on stdout is never changed.

### Syntax
- Expressions may continue on the next line after an operator (`+`, `&&`, `=`, ...).
- `\uXXXX` string escapes. Better lexer errors for bad escapes and numbers.
- Stricter, clearer block validation.

### Operators
- Added `&&`, `||` and `!` (the 0.1.0 words `and`, `or`, `not` still work).
- **Behaviour change:** `and`/`or`/`&&`/`||` now always return `true` or `false` (0.1.0 returned one of the operands).
- `!` binds tightly like `-`; the keyword `not` keeps its 0.1.0 low precedence, so existing programs behave the same.
- Documented precedence and associativity; chained comparisons such as `1 < 2 < 3` give a helpful type error.

### CLI
- `keen --version`, `keen --help`, `keen run <file> [--trace|--debug|--verbose]`, `keen check <file>`.
  `keen version` and `keen help` from 0.1.0 still work.
- Windows: reads UTF-8, UTF-8 with BOM and UTF-16 files (PowerShell/Notepad), CRLF line endings,
  and never crashes on characters the console cannot display.

### Other
- `KEEN_VERSION = "0.2.0"`, package metadata updated.
- New examples: `calculator`, `condition`, `operators`, `multiline`, `debug_demo`.
- Test suite grew from 122 to 236 tests, including golden-output tests that run every 0.1.0 example and
  compare against the output recorded from 0.1.0.

### Compatibility
All 0.1.0 example programs produce identical output. The only intentional behaviour change is the boolean
result of `and`/`or`. Error *text* changed (new report format).

## 0.1.0 - Language core
Lexer, parser, AST, semantic analyzer, tree-walking interpreter; variables, constants, numbers, strings,
booleans, null, arrays; `if`/`while`/`for`; functions and closures; built-ins; `keen run`/`check`.
