"""Nordpool energy pricing forecast parser.

Nordpool provides energy pricing data via the nordpool HACS integration.
Sensors expose current price as the state value, with forecast data
in ``raw_today`` and ``raw_tomorrow`` attributes containing start/end
timestamps and price values.

See: https://github.com/custom-components/nordpool
"""

from collections.abc import Mapping, Sequence
import logging
from typing import Literal, Protocol, TypedDict, TypeGuard

from custom_components.haeo.core.state import EntityState
from custom_components.haeo.core.units import DeviceClass

from .utils import is_parsable_to_datetime, parse_datetime_to_timestamp

_LOGGER = logging.getLogger(__name__)

Format = Literal["nordpool"]
DOMAIN: Format = "nordpool"


class NordpoolForecastEntry(TypedDict):
    """Type definition for a Nordpool raw forecast entry."""

    start: str
    end: str
    value: float


class NordpoolAttributes(TypedDict):
    """Type definition for Nordpool State attributes."""

    raw_today: Sequence[NordpoolForecastEntry]
    raw_tomorrow: Sequence[NordpoolForecastEntry]
    currency: str


class NordpoolState(Protocol):
    """Protocol for a State object with validated Nordpool forecast data."""

    attributes: NordpoolAttributes


class Parser:
    """Parser for Nordpool energy pricing forecast data.

    Nordpool sensors provide pricing in the ``raw_today`` and ``raw_tomorrow``
    attributes as lists of ``{start, end, value}`` entries with ISO datetime strings.
    """

    DOMAIN: Format = DOMAIN
    DEVICE_CLASS: DeviceClass = DeviceClass.MONETARY

    @staticmethod
    def detect(state: EntityState) -> TypeGuard[NordpoolState]:
        """Check if data matches Nordpool format and narrow type."""
        if "raw_today" not in state.attributes:
            return False

        raw_today = state.attributes["raw_today"]
        if not (isinstance(raw_today, Sequence) and not isinstance(raw_today, (str, bytes))) or not raw_today:
            return False

        return all(
            isinstance(item, Mapping)
            and "start" in item
            and "end" in item
            and "value" in item
            and isinstance(item["value"], (int, float))
            and is_parsable_to_datetime(item["start"])
            and is_parsable_to_datetime(item["end"])
            for item in raw_today
        )

    @staticmethod
    def _unit(state: NordpoolState) -> str:
        """Derive the unit string from the currency attribute."""
        currency = state.attributes.get("currency", "EUR")
        return f"{currency}/kWh"

    @staticmethod
    def _parse_entries(entries: Sequence[NordpoolForecastEntry]) -> list[tuple[int, float]]:
        """Parse a list of Nordpool forecast entries into step-function boundary points.

        Each entry produces two points (start, value) and (end, value) to create
        a step function without linear interpolation between periods.
        """
        parsed: list[tuple[int, float]] = []
        for item in entries:
            start = parse_datetime_to_timestamp(item["start"])
            end = parse_datetime_to_timestamp(item["end"])
            value = item["value"]
            parsed.append((start, value))
            parsed.append((end, value))
        return parsed

    @staticmethod
    def extract(state: NordpoolState) -> tuple[Sequence[tuple[int, float]], str, DeviceClass]:
        """Extract forecast data from Nordpool format.

        Combines ``raw_today`` and ``raw_tomorrow`` (when available) into a
        single time series with step-function boundaries.
        """
        parsed = Parser._parse_entries(state.attributes["raw_today"])

        # Include tomorrow's data when available
        raw_tomorrow = state.attributes.get("raw_tomorrow")
        if raw_tomorrow:
            parsed.extend(Parser._parse_entries(raw_tomorrow))

        parsed.sort(key=lambda x: x[0])

        unit = Parser._unit(state)
        return parsed, unit, Parser.DEVICE_CLASS
