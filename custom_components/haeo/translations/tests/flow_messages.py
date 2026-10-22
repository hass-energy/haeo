"""Find the errors, abort reasons, and steps a flow handler can show by reading the code its steps reach.

Starting from the flow's own ``async_step_*`` methods, this follows every call
to a method of the flow or to a function its modules define, and collects:

- errors: string constants stored into a mapping named ``errors``
- aborts: ``reason`` passed to ``async_abort``, and the first argument of ``AbortFlow``
- steps: ``step_id`` passed to ``async_show_form``

A name used for one of these resolves to the string constants assigned to it in
the same function, its default as a parameter, or a module-level constant.
Only code outside Home Assistant, and Home Assistant's flow base classes, are
followed, so a helper a flow inherits but never calls does not count.
"""

import ast
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from functools import cache
import inspect
import textwrap
import types

# Home Assistant's flow base classes, whose helpers return abort reasons such as reconfigure_successful
HOME_ASSISTANT_FLOW_MODULES = frozenset({"homeassistant.config_entries", "homeassistant.data_entry_flow"})


@dataclass
class FlowMessages:
    """The strings a flow can show, by kind."""

    errors: set[str] = field(default_factory=set)
    aborts: set[str] = field(default_factory=set)
    steps: set[str] = field(default_factory=set)


type Function = Callable[..., object]


def _is_integration_code(function: Function) -> bool:
    return not function.__module__.startswith("homeassistant.")


def _unwrap(value: object) -> Function | None:
    """Return the function to follow for a value, or None for anything outside the followed code."""
    if isinstance(value, (staticmethod, classmethod)):
        value = value.__func__
    if callable(value):
        value = inspect.unwrap(value)
    if isinstance(value, types.FunctionType) and (
        _is_integration_code(value) or value.__module__ in HOME_ASSISTANT_FLOW_MODULES
    ):
        return value
    return None


@cache
def _tree(function: Function) -> ast.FunctionDef | ast.AsyncFunctionDef:
    node = ast.parse(textwrap.dedent(inspect.getsource(function))).body[0]
    if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        msg = f"{function.__qualname__} is not a function definition"
        raise TypeError(msg)
    return node


def _strings(node: ast.expr | None, function: Function, tree: ast.FunctionDef | ast.AsyncFunctionDef) -> set[str]:
    """Return the string constants an expression can hold."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return {node.value}
    if not isinstance(node, ast.Name):
        return set()
    found = {
        assigned.value.value
        for assigned in ast.walk(tree)
        if isinstance(assigned, ast.Assign)
        and isinstance(assigned.value, ast.Constant)
        and isinstance(assigned.value.value, str)
        and any(isinstance(target, ast.Name) and target.id == node.id for target in assigned.targets)
    }
    arguments = tree.args
    positional = [*arguments.posonlyargs, *arguments.args]
    defaults = [
        *zip(positional[len(positional) - len(arguments.defaults) :], arguments.defaults, strict=True),
        *zip(arguments.kwonlyargs, arguments.kw_defaults, strict=True),
    ]
    found.update(
        default.value
        for argument, default in defaults
        if argument.arg == node.id and isinstance(default, ast.Constant) and isinstance(default.value, str)
    )
    if isinstance(value := function.__globals__.get(node.id), str):
        found.add(value)
    return found


def _callees(node: ast.AST, function: Function, flow: type) -> Iterator[Function]:
    """Yield the functions an expression in a flow method may call."""
    if isinstance(node, ast.Attribute) and (
        (isinstance(node.value, ast.Name) and node.value.id in {"self", "cls"})
        or (
            isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name) and node.value.func.id == "super"
        )
    ):
        for owner in flow.__mro__:
            if (callee := _unwrap(vars(owner).get(node.attr))) is not None:
                yield callee
    elif isinstance(node, ast.Name) and (callee := _unwrap(function.__globals__.get(node.id))) is not None:
        yield callee


def _keyword(call: ast.Call, name: str) -> ast.expr | None:
    return next((keyword.value for keyword in call.keywords if keyword.arg == name), None)


def _call_name(call: ast.Call) -> str | None:
    if isinstance(call.func, ast.Attribute):
        return call.func.attr
    if isinstance(call.func, ast.Name):
        return call.func.id
    return None


def flow_messages(flow: type) -> FlowMessages:
    """Return the errors, abort reasons, and steps a flow handler can show."""
    messages = FlowMessages()
    pending = [
        function
        for name in dir(flow)
        if name.startswith("async_step_")
        and (function := _unwrap(inspect.getattr_static(flow, name))) is not None
        and _is_integration_code(function)
    ]
    seen: set[Function] = set()
    while pending:
        function = pending.pop()
        if function in seen:
            continue
        seen.add(function)
        tree = _tree(function)
        for node in ast.walk(tree):
            pending.extend(_callees(node, function, flow))
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if (
                        isinstance(target, ast.Subscript)
                        and isinstance(target.value, ast.Name)
                        and target.value.id == "errors"
                    ):
                        messages.errors |= _strings(node.value, function, tree)
            if isinstance(node, ast.Call):
                match _call_name(node):
                    case "async_abort":
                        messages.aborts |= _strings(_keyword(node, "reason"), function, tree)
                    case "AbortFlow" if node.args:
                        messages.aborts |= _strings(node.args[0], function, tree)
                    case "async_show_form":
                        messages.steps |= _strings(_keyword(node, "step_id"), function, tree)
                    case _:
                        pass
    return messages
