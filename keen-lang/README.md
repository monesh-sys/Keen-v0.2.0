# KEEN — Write less. Build more.

**KEEN** is an original programming language with its own lexer, parser, semantic analyzer and interpreter.
Version **0.2.0 "Core Improvements"** · Developed by **Monesh K.K.** · Implemented in Python · files end in `.keen`

## Version 0.2.0 features
- Professional error reports with exact line/column, suggestions and call stacks
- Debugging: `--trace`, `--debug`, `--verbose` (diagnostics on stderr, program output untouched)
- Operators `&&`, `||`, `!` with documented precedence; logical operators always return booleans
- Multi-line expressions, `//` comments, `\n \t \" \u00e9`-style string escapes
- Safe type checking at runtime: invalid operations are errors, never silent wrong results
- Windows-friendly CLI (CRLF, UTF-8/BOM/UTF-16 files)
- 236 automated tests; every 0.1.0 example still produces identical output

## Installation

KEEN needs **Python 3.10 or newer** and nothing else. The commands below are for **Windows PowerShell**;
macOS/Linux users: see the note at the end of this section.

### Step 1: Check Python
```powershell
python --version
```
If this says the command is not found, install Python from <https://www.python.org/downloads/> and tick
**"Add Python to PATH"** during setup. Then close and reopen PowerShell.

### Step 2: Extract the zip and open the project folder
Right-click `keen-lang-0.2.0.zip` and choose **Extract All**, then:
```powershell
cd C:\Users\<your-name>\Downloads\keen-lang-0.2.0
dir
```
The listing **must** show `keen`, `examples`, `tests` and `pyproject.toml`.
If you only see another folder called `keen-lang`, go inside it (`cd keen-lang`) and run `dir` again.
Every remaining step is run from the folder that contains `pyproject.toml`.

### Step 3: Remove any other KEEN version
Every KEEN version uses the same package name, so only one can be installed at a time.
```powershell
pip uninstall keen-lang -y
pip uninstall keen -y
```
A "not installed" warning is fine. This prevents an old version from being picked up by mistake.

### Step 4: Install
```powershell
pip install -e .
```
`-e` makes pip use this folder directly, so do not move or delete it afterwards. It also creates the `keen` command.

### Step 5: Verify
```powershell
python -m keen --version
```
Expected output:
```text
KEEN Programming Language
Version 0.2.0
Developed by Monesh K.K.
```
Run your first program:
```powershell
python -m keen run examples/hello.keen
```
```text
Hello from KEEN!
Created by MoneshSys Technologies.
```

### Step 6: Use the short `keen` command (optional)
```powershell
keen --version
```
If PowerShell says `keen` is **not recognized**, Python's Scripts folder is not on your PATH:
1. Print the folder: `python -c "import sysconfig; print(sysconfig.get_path('scripts', 'nt_user'))"`
2. Press the Windows key, search **Edit environment variables for your account**.
3. Select **Path** > **Edit** > **New**, paste the folder from step 1, click OK.
4. **Close and reopen PowerShell.**

You can always skip this step: `python -m keen ...` does exactly the same thing from any folder once KEEN is installed
(or from the project folder even if it is not installed).

### Troubleshooting
| What you see | Cause and fix |
|---|---|
| `neither 'setup.py' nor 'pyproject.toml' found` | You are in the wrong folder. Run `dir`; if you see a `keen-lang` folder, `cd keen-lang`. |
| `keen : The term 'keen' is not recognized` | Not installed yet, or the Scripts folder is not on PATH. Use `python -m keen ...` or do step 6. |
| `python -m keen --version` prints `KEEN 0.1.0` | Python is loading an old copy. Check with `python -c "import keen; print(keen.__file__)"`; the path must be inside the folder you just extracted. Redo step 3, then step 4 from the correct folder. |
| `KEEN: file not found` or any message not starting with `error:` or `KEEN Error:` | A different program or older copy is answering. Run `pip uninstall keen-lang keen -y` and retry from the project folder. |
| `error: cannot find file 'x.keen'` | The path to your program is wrong. Check the name and your current folder with `dir`. |
| `python` is not recognized | Python is not installed or not on PATH (step 1). Try `py --version` and use `py -m keen ...`. |
| Weird characters in the output | Run `chcp 65001` in Command Prompt, or use Windows Terminal. KEEN never crashes on them, it only replaces what the console cannot show. |

