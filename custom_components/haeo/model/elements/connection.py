"""Connection class for energy system modeling.

Provides a basic lossless bidirectional connection between elements.
Subclasses like PowerConnection add efficiency, pricing, and power limits.
"""

from collections.abc import Sequence
from typing import Final, Literal

from highspy import Highs
from highspy.highs import HighspyArray

from custom_components.haeo.model.element import Element

# Base connection output names - extended by subclasses
type ConnectionOutputName = Literal[
    "connection_power_source_target",
    "connection_power_target_source",
]
type ConnectionConstraintName = Literal["connection_time_slice"]

CONNECTION_OUTPUT_NAMES: Final[frozenset[ConnectionOutputName]] = frozenset(
    (
        CONNECTION_POWER_SOURCE_TARGET := "connection_power_source_target",
        CONNECTION_POWER_TARGET_SOURCE := "connection_power_target_source",
    )
)

CONNECTION_TIME_SLICE: Final = "connection_time_slice"


class Connection[OutputNameT: str](Element[OutputNameT]):
    """Lossless bidirectional connection between elements.

    Provides basic power flow variables and the interface for elements to
    calculate their net power from registered connections.

    The interface provides:
    - source/target: Names of connected elements
    - power_into_source: Effective power flowing into the source element
    - power_into_target: Effective power flowing into the target element

    This base class implements lossless connections. Subclasses like
    PowerConnection add efficiency losses, pricing, and power limits.
    """

    def __init__(
        self,
        name: str,
        periods: Sequence[float],
        *,
        solver: Highs,
        source: str,
        target: str,
    ) -> None:
        """Initialize a lossless connection between two elements.

        Args:
            name: Name of the connection
            periods: Sequence of time period durations in hours (one per optimization interval)
            solver: The HiGHS solver instance for creating variables and constraints
            source: Name of the source element
            target: Name of the target element

        """
        super().__init__(name=name, periods=periods, solver=solver)
        n_periods = self.n_periods
        h = solver

        # Store source and target
        self._source = source
        self._target = target

        # Create power variables for bidirectional flow
        self._power_source_target = h.addVariables(n_periods, lb=0, name_prefix=f"{name}_power_st_", out_array=True)
        self._power_target_source = h.addVariables(n_periods, lb=0, name_prefix=f"{name}_power_ts_", out_array=True)

    @property
    def source(self) -> str:
        """Return the name of the source element."""
        return self._source

    @property
    def target(self) -> str:
        """Return the name of the target element."""
        return self._target

    @property
    def power_source_target(self) -> HighspyArray:
        """Return power flowing from source to target for all periods."""
        return self._power_source_target

    @property
    def power_target_source(self) -> HighspyArray:
        """Return power flowing from target to source for all periods."""
        return self._power_target_source

    @property
    def power_into_source(self) -> HighspyArray:
        """Return effective power flowing into the source element.

        For lossless connections: power_target_source - power_source_target
        """
        return self._power_target_source - self._power_source_target

    @property
    def power_into_target(self) -> HighspyArray:
        """Return effective power flowing into the target element.

        For lossless connections: power_source_target - power_target_source
        """
        return self._power_source_target - self._power_target_source
