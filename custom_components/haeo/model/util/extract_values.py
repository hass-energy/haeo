"""Extract numeric values from sequences of HiGHS variables, constraints, and floats."""

from collections.abc import Sequence
from typing import Any

from highspy import Highs
from highspy.highs import highs_cons, highs_linear_expression, highs_var

# Type alias for extractable HiGHS values (excludes str which should pass through)
type HiGHSValue = float | highs_cons | highs_linear_expression | highs_var


def extract_values(sequence: Sequence[Any] | None, solver: Highs | None = None) -> tuple[Any, ...]:
    """Convert a sequence of HiGHS types to resolved values.

    Args:
        sequence: A sequence of HiGHS variables, constraints, expressions, floats, or other values.
            - highs_cons: Extracts shadow price via solver.constrDual() (defaults to 0.0 if solver not provided)
            - highs_var/highs_linear_expression: Uses solver.val() to resolve
            - float/int: Converts to float
            - Other types (e.g., str): Passes through unchanged
        solver: The HiGHS solver instance to use for value extraction (required after optimization)

    Returns:
        A tuple of resolved values.

    """
    if sequence is None:
        return ()

    resolved: list[Any] = []
    for item in sequence:
        if isinstance(item, highs_cons):
            # Extract shadow price from constraint
            if solver is not None:
                resolved.append(solver.constrDual(item))
            else:
                resolved.append(0.0)
        elif isinstance(item, (highs_var, highs_linear_expression)):
            # Resolve HiGHS variable/expression to float
            if solver is not None:
                resolved.append(float(solver.val(item)))
            else:
                resolved.append(0.0)
        elif isinstance(item, (int, float)) and not isinstance(item, bool):
            # Convert numeric types to float
            resolved.append(float(item))
        else:
            # Pass through other types unchanged (e.g., strings)
            resolved.append(item)
    return tuple(resolved)
