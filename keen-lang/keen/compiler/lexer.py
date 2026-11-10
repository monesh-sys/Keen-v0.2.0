"""Lexer: converts KEEN source text into a list of tokens."""

from keen.compiler.errors import KeenLexError
from keen.compiler.tokens import KEYWORDS, Token, TokenType as T

TWO_CHAR = {
    "==": T.EQ,
    "!=": T.NE,
    "<=": T.LE,
    ">=": T.GE,
    "+=": T.PLUS_ASSIGN,
    "-=": T.MINUS_ASSIGN,
    "*=": T.STAR_ASSIGN,
    "/=": T.SLASH_ASSIGN,
    "&&": T.AND,
    "||": T.OR,
}

ONE_CHAR = {
    "+": T.PLUS,
    "-": T.MINUS,
    "*": T.STAR,
    "/": T.SLASH,
    "%": T.PERCENT,
    "=": T.ASSIGN,
    "<": T.LT,
    ">": T.GT,
    "(": T.LPAREN,
    ")": T.RPAREN,
    "[": T.LBRACKET,
    "]": T.RBRACKET,
    "{": T.LBRACE,
    "}": T.RBRACE,
    ",": T.COMMA,
    ";": T.SEMICOLON,
    "!": T.NOT,
}

ESCAPES = {"n": "\n", "t": "\t", "r": "\r", "\\": "\\", '"': '"', "'": "'", "0": "\0"}


class Lexer:
    def __init__(self, source):
        self.src = source
        self.pos = 0
        self.line = 1
        self.col = 1
        self.tokens = []
        self.depth = 0  # nesting of () and []; newlines are ignored inside

    # -- helpers -----------------------------------------------------------
    def _peek(self, offset=0):
        i = self.pos + offset
        return self.src[i] if i < len(self.src) else ""

    def _advance(self):
        ch = self.src[self.pos]
        self.pos += 1
        if ch == "\n":
            self.line += 1
            self.col = 1
        else:
            self.col += 1
        return ch

    def _add(self, type_, text, line, col, value=None):
        self.tokens.append(Token(type_, text, line, col, value))

    # -- main loop ---------------------------------------------------------
    def tokenize(self):
        while self.pos < len(self.src):
            ch = self._peek()
            if ch in " \t\r":
                self._advance()
            elif ch == "\n":
                if self.depth == 0 and self.tokens and self.tokens[-1].type != T.NEWLINE:
                    self._add(T.NEWLINE, "\\n", self.line, self.col)
                self._advance()
            elif ch == "/" and self._peek(1) == "/":
                while self.pos < len(self.src) and self._peek() != "\n":
                    self._advance()
            elif ch.isdigit():
                self._number()
            elif ch.isalpha() or ch == "_":
                self._identifier()
            elif ch in "\"'":
                self._string()
            else:
                self._operator()
        if self.depth == 0 and self.tokens and self.tokens[-1].type != T.NEWLINE:
            self._add(T.NEWLINE, "\\n", self.line, self.col)
        self._add(T.EOF, "", self.line, self.col)
        return self.tokens

    # -- token readers -----------------------------------------------------
    def _number(self):
        line, col = self.line, self.col
        start = self.pos
        while self._peek().isdigit() or (self._peek() == "_" and self._peek(1).isdigit()):
            self._advance()
        is_float = False
        if self._peek() == "." and self._peek(1).isdigit():
            is_float = True
            self._advance()
            while self._peek().isdigit() or (self._peek() == "_" and self._peek(1).isdigit()):
                self._advance()
        text = self.src[start:self.pos]
        if self._peek().isalpha() or self._peek() == "_":
            raise KeenLexError(
                f"Invalid number '{text}{self._peek()}...'",
                line, col, "Identifiers cannot start with a digit.",
            )
        clean = text.replace("_", "")
        self._add(T.NUMBER, text, line, col, float(clean) if is_float else int(clean))

    def _identifier(self):
        line, col = self.line, self.col
        start = self.pos
        while self._peek().isalnum() or self._peek() == "_":
            self._advance()
        text = self.src[start:self.pos]
        self._add(KEYWORDS.get(text, T.IDENT), text, line, col)

    def _string(self):
        line, col = self.line, self.col
        quote = self._advance()
        chars = []
        while True:
            if self.pos >= len(self.src) or self._peek() == "\n":
                raise KeenLexError(
                    "Unterminated string", line, col,
                    f"Add a closing {quote} at the end of the string.",
                )
            ch = self._advance()
            if ch == quote:
                break
            if ch == "\\":
                if self.pos >= len(self.src):
                    raise KeenLexError("Unterminated string", line, col)
                esc = self._advance()
                if esc == "u":
                    digits = ""
                    while len(digits) < 4 and self._peek() and self._peek() in "0123456789abcdefABCDEF":
                        digits += self._advance()
                    if len(digits) != 4:
                        raise KeenLexError(
                            "Invalid unicode escape", self.line, self.col - 2 - len(digits),
                            "Use exactly four hex digits, for example \\u00e9.",
                        )
                    chars.append(chr(int(digits, 16)))
                    continue
                if esc not in ESCAPES:
                    raise KeenLexError(
                        f"Unknown escape sequence '\\{esc}'", self.line, self.col - 2,
                        "Supported escapes: \\n \\t \\r \\\\ \\\" \\' \\0",
                    )
                chars.append(ESCAPES[esc])
            else:
                chars.append(ch)
        self._add(T.STRING, quote + "".join(chars) + quote, line, col, "".join(chars))

    def _operator(self):
        line, col = self.line, self.col
        two = self._peek() + self._peek(1)
        if two in TWO_CHAR:
            self._advance()
            self._advance()
            self._add(TWO_CHAR[two], two, line, col)
            return
        ch = self._peek()
        if ch in ONE_CHAR:
            self._advance()
            if ch in "([":
                self.depth += 1
            elif ch in ")]":
                self.depth = max(0, self.depth - 1)
            self._add(ONE_CHAR[ch], ch, line, col)
            return
        if ch == "&":
            raise KeenLexError("Invalid operator '&'", line, col, "Did you mean '&&' (logical and)?")
        if ch == "|":
            raise KeenLexError("Invalid operator '|'", line, col, "Did you mean '||' (logical or)?")
        raise KeenLexError(
            f"Unexpected character '{ch}'", line, col,
            "This character is not part of the KEEN language. Remove it, or put it inside a string.",
        )
