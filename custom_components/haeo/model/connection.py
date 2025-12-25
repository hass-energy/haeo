"""Base connection class for energy system modeling.

Provides the common interface for all connection types (PowerConnection,
BatteryBalanceConnection, etc.) that link elements together in the network.
"""

from abc import abstractmethod
from typing import Final, Literal

from highspy.highs import HighspyArray

from .element import Element

# Base connection output names - extended by subclasses
type ConnectionOutputName = Literal["connection_time_slice"]
type ConnectionConstraintName = Literal["connection_time_slice"]

CONNECTION_OUTPUT_NAMES: Final[frozenset[ConnectionOutputName]] = frozenset(
    (CONNECTION_TIME_SLICE := "connection_time_slice",)
)


class Connection[OutputNameT: str, ConstraintNameT: str](Element[OutputNameT, ConstraintNameT]):
    """Base class for connections between elements.

    All connection types must implement the power flow interface that allows
    elements to calculate their net power from registered connections.

    The interface provides:
    - source/target: Names of connected elements
    - power_into_source: Effective power flowing into the source element
    - power_into_target: Effective power flowing into the target element

    Implementations handle efficiency internally - the power_into_* methods
    return power after any losses are applied.
    """

    @property
    @abstractmethod
    def source(self) -> str:
        """Return the name of the source element."""

    @property
    @abstractmethod
    def target(self) -> str:
        """Return the name of the target element."""

    @property
    @abstractmethod
    def power_into_source(self) -> HighspyArray:
        """Return effective power flowing into the source element.

        This is the net power the source element receives from this connection,
        after any efficiency losses are applied. Positive values indicate power
        entering the source.
        """

    @property
    @abstractmethod
    def power_into_target(self) -> HighspyArray:
        """Return effective power flowing into the target element.

        This is the net power the target element receives from this connection,
        after any efficiency losses are applied. Positive values indicate power
        entering the target.
        """
