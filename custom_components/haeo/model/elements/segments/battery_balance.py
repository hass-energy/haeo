"""Battery balance segment for energy redistribution between battery sections."""

from typing import Any, Final, Literal, NotRequired

from highspy import Highs
from highspy.highs import HighspyArray, highs_linear_expression
import numpy as np
from numpy.typing import NDArray
from typing_extensions import TypedDict

from custom_components.haeo.model.const import OutputType
from custom_components.haeo.model.output_data import OutputData
from custom_components.haeo.model.reactive import constraint, cost, output

from .segment import Segment


class BatteryBalanceSegmentSpec(TypedDict):
    """Specification for creating a BatteryBalanceSegment."""

    segment_type: Literal["battery_balance"]
    slack_penalty: NotRequired[float | None]


type BatteryBalanceOutputName = Literal[
    "balance_power_down",
    "balance_power_up",
    "balance_unmet_demand",
    "balance_absorbed_excess",
    "balance_down_lower_bound",
    "balance_down_slack_bound",
    "balance_up_upper_bound",
    "balance_up_slack_bound",
]

BALANCE_POWER_DOWN: Final = "balance_power_down"
BALANCE_POWER_UP: Final = "balance_power_up"
BALANCE_UNMET_DEMAND: Final = "balance_unmet_demand"
BALANCE_ABSORBED_EXCESS: Final = "balance_absorbed_excess"


