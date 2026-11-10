"""Tree-walking interpreter for KEEN."""

import difflib
import sys

from keen.compiler import ast_nodes as ast
from keen.compiler.errors import BuiltinError, KeenRuntimeError
from keen.runtime.builtins import BUILTINS
from keen.runtime.values import (
    BuiltinFunction, KeenFunction, is_number, is_truthy, keen_equals, type_name,
)


class BreakSignal(Exception):
    pass


class ContinueSignal(Exception):
    pass


class ReturnSignal(Exception):
    def __init__(self, value):
        self.value = value


class Environment:
    def __init__(self, parent=None):
        self.parent = parent
        self.vars = {}
        self.consts = set()

    def define(self, name, value, is_const=False):
        self.vars[name] = value
        if is_const:
            self.consts.add(name)

    def find(self, name):
        env = self
        while env is not None:
            if name in env.vars:
                return env
            env = env.parent
        return None

    def all_names(self):
        names, env = set(), self
        while env is not None:
            names.update(env.vars)
            env = env.parent
        return names


class Interpreter:
    def __init__(self, write=None, read_line=None, max_call_depth=1000, tracer=None):
        self.tracer = tracer  # optional keen.runtime.debug.Tracer
        self.call_stack = []  # [(function name, call line, call column)]
        self.write = write or sys.stdout.write
        self.read_line = read_line or (lambda: sys.stdin.readline().rstrip("\n"))
        self.max_call_depth = max_call_depth
        self.call_depth = 0
        self.app_name = None
        self.builtin_env = Environment()
        for name, fn in BUILTINS.items():
            self.builtin_env.define(name, fn, is_const=True)
        self.globals = Environment(self.builtin_env)

    # -- entry point -------------------------------------------------------
    def run(self, program):
        try:
            self._exec_body(program.body, self.globals)
        except (BreakSignal, ContinueSignal):
            raise KeenRuntimeError("'break'/'continue' used outside a loop")
        except ReturnSignal:
            raise KeenRuntimeError("'return' used outside a function")
        except KeenRuntimeError as e:
            if e.stack is None:
                e.stack = []
            if self.tracer is not None:
                self.tracer.on_error(e)
            raise

    # -- helpers -----------------------------------------------------------
    @staticmethod
    def _err(message, node, hint=None):
        return KeenRuntimeError(message, node.line, node.col, hint)

    def _declare(self, env, name, value, is_const, node):
        if name in env.vars:
            raise self._err(f"'{name}' is already declared in this scope", node)
        env.define(name, value, is_const)

    def _exec_body(self, stmts, env):
        for s in stmts:  # hoist functions
            if isinstance(s, ast.FnDecl):
                self._declare(env, s.name, KeenFunction(s, env), False, s)
        for s in stmts:
            self._exec(s, env)

    def _exec(self, node, env):
        if self.tracer is not None and not isinstance(node, ast.FnDecl):
            self.tracer.on_statement(node, self.call_depth)
        getattr(self, "_exec_" + type(node).__name__)(node, env)

    def _eval(self, node, env):
        return getattr(self, "_eval_" + type(node).__name__)(node, env)

    # -- statements --------------------------------------------------------
    def _exec_AppDecl(self, node, env):
        self.app_name = node.name

    def _exec_VarDecl(self, node, env):
        value = self._eval(node.value, env)
        self._declare(env, node.name, value, node.is_const, node)
        if self.tracer is not None:
            self.tracer.on_variable(node.name, value)

    def _exec_FnDecl(self, node, env):
        pass  # already hoisted by _exec_body

    def _exec_Return(self, node, env):
        raise ReturnSignal(None if node.value is None else self._eval(node.value, env))

    def _exec_If(self, node, env):
        if is_truthy(self._eval(node.condition, env)):
            self._exec_body(node.then_body, Environment(env))
        elif node.else_body is not None:
            self._exec_body(node.else_body, Environment(env))

    def _exec_While(self, node, env):
        while is_truthy(self._eval(node.condition, env)):
            try:
                self._exec_body(node.body, Environment(env))
            except ContinueSignal:
                continue
            except BreakSignal:
                break

    def _exec_For(self, node, env):
        iterable = self._eval(node.iterable, env)
        if isinstance(iterable, list):
            items = list(iterable)
        elif isinstance(iterable, str):
            items = list(iterable)
        else:
            raise self._err(
                f"Cannot loop over a value of type {type_name(iterable)}", node.iterable,
                "'for' works on arrays and strings. For numbers use range(), e.g. for i in range(0, 5).",
            )
        for item in items:
            loop_env = Environment(env)
            loop_env.define(node.var, item)
            try:
                self._exec_body(node.body, loop_env)
            except ContinueSignal:
                continue
            except BreakSignal:
                break

    def _exec_Break(self, node, env):
        raise BreakSignal()

    def _exec_Continue(self, node, env):
        raise ContinueSignal()

    def _exec_ExprStmt(self, node, env):
        self._eval(node.expr, env)

    def _exec_Assign(self, node, env):
        target = node.target
        if isinstance(target, ast.Identifier):
            owner = env.find(target.name)
            if owner is None:
                raise self._undefined(target.name, target, env)
            if target.name in owner.consts:
                raise self._err(f"Cannot assign to constant '{target.name}'", target)
            value = self._eval(node.value, env)
            if node.op != "=":
                value = self._binary(node.op[0], owner.vars[target.name], value, node)
            owner.vars[target.name] = value
            if self.tracer is not None:
                self.tracer.on_variable(target.name, value)
        else:
            container = self._eval(target.obj, env)
            index = self._eval(target.index, env)
            idx = self._check_index(container, index, target, for_store=True)
            value = self._eval(node.value, env)
            if node.op != "=":
                value = self._binary(node.op[0], container[idx], value, node)
            container[idx] = value
            if self.tracer is not None:
                base = target.obj.name if isinstance(target.obj, ast.Identifier) else ""
                self.tracer.on_variable(f"{base}[{idx}]", value)

    # -- expressions -------------------------------------------------------
    def _eval_Literal(self, node, env):
        return node.value

    def _undefined(self, name, node, env):
        matches = difflib.get_close_matches(name, env.all_names(), n=1)
        hint = f"Did you mean '{matches[0]}'?" if matches else None
        return self._err(f"Undefined variable '{name}'", node, hint)

    def _eval_Identifier(self, node, env):
        owner = env.find(node.name)
        if owner is None:
            raise self._undefined(node.name, node, env)
        return owner.vars[node.name]

    def _eval_ArrayLiteral(self, node, env):
        return [self._eval(e, env) for e in node.elements]

    def _eval_Unary(self, node, env):
        v = self._eval(node.operand, env)
        if node.op == "not":
            return not is_truthy(v)
        if not is_number(v):
            raise self._err(f"Cannot negate a value of type {type_name(v)}", node,
                            "The unary '-' only works on integers and floats.")
        return -v

    def _eval_Logical(self, node, env):
        # Short-circuit evaluation; the result is always a boolean (since 0.2.0).
        left = is_truthy(self._eval(node.left, env))
        if node.op == "and":
            return left and is_truthy(self._eval(node.right, env))
        return left or is_truthy(self._eval(node.right, env))

    def _eval_Binary(self, node, env):
        left = self._eval(node.left, env)
        right = self._eval(node.right, env)
        return self._binary(node.op, left, right, node)

    def _binary(self, op, l, r, node):
        if op == "+":
            if is_number(l) and is_number(r):
                return l + r
            if isinstance(l, str) and isinstance(r, str):
                return l + r
            if isinstance(l, list) and isinstance(r, list):
                return l + r
            hint = None
            if isinstance(l, str) or isinstance(r, str):
                hint = "Use str(value) to convert a value to a string before joining."
            raise self._err(f"Cannot add {type_name(l)} and {type_name(r)}", node, hint)
        if op in ("-", "*", "/", "%"):
            if not (is_number(l) and is_number(r)):
                hint = None
                if isinstance(l, str) or isinstance(r, str):
                    hint = "Use int() or float() to convert a string to a number first."
                raise self._err(
                    f"Operator '{op}' needs two numbers, got {type_name(l)} and {type_name(r)}",
                    node, hint)
            if op == "-":
                return l - r
            if op == "*":
                return l * r
            if r == 0:
                raise self._err("Division by zero" if op == "/" else "Modulo by zero", node)
            return l / r if op == "/" else l % r
        if op in ("<", "<=", ">", ">="):
            ok = (is_number(l) and is_number(r)) or (isinstance(l, str) and isinstance(r, str))
            if not ok:
                raise self._err(f"Cannot compare {type_name(l)} with {type_name(r)}", node,
                                "Comparison works on two numbers or two strings. "
                                "Note that 'a < b < c' is not a chained comparison; use 'a < b && b < c'.")
            return {"<": l < r, "<=": l <= r, ">": l > r, ">=": l >= r}[op]
        if op == "==":
            return keen_equals(l, r)
        if op == "!=":
            return not keen_equals(l, r)
        raise self._err(f"Unknown operator '{op}'", node)

    def _check_index(self, container, index, node, for_store=False):
        if not isinstance(container, (list, str)):
            raise self._err(f"Cannot index a value of type {type_name(container)}", node)
        if for_store and isinstance(container, str):
            raise self._err("Strings are immutable; you cannot assign to a character", node)
        if isinstance(index, bool) or not isinstance(index, int):
            raise self._err(f"Index must be an integer, got {type_name(index)}", node)
        if not -len(container) <= index < len(container):
            raise self._err(
                f"Index {index} is out of range (length is {len(container)})", node)
        return index

    def _eval_Index(self, node, env):
        container = self._eval(node.obj, env)
        index = self._eval(node.index, env)
        return container[self._check_index(container, index, node)]

    def _eval_Call(self, node, env):
        callee = self._eval(node.callee, env)
        args = [self._eval(a, env) for a in node.args]
        if isinstance(callee, (KeenFunction, BuiltinFunction)):
            lo, hi = callee.arity
            if len(args) < lo or (hi is not None and len(args) > hi):
                expected = str(lo) if lo == hi else (f"at least {lo}" if hi is None else f"{lo} to {hi}")
                raise self._err(
                    f"'{callee.name}' expects {expected} argument(s) but got {len(args)}", node)
        if isinstance(callee, BuiltinFunction):
            try:
                return callee.func(self, args)
            except BuiltinError as e:
                raise self._err(str(e), node)
        if isinstance(callee, KeenFunction):
            return self._call_function(callee, args, node)
        what = f"'{node.callee.name}'" if isinstance(node.callee, ast.Identifier) else "This value"
        raise self._err(f"{what} is not a function (it is {type_name(callee)})", node)

    def _call_function(self, fn, args, node):
        if self.call_depth >= self.max_call_depth:
            raise self._err(
                f"Maximum call depth ({self.max_call_depth}) exceeded in '{fn.name}'", node,
                "This usually means a function calls itself without a stopping condition.")
        env = Environment(fn.closure)
        for name, value in zip(fn.decl.params, args):
            env.define(name, value)
        if self.tracer is not None:
            self.tracer.on_call(fn.name, args, self.call_depth)
        self.call_depth += 1
        self.call_stack.append((fn.name, node.line, node.col))
        result = None
        try:
            self._exec_body(fn.decl.body, env)
        except ReturnSignal as r:
            result = r.value
        except KeenRuntimeError as e:
            if e.stack is None:  # first frame to see the error records the stack
                e.stack = list(self.call_stack)
            raise
        finally:
            self.call_stack.pop()
            self.call_depth -= 1
        if self.tracer is not None:
            self.tracer.on_return(fn.name, result, self.call_depth)
        return result
