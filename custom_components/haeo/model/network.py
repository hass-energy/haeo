"""Network class for electrical system modeling and optimization."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
import logging
from typing import Any, cast

from highspy import Highs, HighsModelStatus
from highspy.highs import highs_cons, highs_linear_expression

from .element import Element
from .elements import ELEMENTS, ModelElementType
from .elements.battery import Battery
from .elements.battery_balance_connection import BatteryBalanceConnection
from .elements.connection import Connection

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
    elements: dict[str, Element[Any]] = field(default_factory=dict)
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

    def add(self, spec: Mapping[str, Any] | str, name: str | None = None, **kwargs: Any) -> Element[Any]:
        """Add a new element to the network.

        Accepts either a spec mapping (preferred) or the legacy positional form:
        - add(spec)
        - add(element_type, name, **kwargs)
        """
        # Normalize to spec dict
        if isinstance(spec, Mapping):
            element_type = spec["element_type"]
            elem_name = spec["name"]
            element_kwargs = {k: v for k, v in spec.items() if k not in ("element_type", "name")}
        else:
            # Legacy signature: add(element_type, name, **kwargs)
            element_type = cast("ModelElementType", spec)
            if name is None:
                msg = "Name is required when using legacy add(element_type, name, **kwargs) signature"
                raise ValueError(msg)
            elem_name = name
            element_kwargs = dict(kwargs)

        element_registry = ELEMENTS[element_type]

        if elem_name in self.elements:
            element = self.elements[elem_name]
            if not isinstance(element, element_registry.factory):
                msg = (
                    f"Existing element '{elem_name}' is type {type(element).__name__}, "
                    f"cannot update with type {element_registry.factory.__name__}"
                )
                raise TypeError(msg)

            for param_name, param_value in element_kwargs.items():
                if param_name in {"source", "target", "segments", "fixed_power"}:
                    continue
                # Delegate updates to element's __setitem__ to trigger reactive invalidation
                element[param_name] = param_value
            return element

        element = element_registry.factory(name=elem_name, periods=self.periods, solver=self._solver, **element_kwargs)
        self.elements[elem_name] = element

        # Register connections immediately when adding Connection elements
        # (but not BatteryBalanceConnection - those register themselves via set_battery_references)
        if isinstance(element, Connection) and not isinstance(element, BatteryBalanceConnection):
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

        # Register battery balance connections with their battery sections
        if isinstance(element, BatteryBalanceConnection):
            # BatteryBalanceConnection uses source=upper, target=lower
            upper_element = self.elements.get(element.source)
            lower_element = self.elements.get(element.target)

            if not isinstance(upper_element, Battery):
                msg = f"Upper element '{element.source}' is not a battery"
                raise TypeError(msg)

            if not isinstance(lower_element, Battery):
                msg = f"Lower element '{element.target}' is not a battery"
                raise TypeError(msg)

            element.set_battery_references(upper_element, lower_element)

        return element

    def cost(self) -> highs_linear_expression | None:
        """Return aggregated cost expression from all elements in the network.

        Discovers and calls all element cost() methods, summing their results into
        a single expression. Element costs are cached individually, so this aggregation
        is inexpensive.

        Returns:
            Single aggregated cost expression or None if no costs

        """
        # Collect costs from all elements
        costs = [element_cost for element in self.elements.values() if (element_cost := element.cost()) is not None]

        # Aggregate into a single expression
        if not costs:
            return None
        if len(costs) == 1:
            return costs[0]
        return Highs.qsum(costs)

    def optimize(self) -> float:
        """Solve the optimization problem and return the cost.

        After optimization, access optimized values directly from elements and connections.

        Collects constraints and costs from all elements. Calling element.constraints()
        automatically triggers constraint creation/updating via decorators. On first call,
        this builds all constraints. On subsequent calls, only invalidated constraints are
        rebuilt (those whose TrackedParam dependencies have changed).

        Returns:
            The total optimization cost

        """
        # Validate network before optimization
        self.validate()

        h = self._solver

        # Collect constraints from all elements (reactive - calling triggers decorator lifecycle)
        for element_name, element in self.elements.items():
            try:
                element.constraints()
            except Exception as e:
                msg = f"Failed to apply constraints for element '{element_name}'"
                raise ValueError(msg) from e

        # Get aggregated cost from network (reactive - only rebuilds if any element cost invalidated)
        if (total_cost := self.cost()) is not None:
            h.minimize(total_cost)
        else:
            # No cost terms - just run to check feasibility
            h.run()

        # Check optimization status
        status = h.getModelStatus()
        if status == HighsModelStatus.kOptimal:
            return h.getObjectiveValue()

        msg = f"Optimization failed with status: {h.modelStatusToString(status)}"
        raise ValueError(msg)

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

    def constraints(self) -> dict[str, dict[str, highs_cons | list[highs_cons]]]:
        """Return all constraints from all elements in the network.

        Returns:
            Dictionary mapping element names to their constraint dictionaries.
            Each constraint dictionary maps constraint method names to constraint objects.

        """
        result: dict[str, dict[str, highs_cons | list[highs_cons]]] = {}
        for element_name, element in self.elements.items():
            if element_constraints := element.constraints():
                result[element_name] = element_constraints
        return result
