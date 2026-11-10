"""Built-in functions available in every KEEN program (core of keen.io / keen.string later)."""

import math

from keen.compiler.errors import BuiltinError
from keen.runtime.values import BuiltinFunction, is_number, to_display, type_name


def _print(interp, args):
    interp.write(" ".join(to_display(a) for a in args) + "\n")
    return None


def _len(interp, args):
    v = args[0]
    if isinstance(v, (str, list)):
        return len(v)
    raise BuiltinError(f"len() expects a string or array, got {type_name(v)}")


def _str(interp, args):
    return to_display(args[0])


def _int(interp, args):
    v = args[0]
    if isinstance(v, bool):
        raise BuiltinError("int() cannot convert a boolean")
    if isinstance(v, int):
        return v
    if isinstance(v, float):
        if math.isinf(v) or math.isnan(v):
            raise BuiltinError("int() cannot convert infinity or NaN")
        return int(v)
    if isinstance(v, str):
        try:
            return int(v.strip())
        except ValueError:
            raise BuiltinError(f"int() cannot convert the string \"{v}\" to an integer")
    raise BuiltinError(f"int() cannot convert a value of type {type_name(v)}")


def _float(interp, args):
    v = args[0]
    if isinstance(v, bool):
        raise BuiltinError("float() cannot convert a boolean")
    if is_number(v):
        return float(v)
    if isinstance(v, str):
        try:
            return float(v.strip())
        except ValueError:
            raise BuiltinError(f"float() cannot convert the string \"{v}\" to a float")
    raise BuiltinError(f"float() cannot convert a value of type {type_name(v)}")


def _type(interp, args):
    return type_name(args[0])


def _range(interp, args):
    for a in args:
        if isinstance(a, bool) or not isinstance(a, int):
            raise BuiltinError(f"range() expects integers, got {type_name(a)}")
    if len(args) == 1:
        start, stop, step = 0, args[0], 1
    elif len(args) == 2:
        start, stop, step = args[0], args[1], 1
    else:
        start, stop, step = args
    if step == 0:
        raise BuiltinError("range() step cannot be 0")
    r = range(start, stop, step)
    if len(r) > 10_000_000:
        raise BuiltinError("range() is too large (limit is 10,000,000 items)")
    return list(r)


def _push(interp, args):
    if not isinstance(args[0], list):
        raise BuiltinError(f"push() expects an array as its first argument, got {type_name(args[0])}")
    args[0].append(args[1])
    return None


def _input(interp, args):
    if args:
        interp.write(to_display(args[0]))
    return interp.read_line()


BUILTINS = {
    "print": BuiltinFunction("print", _print, 0, None),
    "len": BuiltinFunction("len", _len, 1, 1),
    "str": BuiltinFunction("str", _str, 1, 1),
    "int": BuiltinFunction("int", _int, 1, 1),
    "float": BuiltinFunction("float", _float, 1, 1),
    "type": BuiltinFunction("type", _type, 1, 1),
    "range": BuiltinFunction("range", _range, 1, 3),
    "push": BuiltinFunction("push", _push, 2, 2),
    "input": BuiltinFunction("input", _input, 0, 1),
}

BUILTIN_NAMES = tuple(BUILTINS)
