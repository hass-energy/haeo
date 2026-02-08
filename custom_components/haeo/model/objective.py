"""Objective cost structures for multiobjective optimization."""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from highspy import Highs
from highspy.highs import highs_linear_expression

type ObjectiveExpression = highs_linear_expression
type ObjectiveValue = ObjectiveExpression | "ObjectiveCost"


@dataclass(frozen=True, slots=True)
class ObjectiveCost:
    """Container for lexicographic optimization objectives."""

    primary: ObjectiveExpression | None
    secondary: ObjectiveExpression | None

    @property
    def is_empty(self) -> bool:
        """Return True when no objective expressions are set."""
        return self.primary is None and self.secondary is None


def as_objective_cost(value: ObjectiveValue) -> ObjectiveCost:
    """Coerce a value to an ObjectiveCost container."""
    if isinstance(value, ObjectiveCost):
        return value
    return ObjectiveCost(primary=value, secondary=None)


def combine_objectives(costs: Iterable[ObjectiveCost]) -> ObjectiveCost:
    """Combine multiple objective costs into a single ObjectiveCost."""
    primary_terms = [cost.primary for cost in costs if cost.primary is not None]
    secondary_terms = [cost.secondary for cost in costs if cost.secondary is not None]
    return ObjectiveCost(
        primary=_sum_terms(primary_terms),
        secondary=_sum_terms(secondary_terms),
    )


def _sum_terms(terms: Sequence[ObjectiveExpression]) -> ObjectiveExpression | None:
    if not terms:
        return None
    if len(terms) == 1:
        return terms[0]
    return Highs.qsum(terms)


__all__ = [
    "ObjectiveCost",
    "ObjectiveExpression",
    "ObjectiveValue",
    "as_objective_cost",
    "combine_objectives",
]