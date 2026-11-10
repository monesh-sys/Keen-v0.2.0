# KEEN Language Specification — v0.2.0

## 1. Lexical structure
- Source is UTF-8 text. Files use the `.keen` extension.
- **Comments:** `//` to end of line.
- **Statement termination:** a newline or `;`. Newlines are ignored inside `( )` and `[ ]`, and directly
  after an operator (`+ - * / % == != < <= > >= && || and or not ! = += -= *= /=` and `,`), so an expression can
  continue on the next line. A line that *starts* with an operator is a new statement.
- **Identifiers:** letter or `_`, then letters, digits, `_`. Case-sensitive.
- **Keywords:** `let const fn return if else while for in break continue true false null and or not`
  (`app` is contextual: it is a declaration only when followed by a string at the start of a statement.)
- **Numbers:** `42` (integer, arbitrary size), `3.14` (float); `_` allowed between digits (`1_000`).
- **Strings:** `"..."` or `'...'`; escapes `\n \t \r \\ \" \' \0 \uXXXX` (four hex digits). Strings cannot span lines.

## 2. Grammar (EBNF)
```ebnf
program     = { statement } ;
block       = "{" { statement } "}" ;
statement   = app_decl | var_decl | fn_decl | if_stmt | while_stmt | for_stmt
            | return_stmt | "break" | "continue" | assign_or_expr ;
app_decl    = "app" STRING ;
var_decl    = ( "let" | "const" ) IDENT "=" expr ;
fn_decl     = "fn" IDENT "(" [ IDENT { "," IDENT } ] ")" block ;
if_stmt     = "if" expr block [ "else" ( if_stmt | block ) ] ;
while_stmt  = "while" expr block ;
for_stmt    = "for" IDENT "in" expr block ;
return_stmt = "return" [ expr ] ;
assign_or_expr = expr [ ( "=" | "+=" | "-=" | "*=" | "/=" ) expr ] ;   (* left side: IDENT or index *)

expr        = or_expr ;
or_expr     = and_expr { ( "or" | "||" ) and_expr } ;
and_expr    = not_expr { ( "and" | "&&" ) not_expr } ;
not_expr    = "not" not_expr | equality ;          (* keyword form: low precedence *)
equality    = comparison { ( "==" | "!=" ) comparison } ;
comparison  = term { ( "<" | "<=" | ">" | ">=" ) term } ;
term        = factor { ( "+" | "-" ) factor } ;
factor      = unary { ( "*" | "/" | "%" ) unary } ;
unary       = ( "-" | "!" ) unary | postfix ;       (* symbol form: high precedence *)
postfix     = primary { "(" [ expr { "," expr } ] ")" | "[" expr "]" } ;
primary     = NUMBER | STRING | "true" | "false" | "null" | IDENT
            | "(" expr ")" | "[" [ expr { "," expr } [ "," ] ] "]" ;
```
`else` must be on the same line as the closing `}` of the `if` block.
Assignment is a statement, not an expression.

## 3. Types
`integer`, `float`, `string`, `boolean`, `null`, `array`, `function`. (`object` is planned.)
Typing is dynamic in 0.1.0.

**Truthiness:** `false`, `null`, `0`, `0.0`, `""` and `[]` are falsy; everything else is truthy.
**Equality:** `==` never converts types (`1 == true` is `false`; `1 == 1.0` is `true`). Arrays compare element-wise.

## 4. Operators
| Operator | Meaning | Operands |
|---|---|---|
| `+` | add / concatenate | number+number, string+string, array+array |
| `- * %` | arithmetic | numbers |
| `/` | division, **always returns float** | numbers; divisor ≠ 0 |
| `== !=` | equality | any |
| `< <= > >=` | ordering | two numbers or two strings |
| `&&` / `and` | short-circuit and, **returns boolean** | any (by truthiness) |
| `\|\|` / `or` | short-circuit or, **returns boolean** | any (by truthiness) |
| `!` (tight) / `not` (loose) | logical negation, returns boolean | any |
| `= += -= *= /=` | assignment | variable or `array[i]` |

Mixing types (e.g. `"n: " + 5`) is a runtime error; use `str()`.
Precedence, high to low: call/index; unary `-` `!`; `* / %`; `+ -`; `< <= > >=`; `== !=`; `not`; `&& and`; `|| or`.
All binary operators are left-associative; unary operators and `not` are right-associative.
Comparisons do not chain (`1 < 2 < 3` compares a boolean with an integer and is an error).

## 5. Scoping
- Blocks (`if`, `while`, `for`, function bodies) create scopes. Inner scopes may shadow outer names.
- Declaring the same name twice in one scope is an error. A function's parameters share its body scope.
- A `for` loop variable lives in the loop body scope.
- Functions are hoisted within their block, so they may be called before the line that defines them.
- Functions are first-class values and close over the scope they were defined in.
- `const` bindings cannot be reassigned (the value itself, e.g. an array, can still be mutated).

## 6. Built-in functions
| Function | Description |
|---|---|
| `print(...)` | print values separated by spaces, then a newline |
| `len(x)` | length of a string or array |
| `str(x)` / `int(x)` / `float(x)` | conversions |
| `type(x)` | type name as a string |
| `range(stop)`, `range(start, stop[, step])` | array of integers |
| `push(array, value)` | append to an array |
| `input([prompt])` | read a line from standard input |

Indexing: `a[0]`, negative indexes count from the end, out-of-range is an error. Strings are indexable but immutable.

## 7. Errors
Four types: Lexer Error, Syntax Error (stop at the first), Semantic Error (all reported before running) and
Runtime Error. Each report shows Type, File, Line, Column, Message, an optional Suggestion, a call stack
for errors inside functions, and a source excerpt (see README for the exact format).
Semantic checks: undefined/early-used names, duplicate declarations, const assignment,
`break`/`continue` outside loops, `return` outside functions.
Runtime limit: maximum call depth 1000.
