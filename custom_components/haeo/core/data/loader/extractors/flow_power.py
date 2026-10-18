"""Flow Power HA energy pricing forecast parser.

Flow Power provides energy pricing for Australian customers with Price Efficiency
Adjustment (PEA) and Happy Hour export pricing. See: https://github.com/bolagnaise/Flow-Power-HA
"""

from collections.abc import Mapping, Sequence
import logging
from typing import Literal, Protocol, TypedDict, TypeGuard

from custom_components.haeo.core.state import EntityState
from custom_components.haeo.core.units import DeviceClass, UnitOfMeasurement

from .utils import hold_until_next, is_parsable_to_datetime, parse_datetime_to_timestamp, step_points

_LOGGER = logging.getLogger(__name__)

Format = Literal["flow_power"]
DOMAIN: Format = "flow_power"


class FlowPowerAttributes(TypedDict):
    """Type definition for Flow Power State attributes."""

    forecast_dict: Mapping[str, float | int]


class FlowPowerState(Protocol):
    """Protocol for a State object with validated Flow Power forecast data."""

    attributes: FlowPowerAttributes


class Parser:
    """Parser for Flow Power pricing forecast data.

    Flow Power sensors provide forecast data in the `forecast_dict` attribute
    as a mapping of timestamp strings to price values.
    """

    DOMAIN: Format = DOMAIN
    UNIT: UnitOfMeasurement = UnitOfMeasurement.DOLLAR_PER_KWH  # Flow Power prices are in $/kWh
    DEVICE_CLASS: DeviceClass = DeviceClass.MONETARY

    @staticmethod
    def detect(state: EntityState) -> TypeGuard[FlowPowerState]:
        """Check if data matches Flow Power format and narrow type.

        Requires at least 2 entries to determine period length.
        """

        if "forecast_dict" not in state.attributes:
            return False

        forecast_dict = state.attributes["forecast_dict"]
        if not isinstance(forecast_dict, Mapping) or len(forecast_dict) < 2:  # noqa: PLR2004 (minimum 2 entries needed to determine period length)
            return False

        return all(
            isinstance(key, str) and isinstance(value, (int, float)) and is_parsable_to_datetime(key)
            for key, value in forecast_dict.items()
        )

    @staticmethod
    def extract(state: FlowPowerState) -> tuple[Sequence[tuple[int, float]], UnitOfMeasurement, DeviceClass]:
        """Extract forecast data from Flow Power format.

        Flow Power provides prices at the start of each period. Each price holds
        until the next period starts, and the last for as long as the period
        before it, so the periods become a step function.

        Returns timestamps in seconds as integers.
        """
        forecast_dict = state.attributes["forecast_dict"]
        prices = [(parse_datetime_to_timestamp(ts), float(price)) for ts, price in forecast_dict.items()]
        parsed = step_points(hold_until_next(prices))
        return parsed, Parser.UNIT, Parser.DEVICE_CLASS
