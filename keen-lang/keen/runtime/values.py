"""Runtime value model for KEEN.

KEEN values are represented with native Python objects:
    integer -> int, float -> float, string -> str, boolean -> bool,
    null -> None, array -> list, function -> KeenFunction / BuiltinFunction
"""


class KeenFunction:
    def __init__(self, decl, closure):
        self.decl = decl
        self.closure = closure

    @property
    def name(self):
        return self.decl.name

    @property
    def arity(self):
        return (len(self.decl.params), len(self.decl.params))


class BuiltinFunction:
    def __init__(self, name, func, min_args, max_args):
        self.name = name
        self.func = func
        self.min_args = min_args
        self.max_args = max_args  # None = variadic

    @property
    def arity(self):
        return (self.min_args, self.max_args)


def is_number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def type_name(v):
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "boolean"
    if isinstance(v, int):
        return "integer"
    if isinstance(v, float):
        return "float"
    if isinstance(v, str):
        return "string"
    if isinstance(v, list):
        return "array"
    if isinstance(v, (KeenFunction, BuiltinFunction)):
        return "function"
    return type(v).__name__


def is_truthy(v):
    """false, null, 0, 0.0, "" and [] are falsy; everything else is truthy."""
    if v is None or v is False:
        return False
    if is_number(v):
        return v != 0
    if isinstance(v, (str, list)):
        return len(v) > 0
    return True


def keen_equals(a, b):
    if is_number(a) and is_number(b):
        return a == b
    if isinstance(a, bool) or isinstance(b, bool):
        return isinstance(a, bool) and isinstance(b, bool) and a == b
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(keen_equals(x, y) for x, y in zip(a, b))
    if type(a) is not type(b):
        return False
    return a == b


def to_display(v, nested=False):
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return str(v)
    if isinstance(v, str):
        if nested:
            return '"' + v.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n") + '"'
        return v
    if isinstance(v, list):
        return "[" + ", ".join(to_display(x, True) for x in v) + "]"
    if isinstance(v, (KeenFunction, BuiltinFunction)):
        return f"<fn {v.name}>"
    return str(v)
