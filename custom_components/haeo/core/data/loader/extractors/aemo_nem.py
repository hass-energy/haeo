"""AEMO energy market forecast parser."""

from collections.abc import Mapping, Sequence
from datetime import datetime
import logging
from typing import Literal, NotRequired, Protocol, TypedDict, TypeGuard

from custom_components.haeo.core.state import EntityState
from custom_components.haeo.core.units import DeviceClass, UnitOfMeasurement

from .utils import is_parsable_to_datetime, parse_datetime_to_timestamp

_LOGGER = logging.getLogger(__name__)

Format = Literal["aemo_nem"]
DOMAIN: Format = "aemo_nem"

# Length of an AEMO pre-dispatch forecast block, used when a block has no end time
BLOCK_SECONDS = 30 * 60


class AemoForecastEntry(TypedDict):
    """Type definition for an AEMO forecast entry."""

    start_time: str | datetime
    end_time: NotRequired[str | datetime]
    price: float


class AemoNemAttributes(TypedDict):
    """Type definition for AEMO NEM State attributes."""

    forecast: Sequence[AemoForecastEntry]


class AemoNemState(Protocol):
    """Protocol for a State object with validated AEMO NEM forecast data."""

    attributes: AemoNemAttributes


class Parser:
    """Parser for AEMO energy market forecast data."""

    DOMAIN: Format = DOMAIN
    UNIT: UnitOfMeasurement = UnitOfMeasurement.DOLLAR_PER_KWH  # AEMO prices are in $/kWh
    DEVICE_CLASS: DeviceClass = DeviceClass.MONETARY

    @staticmethod
    def detect(state: EntityState) -> TypeGuard[AemoNemState]:
        """Check if data matches AEMO energy market format and narrow type."""

        if "forecast" not in state.attributes:
            return False

        forecast = state.attributes["forecast"]
        if not (isinstance(forecast, Sequence) and not isinstance(forecast, (str, bytes))) or not forecast:
            return False

        return all(
            isinstance(item, Mapping)
            and "start_time" in item
            and "price" in item
            and isinstance(item["price"], (int, float))
            and is_parsable_to_datetime(item["start_time"])
            and ("end_time" not in item or is_parsable_to_datetime(item["end_time"]))
            for item in forecast
        )

    @staticmethod
    def extract(state: AemoNemState) -> tuple[Sequence[tuple[int, float]], UnitOfMeasurement, DeviceClass]:
        """Extract forecast data from AEMO energy market format.

        Each price holds for its whole block, so each block emits two points,
        (start, price) and (end, price), making a step function rather than a
        ramp between blocks. Adjacent blocks share a boundary timestamp, which
        the caller separates so the fuser does not interpolate across it.

        A block ends at its end time. Without one, it ends where the next block
        starts, and the last block lasts one pre-dispatch interval.
        """
        blocks = sorted(
            ((parse_datetime_to_timestamp(item["start_time"]), item) for item in state.attributes["forecast"]),
            key=lambda block: block[0],
        )
        starts = [start for start, _ in blocks]
        next_starts = [*starts[1:], starts[-1] + BLOCK_SECONDS]

        parsed: list[tuple[int, float]] = []
        for (start, item), next_start in zip(blocks, next_starts, strict=True):
            end = parse_datetime_to_timestamp(item["end_time"]) if "end_time" in item else next_start
            parsed.append((start, item["price"]))
            parsed.append((end, item["price"]))
        return parsed, Parser.UNIT, Parser.DEVICE_CLASS
