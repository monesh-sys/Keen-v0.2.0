"""Recursive-descent parser: tokens -> AST. Stops at the first syntax error."""

from keen.compiler import ast_nodes as ast
from keen.compiler.errors import KeenSyntaxError
from keen.compiler.tokens import TokenType as T

ASSIGN_OPS = (T.ASSIGN, T.PLUS_ASSIGN, T.MINUS_ASSIGN, T.STAR_ASSIGN, T.SLASH_ASSIGN)

# Tokens that must be followed by a value; used to word "incomplete expression" errors.
NEEDS_OPERAND = (
    T.PLUS, T.MINUS, T.STAR, T.SLASH, T.PERCENT, T.EQ, T.NE, T.LT, T.LE, T.GT, T.GE,
    T.AND, T.OR, T.NOT, T.COMMA, T.LPAREN, T.LBRACKET,
) + ASSIGN_OPS

CLOSERS = {T.LPAREN: ")", T.LBRACKET: "]", T.LBRACE: "}"}


class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    # -- token helpers -----------------------------------------------------
    def _peek(self, offset=0):
        i = min(self.pos + offset, len(self.tokens) - 1)
        return self.tokens[i]

    def _check(self, *types):
        return self._peek().type in types

    def _advance(self):
        tok = self.tokens[self.pos]
        if tok.type != T.EOF:
            self.pos += 1
        return tok

    def _match(self, *types):
        if self._check(*types):
            return self._advance()
        return None

    @staticmethod
    def _describe(tok):
        if tok.type == T.EOF:
            return "end of file"
        if tok.type == T.NEWLINE:
            return "end of line"
        return f"'{tok.text}'"

    def _error(self, message, tok=None, hint=None):
        tok = tok or self._peek()
        line, col = tok.line, tok.col
        if tok.type == T.EOF:
            # "end of file" has no visible position; point just after the last real token.
            for prev in reversed(self.tokens):
                if prev.type not in (T.EOF, T.NEWLINE):
                    line, col = prev.line, prev.col + len(prev.text)
                    break
        return KeenSyntaxError(message, line, col, hint)

    def _expect(self, type_, message, hint=None, open_tok=None):
        if self._check(type_):
            return self._advance()
        tok = self._peek()
        if hint is None and open_tok is not None:
            closer = CLOSERS.get(open_tok.type, "?")
            hint = (f"Check that the '{open_tok.text}' on line {open_tok.line}, "
                    f"column {open_tok.col} has a matching '{closer}'.")
        raise self._error(f"{message} but found {self._describe(tok)}", tok, hint)

    def _skip_newlines(self):
        while self._check(T.NEWLINE, T.SEMICOLON):
            self._advance()

    def _skip_line_breaks(self):
        """Allow an expression to continue on the next line after an operator."""
        while self._check(T.NEWLINE):
            self._advance()

    def _end_statement(self):
        if self._check(T.NEWLINE, T.SEMICOLON):
            self._advance()
        elif not self._check(T.EOF, T.RBRACE):
            tok = self._peek()
            raise self._error(
                f"Expected end of statement but found {self._describe(tok)}", tok,
                "Put each statement on its own line (or separate them with ';').",
            )

    # -- program / blocks --------------------------------------------------
    def parse(self):
        body = []
        self._skip_newlines()
        while not self._check(T.EOF):
            body.append(self._statement())
            self._skip_newlines()
        return ast.Program(body, line=1, col=1)

    def _block(self, context="Expected '{'"):
        open_tok = self._expect(T.LBRACE, context)
        stmts = []
        self._skip_newlines()
        while not self._check(T.RBRACE):
            if self._check(T.EOF):
                raise self._error(
                    "Unclosed block: expected '}' before end of file", open_tok,
                    "This '{' was never closed.",
                )
            stmts.append(self._statement())
            self._skip_newlines()
        self._advance()  # }
        return stmts

    # -- statements --------------------------------------------------------
    def _statement(self):
        tok = self._peek()
        t = tok.type
        if t == T.IDENT and tok.text == "app" and self._peek(1).type == T.STRING:
            self._advance()
            name = self._advance().value
            self._end_statement()
            return ast.AppDecl(name, line=tok.line, col=tok.col)
        if t in (T.LET, T.CONST):
            return self._var_decl()
        if t == T.FN:
            return self._fn_decl()
        if t == T.IF:
            return self._if()
        if t == T.WHILE:
            self._advance()
            cond = self._condition("while")
            return ast.While(cond, self._block(), line=tok.line, col=tok.col)
        if t == T.FOR:
            return self._for()
        if t == T.RETURN:
            self._advance()
            value = None
            if not self._check(T.NEWLINE, T.SEMICOLON, T.EOF, T.RBRACE):
                value = self._expression()
            self._end_statement()
            return ast.Return(value, line=tok.line, col=tok.col)
        if t == T.BREAK:
            self._advance()
            self._end_statement()
            return ast.Break(line=tok.line, col=tok.col)
        if t == T.CONTINUE:
            self._advance()
            self._end_statement()
            return ast.Continue(line=tok.line, col=tok.col)
        if t == T.ELSE:
            raise self._error(
                "'else' without a matching 'if'", tok,
                "'else' must be on the same line as the closing '}' of the 'if' block: } else {",
            )
        return self._expr_or_assign()

    def _var_decl(self):
        kw = self._advance()
        is_const = kw.type == T.CONST
        name_tok = self._expect(T.IDENT, f"Expected a name after '{kw.text}'")
        if not self._check(T.ASSIGN):
            if is_const:
                raise self._error(
                    f"Constant '{name_tok.text}' must be given a value",
                    name_tok, f"Write: const {name_tok.text} = <value>",
                )
            raise self._error(
                f"Variable '{name_tok.text}' must be given a value", name_tok,
                f"Write: let {name_tok.text} = null   (if you want an empty variable)",
            )
        self._advance()
        self._skip_line_breaks()
        value = self._expression()
        self._end_statement()
        return ast.VarDecl(name_tok.text, value, is_const, line=kw.line, col=kw.col)

    def _fn_decl(self):
        kw = self._advance()
        name_tok = self._expect(T.IDENT, "Expected a function name after 'fn'")
        open_paren = self._expect(T.LPAREN, f"Expected '(' after function name '{name_tok.text}'")
        params = []
        if not self._check(T.RPAREN):
            while True:
                p = self._expect(T.IDENT, "Expected a parameter name")
                params.append(p.text)
                if not self._match(T.COMMA):
                    break
        self._expect(T.RPAREN, "Expected ')' after parameters", open_tok=open_paren)
        body = self._block(f"Expected '{{' to start the body of function '{name_tok.text}'")
        return ast.FnDecl(name_tok.text, params, body, line=kw.line, col=kw.col)

    def _condition(self, keyword):
        if self._check(T.LBRACE):
            raise self._error(
                f"Missing condition after '{keyword}'", self._peek(),
                f"Write a condition before the '{{', for example: {keyword} x > 0 {{ ... }}"
                if keyword != "for" else "Example: for i in range(0, 5) { ... }")
        cond = self._expression()
        if not self._check(T.LBRACE):
            tok = self._peek()
            hint = "Use '==' to compare values; '=' assigns." if tok.type == T.ASSIGN else None
            raise self._error(
                f"Expected '{{' after {keyword} condition but found {self._describe(tok)}",
                tok, hint,
            )
        return cond

    def _if(self):
        kw = self._advance()
        cond = self._condition("if")
        then_body = self._block()
        else_body = None
        if self._match(T.ELSE):
            if self._check(T.IF):
                else_body = [self._if()]
            else:
                else_body = self._block()
        return ast.If(cond, then_body, else_body, line=kw.line, col=kw.col)

    def _for(self):
        kw = self._advance()
        var = self._expect(T.IDENT, "Expected a loop variable name after 'for'")
        self._expect(T.IN, f"Expected 'in' after '{var.text}'", "Example: for i in range(0, 5) { ... }")
        iterable = self._condition("for")
        return ast.For(var.text, iterable, self._block(), line=kw.line, col=kw.col)

    def _expr_or_assign(self):
        start = self._peek()
        expr = self._expression()
        if self._check(*ASSIGN_OPS):
            op_tok = self._advance()
            self._skip_line_breaks()
            if not isinstance(expr, (ast.Identifier, ast.Index)):
                raise self._error(
                    "Invalid assignment target", start,
                    "You can only assign to a variable or an array element.",
                )
            value = self._expression()
            self._end_statement()
            return ast.Assign(expr, op_tok.text, value, line=start.line, col=start.col)
        self._end_statement()
        return ast.ExprStmt(expr, line=start.line, col=start.col)

    # -- expressions (lowest to highest precedence) -------------------------
    def _expression(self):
        return self._or()

    def _or(self):
        left = self._and()
        while self._check(T.OR):
            tok = self._advance()
            self._skip_line_breaks()
            left = ast.Logical("or", left, self._and(), line=tok.line, col=tok.col)
        return left

    def _and(self):
        left = self._not()
        while self._check(T.AND):
            tok = self._advance()
            self._skip_line_breaks()
            left = ast.Logical("and", left, self._not(), line=tok.line, col=tok.col)
        return left

    def _not(self):
        # The keyword 'not' has low precedence (as in 0.1.0): `not a == b` is `not (a == b)`.
        # The symbol '!' binds tightly; it is handled in _unary.
        if self._check(T.NOT) and self._peek().text == "not":
            tok = self._advance()
            self._skip_line_breaks()
            return ast.Unary("not", self._not(), line=tok.line, col=tok.col)
        return self._equality()

    def _binary_level(self, next_level, types):
        left = next_level()
        while self._check(*types):
            tok = self._advance()
            self._skip_line_breaks()
            left = ast.Binary(tok.text, left, next_level(), line=tok.line, col=tok.col)
        return left

    def _equality(self):
        return self._binary_level(self._comparison, (T.EQ, T.NE))

    def _comparison(self):
        return self._binary_level(self._term, (T.LT, T.LE, T.GT, T.GE))

    def _term(self):
        return self._binary_level(self._factor, (T.PLUS, T.MINUS))

    def _factor(self):
        return self._binary_level(self._unary, (T.STAR, T.SLASH, T.PERCENT))

    def _unary(self):
        if self._check(T.MINUS):
            tok = self._advance()
            self._skip_line_breaks()
            return ast.Unary("-", self._unary(), line=tok.line, col=tok.col)
        if self._check(T.NOT):  # '!' (the 'not' keyword is consumed earlier, in _not)
            tok = self._advance()
            self._skip_line_breaks()
            return ast.Unary("not", self._unary(), line=tok.line, col=tok.col)
        return self._postfix()

    def _postfix(self):
        expr = self._primary()
        while True:
            if self._check(T.LPAREN):
                tok = self._advance()
                args = []
                if not self._check(T.RPAREN):
                    while True:
                        args.append(self._expression())
                        if not self._match(T.COMMA):
                            break
                self._expect(T.RPAREN, "Expected ')' after arguments", open_tok=tok)
                expr = ast.Call(expr, args, line=tok.line, col=tok.col)
            elif self._check(T.LBRACKET):
                tok = self._advance()
                index = self._expression()
                self._expect(T.RBRACKET, "Expected ']' after index", open_tok=tok)
                expr = ast.Index(expr, index, line=tok.line, col=tok.col)
            else:
                return expr

    def _primary(self):
        tok = self._peek()
        t = tok.type
        if t in (T.NUMBER, T.STRING):
            self._advance()
            return ast.Literal(tok.value, line=tok.line, col=tok.col)
        if t == T.TRUE:
            self._advance()
            return ast.Literal(True, line=tok.line, col=tok.col)
        if t == T.FALSE:
            self._advance()
            return ast.Literal(False, line=tok.line, col=tok.col)
        if t == T.NULL:
            self._advance()
            return ast.Literal(None, line=tok.line, col=tok.col)
        if t == T.IDENT:
            self._advance()
            return ast.Identifier(tok.text, line=tok.line, col=tok.col)
        if t == T.LPAREN:
            self._advance()
            expr = self._expression()
            self._expect(T.RPAREN, "Expected ')' to close the parenthesis", open_tok=tok)
            return expr
        if t == T.LBRACKET:
            self._advance()
            elements = []
            while not self._check(T.RBRACKET):
                elements.append(self._expression())
                if not self._match(T.COMMA):
                    break
            self._expect(T.RBRACKET, "Expected ']' to close the array", open_tok=tok)
            return ast.ArrayLiteral(elements, line=tok.line, col=tok.col)
        back = self.pos - 1
        while back >= 0 and self.tokens[back].type == T.NEWLINE:
            back -= 1
        prev = self.tokens[back] if back >= 0 else None
        if prev is not None and prev.type in NEEDS_OPERAND:
            raise self._error(
                f"Incomplete expression: expected a value after '{prev.text}' "
                f"but found {self._describe(tok)}", prev,
                "Add a value after the operator, or remove the operator.")
        if t in (T.RPAREN, T.RBRACKET, T.RBRACE):
            opener = {T.RPAREN: "(", T.RBRACKET: "[", T.RBRACE: "{"}[t]
            raise self._error(
                f"Unexpected '{tok.text}'", tok,
                f"There is no matching '{opener}' before this. Remove the '{tok.text}' "
                f"or add the missing '{opener}'.")
        raise self._error(
            f"Expected an expression but found {self._describe(tok)}", tok,
            "An expression is a value, a variable name, a function call or a calculation.")
