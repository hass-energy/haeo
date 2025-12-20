"""Network class for electrical system modeling and optimization."""

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
import logging
from typing import Any

from highspy import Highs, HighsModelStatus
from highspy.highs import highs_cons

from .battery import Battery
from .connection import Connection
from .element import Element
from .node import Node
from .source_sink import SourceSink

_LOGGER = logging.getLogger(__name__)


@dataclass
class Network:
    """Network class for electrical system modeling.

    All values use kW-based units for numerical stability:
    - Power: kW
    - Energy: kWh
    - Time: hours (variable-width intervals)
    - Price: $/kWh

    Note: Periods should be provided in hours (conversion from seconds happens at the data loading boundary layer).
    """

    name: str
    periods: Sequence[float]  # Period durations in hours (one per optimization interval)
    elements: dict[str, Element[Any, Any]] = field(default_factory=dict)
    required_energy: Sequence[float] | None = None  # kWh at each timestep boundary, available to model elements
    blackout_protection: bool = False  # Enable blackout protection constraints
    net_power: Sequence[float] | None = None  # kW per period, positive = surplus, negative = deficit
    _solver: Highs = field(default_factory=Highs, repr=False)

    def __post_init__(self) -> None:
        """Set up the solver with logging callback."""
        # Redirect HiGHS logging to Python logger at debug level
        self._solver.cbLogging += self._log_callback

        # Disable console output since we're capturing via callback
        output_off = False
        self._solver.setOptionValue("output_flag", output_off)
        self._solver.setOptionValue("log_to_console", output_off)

    @staticmethod
    def _log_callback(_log_type: int, message: str) -> None:
        """Log HiGHS messages to Python logger."""
        if message:
            _LOGGER.debug("HiGHS: %s", message.rstrip())

    @property
    def n_periods(self) -> int:
        """Return the number of optimization periods."""
        return len(self.periods)

    def add(self, element_type: str, name: str, **kwargs: object) -> Element[Any, Any]:
        """Add an element to the network by type.

        Args:
            element_type: Type of element as a string
            name: Name of the element
            **kwargs: Additional arguments specific to the element type

        Returns:
            The created element

        """
        factories: dict[str, Callable[..., Element[Any, Any]]] = {
            "battery": Battery,
            "connection": Connection,
            "source_sink": SourceSink,
            "node": Node,
        }

        factory = factories[element_type.lower()]
        element = factory(name=name, periods=self.periods, solver=self._solver, **kwargs)
        self.elements[name] = element

        # Register connections immediately when adding Connection elements
        if isinstance(element, Connection):
            # Get source and target elements
            source_element = self.elements.get(element.source)
            target_element = self.elements.get(element.target)

            if source_element is not None:
                source_element.register_connection(element, "source")
            else:
                msg = f"Failed to register connection {name} with source {element.source}: Not found or invalid"
                raise ValueError(msg)

            if target_element is not None:
                target_element.register_connection(element, "target")
            else:
                msg = f"Failed to register connection {name} with target {element.target}: Not found or invalid"
                raise ValueError(msg)

        return element

    def optimize(self) -> float:
        """Solve the optimization problem and return the cost.

        After optimization, access optimized values directly from elements and connections.

        Returns:
            The total optimization cost

        """
        # Validate network before optimization
        self.validate()

        h = self._solver

        # Build constraints for all elements
        for element_name, element in self.elements.items():
            try:
                element.build_constraints()
            except Exception as e:
                msg = f"Failed to build constraints for element '{element_name}'"
                raise ValueError(msg) from e

        # Add blackout protection constraint if enabled
        # This ensures total battery stored energy >= required_energy at each timestep
        if self.blackout_protection and self.required_energy is not None:
            self._add_blackout_protection_constraints()

        # Collect all cost expressions from elements and set objective
        costs = [c for element in self.elements.values() for c in element.cost()]

        # Add blackout protection penalty cost if applicable
        if hasattr(self, "_blackout_shortfall"):
            # Penalty cost: $1000/kWh for energy below required
            # This makes it extremely expensive to be below required_energy
            blackout_penalty = 1000.0
            for t in range(1, self.n_periods + 1):
                costs.append(blackout_penalty * self._blackout_shortfall[t])

        if costs:
            h.minimize(Highs.qsum(costs))
        else:
            # No cost terms - just run to check feasibility
            h.run()

        # Check optimization status
        status = h.getModelStatus()
        if status == HighsModelStatus.kOptimal:
            return h.getObjectiveValue()

        msg = f"Optimization failed with status: {h.modelStatusToString(status)}"
        raise ValueError(msg)

    def _add_blackout_protection_constraints(self) -> None:
        """Add soft penalty for battery energy below required_energy.

        Instead of a hard constraint (which would be infeasible if starting
        below required_energy), we add a penalty cost for the shortfall.
        This works together with the undercharge_cost mechanism.

        The penalty is proportional to how much energy is below required_energy.
        """
        if self.required_energy is None:
            return

        h = self._solver

        # Find all battery elements (excluding internal sections, use top-level batteries)
        # Battery sections are named like "Battery:normal", "Battery:undercharge", etc.
        # We need to sum all sections that belong to the same physical battery
        battery_sections: dict[str, list[Battery]] = {}
        for element_name, element in self.elements.items():
            if isinstance(element, Battery):
                # Extract base battery name (before the first colon)
                base_name = element_name.split(":")[0]
                if base_name not in battery_sections:
                    battery_sections[base_name] = []
                battery_sections[base_name].append(element)

        # For each physical battery, add soft penalty for energy below required
        for sections in battery_sections.values():
            if not sections:
                continue

            # Create slack variables for shortfall at each timestep
            # shortfall[t] >= required_energy[t] - total_stored[t]
            # shortfall[t] >= 0
            shortfall = h.addVariables(self.n_periods + 1, lb=0.0, name_prefix="blackout_shortfall_", out_array=True)

            # Add constraints: shortfall[t] >= required[t] - stored[t]
            # stored_energy has n_periods + 1 values (fence-post for energy boundaries)
            for t in range(1, self.n_periods + 1):
                total_stored = h.qsum(section.stored_energy[t] for section in sections)
                # Total capacity at this timestep (sum of section capacities)
                total_capacity = sum(section.capacity[t] for section in sections)
                # Cap required_energy at total capacity
                min_required = min(self.required_energy[t], total_capacity)
                # shortfall >= required - stored (will be 0 when stored >= required)
                h.addConstr(shortfall[t] >= min_required - total_stored)

            # Store shortfall variables for cost calculation
            self._blackout_shortfall = shortfall

    def validate(self) -> None:
        """Validate the network."""
        # Check that all connection elements have valid source and target elements
        for element in self.elements.values():
            if isinstance(element, Connection):
                if element.source not in self.elements:
                    msg = f"Source element '{element.source}' not found"
                    raise ValueError(msg)
                if element.target not in self.elements:
                    msg = f"Target element '{element.target}' not found"
                    raise ValueError(msg)
                if isinstance(self.elements[element.source], Connection):
                    msg = f"Source element '{element.source}' is a connection"
                    raise ValueError(msg)  # noqa: TRY004 value error is appropriate here
                if isinstance(self.elements[element.target], Connection):
                    msg = f"Target element '{element.target}' is a connection"
                    raise ValueError(msg)  # noqa: TRY004 value error is appropriate here

    def constraints(self) -> list[highs_cons]:
        """Return all constraints from all elements in the network.

        Returns:
            A flat list of all constraints from all elements.

        """
        result: list[highs_cons] = []
        for element_name, element in self.elements.items():
            try:
                result.extend(element.constraints())
            except Exception as e:
                msg = f"Failed to get constraints for element '{element_name}'"
                raise ValueError(msg) from e
        return result
