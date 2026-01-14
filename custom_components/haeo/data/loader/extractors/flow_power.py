"""Flow Power HA energy pricing forecast parser.

Flow Power provides energy pricing for Australian customers with Price Efficiency
Adjustment (PEA) and Happy Hour export pricing. See: https://github.com/bolagnaise/Flow-Power-HA
"""

from collections.abc import Mapping, Sequence
import logging
from typing import Literal, Protocol, TypedDict, TypeGuard

from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.core import State

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
    UNIT: str = "$/kWh"  # Flow Power prices are in $/kWh
    DEVICE_CLASS: SensorDeviceClass = SensorDeviceClass.MONETARY

    @staticmethod
    def detect(state: State) -> TypeGuard[FlowPowerState]:
        """Check if data matches Flow Power format and narrow type."""

        if "forecast_dict" not in state.attributes:
            return False

        forecast_dict = state.attributes["forecast_dict"]
        if not isinstance(forecast_dict, Mapping) or not forecast_dict:
            return False

        return all(
            isinstance(key, str) and isinstance(value, (int, float)) and is_parsable_to_datetime(key)
            for key, value in forecast_dict.items()
        )

    @staticmethod
    def extract(state: FlowPowerState) -> tuple[Sequence[tuple[int, float]], str, SensorDeviceClass]:
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
        parsed: list[tuple[int, float]] = []

        for i, (start_ts, price) in enumerate(entries):
            if i < len(entries) - 1:
                # Use next timestamp as end of this period
                end_ts = entries[i + 1][0]
            elif len(entries) >= 2:  # noqa: PLR2004
                # Last entry: use same period length as previous
                prev_period = entries[-1][0] - entries[-2][0]
                end_ts = start_ts + prev_period
            else:
                # Single entry: no way to determine period, just emit start point
                parsed.append((start_ts, price))
                continue

            parsed.append((start_ts, price))
            parsed.append((end_ts, price))

        parsed.sort(key=lambda x: x[0])
        return parsed, Parser.UNIT, Parser.DEVICE_CLASS
