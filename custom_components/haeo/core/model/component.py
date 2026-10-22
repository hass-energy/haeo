"""Base for the parts of the model that declare constraints, costs, and outputs with reactive decorators."""

from collections.abc import Iterator

from .linear import LinearArray, total
from .reactive import OutputMethod, ReactiveConstraint, ReactiveCost, applied_constraint, cost
from .solver import Solver
from .util.solver_rows import RowIndices


class ModelComponent:
    """A part of the model whose constraints, costs, and outputs are found by reflection.

    Elements and connection segments both declare ``@constraint``, ``@cost`` and
    ``@output`` methods, and this class discovers and calls them.
    """

    _solver: Solver

    def constraints(self) -> dict[str, RowIndices]:
        """Apply every ``@constraint`` method and return the rows of those that currently bind.

        Calling a constraint method creates or updates its rows in the solver.
        """
        result: dict[str, RowIndices] = {}
        for name in dir(type(self)):
            if isinstance(getattr(type(self), name, None), ReactiveConstraint):
                getattr(self, name)()
                if (rows := applied_constraint(self, name)) is not None:
                    result[name] = rows
        return result

    def declared_outputs(self) -> Iterator[tuple[str, OutputMethod[object] | ReactiveConstraint[object]]]:
        """Yield each ``@output`` method and constraint by the output name it reports under.

        A constraint reports its shadow prices under its own name when declared with ``output=True``.
        """
        for name in dir(type(self)):
            attr = getattr(type(self), name, None)
            if isinstance(attr, OutputMethod):
                yield attr.output_name, attr
            elif isinstance(attr, ReactiveConstraint):
                yield name, attr

    @cost
    def cost(self) -> LinearArray | None:
        """Return the sum of every other ``@cost`` method, or None when there are none.

        Cached by the ``@cost`` decorator, so it only recomputes when one of them changes.
        """
        costs = (
            getattr(self, name)()
            for name in dir(type(self))
            if name != "cost" and isinstance(getattr(type(self), name, None), ReactiveCost)
        )
        return total(costs)


__all__ = ["ModelComponent"]
