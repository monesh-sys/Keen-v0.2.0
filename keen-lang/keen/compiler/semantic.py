"""Semantic analyzer: static checks that run before execution.

Checks performed in 0.1.0 (no static type checking yet - see docs/DESIGN_DECISIONS.md):
  * use of undefined variables (with "did you mean" suggestions)
  * use of a variable before its declaration
  * assignment to constants
  * duplicate declarations in the same scope
  * duplicate parameter names
  * 'break' / 'continue' outside a loop
  * 'return' outside a function
"""

import difflib

from keen.compiler import ast_nodes as ast
from keen.compiler.errors import KeenSemanticError


class SemanticAnalyzer:
    def __init__(self, builtin_names=()):
        self.errors = []
        # scope stack: dict name -> is_const. Index 0 holds builtins.
        self.scopes = [{n: True for n in builtin_names}]
        self.loop_depth = 0
        self.fn_depth = 0
        self.deferred = []  # stack of lists of (FnDecl, scope-chain)

    # -- public ------------------------------------------------------------
    def analyze(self, program):
        self.scopes.append({})
        self._block(program.body, new_scope=False)
        return self.errors

    # -- helpers -----------------------------------------------------------
    def _error(self, message, node, hint=None):
        self.errors.append(KeenSemanticError(message, node.line, node.col, hint))

    def _lookup(self, name):
        for scope in reversed(self.scopes):
            if name in scope:
                return scope[name]
        return None

    def _visible_names(self):
        names = set()
        for scope in self.scopes:
            names.update(scope)
        return names

    def _declare(self, name, is_const, node):
        scope = self.scopes[-1]
        if name in scope:
            self._error(f"'{name}' is already declared in this scope", node,
                        "Choose a different name, or assign to the existing variable with '='.")
        else:
            scope[name] = is_const

    def _undefined(self, name, node):
        matches = difflib.get_close_matches(name, self._visible_names(), n=1)
        hint = f"Did you mean '{matches[0]}'?" if matches else None
        self._error(f"Undefined variable '{name}'", node, hint)

    # -- blocks ------------------------------------------------------------
    def _block(self, stmts, new_scope=True):
        if new_scope:
            self.scopes.append({})
        # functions are hoisted: declare their names first
        for s in stmts:
            if isinstance(s, ast.FnDecl):
                self._declare(s.name, False, s)
        self.deferred.append([])
        for s in stmts:
            self._visit(s)
        pending = self.deferred.pop()
        for decl, chain in pending:
            self._function_body(decl, chain)
        if new_scope:
            self.scopes.pop()

    def _function_body(self, decl, chain):
        saved = (self.scopes, self.loop_depth, self.fn_depth)
        self.scopes = list(chain) + [{}]
        self.loop_depth = 0
        self.fn_depth += 1
        for p in decl.params:
            if p in self.scopes[-1]:
                self._error(f"Duplicate parameter '{p}' in function '{decl.name}'", decl)
            else:
                self.scopes[-1][p] = False
        self._block(decl.body, new_scope=False)
        self.scopes, self.loop_depth, self.fn_depth = saved

    # -- statements --------------------------------------------------------
    def _visit(self, node):
        getattr(self, "_visit_" + type(node).__name__)(node)

    def _visit_AppDecl(self, node):
        pass

    def _visit_VarDecl(self, node):
        self._visit(node.value)
        self._declare(node.name, node.is_const, node)

    def _visit_FnDecl(self, node):
        self.deferred[-1].append((node, list(self.scopes)))

    def _visit_Return(self, node):
        if self.fn_depth == 0:
            self._error("'return' can only be used inside a function", node)
        if node.value is not None:
            self._visit(node.value)

    def _visit_If(self, node):
        self._visit(node.condition)
        self._block(node.then_body)
        if node.else_body is not None:
            self._block(node.else_body)

    def _visit_While(self, node):
        self._visit(node.condition)
        self.loop_depth += 1
        self._block(node.body)
        self.loop_depth -= 1

    def _visit_For(self, node):
        self._visit(node.iterable)
        self.scopes.append({node.var: False})
        self.loop_depth += 1
        self._block(node.body, new_scope=False)
        self.loop_depth -= 1
        self.scopes.pop()

    def _visit_Break(self, node):
        if self.loop_depth == 0:
            self._error("'break' can only be used inside a loop", node)

    def _visit_Continue(self, node):
        if self.loop_depth == 0:
            self._error("'continue' can only be used inside a loop", node)

    def _visit_ExprStmt(self, node):
        self._visit(node.expr)

    def _visit_Assign(self, node):
        self._visit(node.value)
        target = node.target
        if isinstance(target, ast.Identifier):
            state = self._lookup(target.name)
            if state is None:
                self._undefined(target.name, target)
            elif state:
                self._error(f"Cannot assign to constant '{target.name}'", target,
                            "Declare it with 'let' instead of 'const' if it needs to change.")
        else:
            self._visit(target)

    # -- expressions -------------------------------------------------------
    def _visit_Literal(self, node):
        pass

    def _visit_Identifier(self, node):
        if self._lookup(node.name) is None:
            self._undefined(node.name, node)

    def _visit_ArrayLiteral(self, node):
        for e in node.elements:
            self._visit(e)

    def _visit_Unary(self, node):
        self._visit(node.operand)

    def _visit_Binary(self, node):
        self._visit(node.left)
        self._visit(node.right)

    _visit_Logical = _visit_Binary

    def _visit_Call(self, node):
        self._visit(node.callee)
        for a in node.args:
            self._visit(a)

    def _visit_Index(self, node):
        self._visit(node.obj)
        self._visit(node.index)