### Run without installing
Skip steps 3 and 4 and, from the project folder, use:
```powershell
python -m keen run examples/hello.keen
```
Python always runs the copy in the folder you are standing in. This is also the easiest way to keep several KEEN versions
side by side: put each version in its own folder and `cd` into the one you want.

### Installing KEEN 0.1.0 instead
The steps are the same, using the folder from the `keen-lang-0.1.0.zip` download. Two differences:
- Verify with `python -m keen version` (0.1.0 has no `--version` flag). It prints `KEEN 0.1.0`.
- 0.1.0 has `run`, `check`, `version` and `help` only; `--trace`, `--debug`, `--verbose`, `&&`, `||` and `!` are 0.2.0 features.

Because the versions share one package name, uninstall one before installing the other (step 3), or use
"Run without installing" for both.

### macOS / Linux
```bash
python3 --version
cd keen-lang-0.2.0            # the folder that contains pyproject.toml
pip3 uninstall keen-lang -y
pip3 install -e .
keen --version
```
If `keen` is not found, make sure `~/.local/bin` is on your PATH, or use `python3 -m keen ...`.

## CLI commands
| Command | What it does |
|---|---|
| `keen --version` | Show version information |
| `keen --help` | Show help |
| `keen run <file.keen>` | Check and run a program |
| `keen run <file.keen> --trace` | Also print every executed statement and function call (stderr) |
| `keen run <file.keen> --debug` | Trace + variable inspection + variables at exit + error call stack (stderr) |
| `keen run <file.keen> --verbose` | Also show lexer/parser/semantic stages and timing (stderr) |
| `keen check <file.keen>` | Find all syntax/semantic errors without running |

Exit codes: `0` success · `1` program error · `2` usage or file error.

## Syntax
```keen
// comments start with //
let name = "Monesh"          // variable
const version = 0.2          // constant (cannot be reassigned)
print(name)

if version > 0.1 {
    print("KEEN is improving")
} else if version == 0.1 {
    print("Same version")
} else {
    print("Old version")
}

fn add(a, b) {
    return a + b
}
print(add(10, 20))

let i = 0
while i < 3 {
    i += 1
}
for n in range(1, 4) { print(n) }
for item in ["a", "b"] { print(item) }
```
Rules:
- One statement per line (or separate with `;`). Blocks use `{ }`; `else` goes on the same line as `}`.
- An expression continues on the next line **after** an operator, or inside `( )` / `[ ]`:
  ```keen
  let total = 10 +
      20
  ```
  A line that *starts* with an operator is a new statement (and an error).
- Assignment (`=`, `+=`, `-=`, `*=`, `/=`) is a statement, not an expression.
- Names must be declared before use (functions may be used before their definition).
- Blocks create scopes; redeclaring a name in the same scope is an error.

## Data types
| Type | Examples | Notes |
|---|---|---|
| integer | `42`, `1_000` | any size |
| float | `3.14` | `/` always returns a float (`7 / 2` is `3.5`, `10 / 2` is `5.0`) |
| string | `"hi"`, `'hi'` | escapes `\n \t \r \\ \" \' \0 \uXXXX` |
| boolean | `true`, `false` | |
| null | `null` | |
| array | `[1, "a", true]` | indexing `a[0]`, `a[-1]`; `push`, `len` |
| function | `fn f() {}` | first-class, supports closures |

No implicit conversion: `"Age: " + 17` is an error; write `"Age: " + str(17)`.
`==` never converts types (`1 == "1"` and `0 == false` are `false`; `1 == 1.0` is `true`).
Truthiness (for `if`, `while`, `&&`, `||`, `!`): `false`, `null`, `0`, `0.0`, `""`, `[]` are false; everything else is true.

## Operators
From highest to lowest precedence:

| Level | Operators | Associativity |
|---|---|---|
| 1 | calls `f()`, indexing `a[i]` | left |
| 2 | unary `-`, `!` | right |
| 3 | `*` `/` `%` | left |
| 4 | `+` `-` | left |
| 5 | `<` `<=` `>` `>=` | left |
| 6 | `==` `!=` | left |
| 7 | `not` (keyword) | right |
| 8 | `&&` / `and` | left |
| 9 | `\|\|` / `or` | left |

`&&`, `||`, `and`, `or` short-circuit and **always return `true` or `false`**.
`!` binds tightly (`!a == b` is `(!a) == b`); the keyword `not` binds loosely (`not a == b` is `not (a == b)`).
Comparisons do not chain: `1 < 2 < 3` is a type error; write `1 < 2 && 2 < 3`.

```keen
print(10 + 5 * 2)     // 20
print(10 > 5)         // true
print(true && false)  // false
print(true || false)  // true
print(!false)         // true
```
`+` also joins strings (`"a" + "b"`) and arrays. Built-ins: `print len str int float type range push input`.

## Error handling
Every error is reported on **stderr** in the same format:

```text
KEEN Error:
  Type: Semantic Error
  File: example.keen
  Line: 5
  Column: 7
  Message: Undefined variable 'totl'
  Suggestion: Did you mean 'total'?

  5 | print(totl)
    |       ^
```
| Type | Examples |
|---|---|
| Lexer Error | unexpected character, unterminated string, bad number or escape, `&` instead of `&&` |
| Syntax Error | missing `)` / `}`, stray `}`, incomplete expression, unexpected token, missing condition |
| Semantic Error | undefined variable, duplicate declaration, constant reassignment, `break` outside a loop |
| Runtime Error | type mismatch, division by zero, bad index, wrong argument count, call-depth limit |

Syntax errors stop at the first problem. Semantic errors are all reported before anything runs
(`keen check` shows them without running). Runtime errors inside functions add a **call stack**.

## Debugging guide
Diagnostics are written to stderr so `keen run app.keen > out.txt` still captures only program output.
Use `2> debug.txt` to save the trace.

```powershell
keen run examples/debug_demo.keen --trace
keen run examples/debug_demo.keen --debug
```
```text
[trace] step 4    line 11   total += double(i)
[trace]                      -> call double(1)
[trace] step 5    line 7      return n * rate
[trace]                      <- double returned 2
[debug]   total = 2   (integer)
...
[debug] Variables at exit (globals):
[debug]   total = 12   (integer)
[debug]   rate = 2   (constant)
```
- `--trace`: step number, line, source text of each statement; calls and returns (indented by depth).
- `--debug`: everything in `--trace`, plus every variable change and a dump of globals at exit — even after an error.
- `--verbose`: compiler stages and timing.

## Example programs (`examples/`)
`hello` · `variables` · `arithmetic` · `operators` · `conditions` · `condition` (nested) · `calculator` ·
`functions` · `loops` · `multiline` · `debug_demo` · `errors_demo` (intentional mistakes for `keen check`).

## Running the tests
```powershell
python -m unittest discover -s tests -t .
```

## Project layout
```text
keen-lang/
├── keen/
│   ├── compiler/   tokens, lexer, parser, ast_nodes, semantic, interpreter, errors, pipeline
│   ├── runtime/    values, builtins, debug (tracer)
│   └── cli/        main.py  (the `keen` command)
├── examples/  tests/  docs/
└── pyproject.toml  README.md  CHANGELOG.md  LICENSE  CONTRIBUTING.md
```

## Known limitations
- Tree-walking interpreter in Python: correct but not fast. There is no bytecode VM or native compiler.
- No classes, objects/maps, modules/imports, exceptions (`try/catch`), anonymous functions, generics, type annotations,
  async/await or pattern matching yet.
- No standard library modules beyond the nine built-in functions; no web/mobile/desktop/game/AI frameworks,
  package manager, IDE or language server.
- Types are checked at runtime only (no static type checker).
- Syntax errors stop at the first error (no error recovery).
- Recursion is limited to 1000 nested calls.
- The debugger is a tracer: it cannot pause, step or set breakpoints interactively.
- Windows support is implemented with Windows file formats and console behaviour in mind and tested on Linux;
  please report any problem you hit on PowerShell or Command Prompt.

## Developer
**Monesh K.K.** — KEEN, "Write less. Build more."