class BatteryBalanceSegment(Segment):
    """Lossless energy redistribution between adjacent battery sections."""

    DEFAULT_SLACK_PENALTY: Final[float] = 100.0

    def __init__(
        self,
        segment_id: str,
        n_periods: int,
        periods: NDArray[np.floating[Any]],
        solver: Highs,
        *,
        spec: BatteryBalanceSegmentSpec,
    ) -> None:
        """Initialize the balance segment variables."""
        super().__init__(segment_id, n_periods, periods, solver)
        self._slack_penalty = spec.get("slack_penalty") or self.DEFAULT_SLACK_PENALTY

        self._power_down = solver.addVariables(n_periods, lb=0, name_prefix=f"{segment_id}_power_down_", out_array=True)
        self._power_up = solver.addVariables(n_periods, lb=0, name_prefix=f"{segment_id}_power_up_", out_array=True)
        self.unmet_demand = solver.addVariables(
            n_periods, lb=0, name_prefix=f"{segment_id}_unmet_demand_", out_array=True
        )
        self.absorbed_excess = solver.addVariables(
            n_periods, lb=0, name_prefix=f"{segment_id}_absorbed_excess_", out_array=True
        )

    def _get_batteries(self) -> tuple[Any, Any]:
        if (
            self.source_element is None
            or self.target_element is None
            or not hasattr(self.source_element, "stored_energy")
            or not hasattr(self.source_element, "capacity")
            or not hasattr(self.target_element, "stored_energy")
            or not hasattr(self.target_element, "capacity")
        ):
            msg = f"Battery references not set for {self.segment_id}"
            raise ValueError(msg)
        return self.source_element, self.target_element

    def set_endpoints(self, source_element: Any, target_element: Any) -> None:
        """Validate and store connected battery endpoints."""
        if not hasattr(source_element, "stored_energy") or not hasattr(source_element, "capacity"):
            name = getattr(source_element, "name", "source")
            msg = f"Upper element '{name}' is not a battery"
            raise TypeError(msg)
        if not hasattr(target_element, "stored_energy") or not hasattr(target_element, "capacity"):
            name = getattr(target_element, "name", "target")
            msg = f"Lower element '{name}' is not a battery"
            raise TypeError(msg)
        super().set_endpoints(source_element, target_element)

    @property
    def power_in_st(self) -> HighspyArray:
        """Power entering segment in source→target direction (upper→lower)."""
        return self._power_down

    @property
    def power_out_st(self) -> HighspyArray:
        """Power leaving segment in source→target direction."""
        return self._power_down

    @property
    def power_in_ts(self) -> HighspyArray:
        """Power entering segment in target→source direction (lower→upper)."""
        return self._power_up

    @property
    def power_out_ts(self) -> HighspyArray:
        """Power leaving segment in target→source direction."""
        return self._power_up

    @constraint(output=True, unit="$/kW")
    def balance_down_lower_bound(self) -> list[highs_linear_expression]:
        """Constraint: energy_down >= demand - unmet_demand."""
        _upper_battery, lower_battery = self._get_batteries()
        lower_stored = lower_battery.stored_energy
        capacity_lower = np.array(lower_battery.capacity)
        periods = self.periods

        energy_down = self._power_down * periods
        unmet_demand_energy = self.unmet_demand * periods
        demand = capacity_lower[:-1] - lower_stored[:-1]
        return list(energy_down >= demand - unmet_demand_energy)

    @constraint(output=True, unit="$/kW")
    def balance_down_slack_bound(self) -> list[highs_linear_expression]:
        """Constraint: unmet_demand >= demand - available."""
        upper_battery, lower_battery = self._get_batteries()
        lower_stored = lower_battery.stored_energy
        upper_stored = upper_battery.stored_energy
        capacity_lower = np.array(lower_battery.capacity)
        periods = self.periods

        unmet_demand_energy = self.unmet_demand * periods
        demand = capacity_lower[:-1] - lower_stored[:-1]
        available = upper_stored[:-1]
        return list(unmet_demand_energy >= demand - available)

    @constraint(output=True, unit="$/kW")
    def balance_up_upper_bound(self) -> list[highs_linear_expression]:
        """Constraint: energy_up <= excess + absorbed_excess."""
        _upper_battery, lower_battery = self._get_batteries()
        lower_stored = lower_battery.stored_energy
        capacity_lower = np.array(lower_battery.capacity)
        periods = self.periods

        energy_up = self._power_up * periods
        absorbed_excess_energy = self.absorbed_excess * periods
        excess = lower_stored[:-1] - capacity_lower[1:]
        return list(energy_up <= excess + absorbed_excess_energy)

    @constraint(output=True, unit="$/kW")
    def balance_up_slack_bound(self) -> list[highs_linear_expression]:
        """Constraint: absorbed_excess >= -excess."""
        _upper_battery, lower_battery = self._get_batteries()
        lower_stored = lower_battery.stored_energy
        capacity_lower = np.array(lower_battery.capacity)
        periods = self.periods

        absorbed_excess_energy = self.absorbed_excess * periods
        excess = lower_stored[:-1] - capacity_lower[1:]
        return list(absorbed_excess_energy >= -excess)

    @cost
    def slack_penalty_cost(self) -> list[highs_linear_expression]:
        """Return aggregated cost from slack penalty."""
        periods = self.periods
        unmet_cost = self.unmet_demand * periods * self._slack_penalty
        absorbed_cost = self.absorbed_excess * periods * self._slack_penalty
        return [*list(unmet_cost), *list(absorbed_cost)]

    @output
    def balance_power_down(self) -> OutputData:
        """Power flow from upper to lower section."""
        return OutputData(
            type=OutputType.POWER_FLOW, unit="kW", values=self._solver.vals(self._power_down), direction="+"
        )

    @output
    def balance_power_up(self) -> OutputData:
        """Power flow from lower to upper section."""
        return OutputData(
            type=OutputType.POWER_FLOW, unit="kW", values=self._solver.vals(self._power_up), direction="-"
        )

    @output
    def balance_unmet_demand(self) -> OutputData:
        """Unmet demand slack variable."""
        return OutputData(type=OutputType.POWER_FLOW, unit="kW", values=self._solver.vals(self.unmet_demand))

    @output
    def balance_absorbed_excess(self) -> OutputData:
        """Absorbed excess slack variable."""
        return OutputData(type=OutputType.POWER_FLOW, unit="kW", values=self._solver.vals(self.absorbed_excess))


__all__ = [
    "BALANCE_ABSORBED_EXCESS",
    "BALANCE_POWER_DOWN",
    "BALANCE_POWER_UP",
    "BALANCE_UNMET_DEMAND",
    "BatteryBalanceOutputName",
    "BatteryBalanceSegment",
    "BatteryBalanceSegmentSpec",
]
