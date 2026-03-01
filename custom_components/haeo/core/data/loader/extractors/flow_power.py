"""Flow Power HA energy pricing forecast parser.

Flow Power provides energy pricing for Australian customers with Price Efficiency
Adjustment (PEA) and Happy Hour export pricing. See: https://github.com/bolagnaise/Flow-Power-HA
"""

from collections.abc import Mapping, Sequence
from itertools import pairwise
import logging
from typing import Literal, Protocol, TypedDict, TypeGuard

from custom_components.haeo.core.state import EntityState
from custom_components.haeo.core.units import DeviceClass, UnitOfMeasurement

from .utils import is_parsable_to_datetime, parse_datetime_to_timestamp

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
        if not isinstance(forecast_dict, Mapping) or len(forecast_dict) < 2:  # noqa: PLR2004
            return False

        return all(
            isinstance(key, str) and isinstance(value, (int, float)) and is_parsable_to_datetime(key)
            for key, value in forecast_dict.items()
        )

    @staticmethod
    def extract(state: FlowPowerState) -> tuple[Sequence[tuple[int, float]], UnitOfMeasurement, DeviceClass]:
        """Extract forecast data from Flow Power format.

        Flow Power provides prices at the start of each period. Emits boundary prices
        to create step functions: each window produces two points (start, price) and
        (end, price) to ensure constant pricing within the window.

        Period lengths are derived from the time between consecutive timestamps.
        The last period uses the same length as the previous period.

        Returns timestamps in seconds as integers.
        """
        forecast_dict = state.attributes["forecast_dict"]

        # Convert forecast_dict to sorted list of (timestamp, price) tuples
        entries: list[tuple[int, float]] = [
            (parse_datetime_to_timestamp(ts_str), float(price)) for ts_str, price in forecast_dict.items()
        ]
        entries.sort(key=lambda x: x[0])

        # Create step function with start and end points for each period
        # Use pairwise to get (current, next) pairs for all but last entry
        parsed: list[tuple[int, float]] = []
        for (start_ts, price), (end_ts, _) in pairwise(entries):
            parsed.append((start_ts, price))
            parsed.append((end_ts, price))

        # Handle last entry: repeat previous period length
        last_ts, last_price = entries[-1]
        prev_period = entries[-1][0] - entries[-2][0]
        parsed.append((last_ts, last_price))
        parsed.append((last_ts + prev_period, last_price))

        parsed.sort(key=lambda x: x[0])
        return parsed, Parser.UNIT, Parser.DEVICE_CLASS
