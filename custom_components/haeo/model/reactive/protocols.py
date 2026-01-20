"""Protocols for reactive infrastructure type hints."""

from typing import Protocol, runtime_checkable

from highspy import Highs


@runtime_checkable
class ReactiveHost(Protocol):
    """Protocol for objects that can host reactive decorators.

    Any class using @constraint, @cost, or TrackedParam must satisfy this protocol.
    Both Element and Segment classes implement this protocol.

    Required attributes:
        _solver: HiGHS solver instance for constraint/cost operations

    """

    _solver: Highs
