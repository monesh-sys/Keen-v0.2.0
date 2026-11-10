# KEEN Design Decisions

Each entry: decision, reason.

1. **Python tree-walking interpreter first.** Matches the spec's roadmap; the fastest way to get a correct reference implementation. Bytecode and native compilation come later and will be measured against this one.
2. **Newline-terminated statements, optional `;`.** Reads cleanly. The lexer drops newlines inside `()`/`[]` so calls and arrays can span lines.
3. **Braces for blocks, no parentheses around conditions.** `if x > 1 { }` as in the spec's proposal.
4. **`else` on the closing-brace line.** Keeps the grammar unambiguous with newline termination; the parser gives a specific hint when violated.
5. **Assignment is a statement.** Prevents `if x = 1` bugs; the parser hints at `==`.
6. **No implicit type coercion.** `"a" + 1` is an error with a hint to use `str()`. `==` never converts types. Surprises are costly in a language meant to be simple and secure.
7. **`/` always yields a float.** One predictable rule for division; integers stay exact for `+ - * %`.
8. **Arbitrary-precision integers.** Inherited from Python; no silent overflow.
9. **Truthiness includes 0, "", [].** Convenient for conditions; documented in the spec.
10. **Functions hoisted, variables not.** Mutual recursion works naturally; using a variable before its `let` is a semantic error.
11. **Separate semantic pass reporting all errors.** Users see every static mistake at once. Function bodies are checked after their enclosing block so they may refer to globals declared later.
12. **Static type checking deferred.** Types are dynamic in 0.1.0; type annotations and checking arrive with a later phase rather than being faked.
13. **Call-depth limit (1000) plus a large thread stack in the CLI.** Runaway recursion yields a KEEN error, not a Python crash.
14. **`app` is a contextual keyword.** `app "Name"` declares the program; `app` remains usable as an identifier.
15. **Python package namespace `keen`.** The spec's `compiler/`, `runtime/`, `cli/` folders live inside `keen/` so they install without clashing with other top-level Python packages.
16. **Only implemented directories exist.** No empty placeholder folders for unbuilt frameworks.
17. **License: MIT (placeholder choice).** Change `LICENSE` and `pyproject.toml` if MoneshSys prefers another license.

## Added in 0.2.0
18. **Logical operators return booleans.** `&&`, `||`, `and`, `or` always yield `true`/`false`, as the 0.2.0 requirements ask. This is the only intentional behaviour change from 0.1.0 (0.1.0 returned an operand).
19. **`!` is tight, `not` is loose.** `!` follows C-family expectations (`!a == b` is `(!a) == b`). The keyword `not` keeps its 0.1.0 precedence so existing programs are unaffected. Both parse from the same token; the parser tells them apart by spelling.
20. **Line continuation only after an operator.** Trailing operators (and open brackets) continue an expression; leading operators do not. This avoids the classic ambiguity where a line starting with `-` silently changes meaning.
21. **Diagnostics on stderr.** Errors, `--trace`, `--debug` and `--verbose` never touch stdout, so shell redirection and tests of program output stay exact.
22. **Tracer as an interpreter hook, not a second interpreter.** The interpreter calls an optional `Tracer`; with no tracer the cost is one `is None` check per statement and behaviour is identical.
23. **Call stack recorded at the first failing frame.** The stack is captured as the error unwinds through the first function call, so it reflects where the failure happened.
24. **End-of-file errors point at the last real token** so the source excerpt and caret are always visible.
25. **Windows file formats handled in the CLI, not the language.** The lexer sees decoded text; the CLI decodes UTF-8, UTF-8 BOM and UTF-16, and the console is configured to replace unencodable characters instead of crashing.
26. **Chained comparisons are rejected by type checking**, with a hint, instead of adding special chained semantics.
