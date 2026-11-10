"""AST node definitions for KEEN."""

from dataclasses import dataclass, field
from typing import Any, List, Optional


@dataclass(kw_only=True)
class Node:
    line: int = 0
    col: int = 0


# ---- statements -----------------------------------------------------------
@dataclass
class Program(Node):
    body: List[Node]


@dataclass
class AppDecl(Node):
    name: str


@dataclass
class VarDecl(Node):
    name: str
    value: Node
    is_const: bool = False


@dataclass
class FnDecl(Node):
    name: str
    params: List[str]
    body: List[Node]


@dataclass
class Return(Node):
    value: Optional[Node] = None


@dataclass
class If(Node):
    condition: Node
    then_body: List[Node]
    else_body: Optional[List[Node]] = None


@dataclass
class While(Node):
    condition: Node
    body: List[Node]


@dataclass
class For(Node):
    var: str
    iterable: Node
    body: List[Node]


@dataclass
class Break(Node):
    pass


@dataclass
class Continue(Node):
    pass


@dataclass
class ExprStmt(Node):
    expr: Node


@dataclass
class Assign(Node):
    target: Node          # Identifier or Index
    op: str               # '=', '+=', '-=', '*=', '/='
    value: Node


# ---- expressions ----------------------------------------------------------
@dataclass
class Literal(Node):
    value: Any


@dataclass
class Identifier(Node):
    name: str


@dataclass
class ArrayLiteral(Node):
    elements: List[Node]


@dataclass
class Unary(Node):
    op: str               # '-' or 'not'
    operand: Node


@dataclass
class Binary(Node):
    op: str
    left: Node
    right: Node


@dataclass
class Logical(Node):
    op: str               # 'and' / 'or'
    left: Node
    right: Node


@dataclass
class Call(Node):
    callee: Node
    args: List[Node]


@dataclass
class Index(Node):
    obj: Node
    index: Node
