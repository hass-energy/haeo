"""Data extractor package for different energy data providers."""

from collections.abc import Sequence
from dataclasses import dataclass
import logging
from typing import cast

from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers import entity_registry as er

from custom_components.haeo.const import convert_to_base_unit
from custom_components.haeo.schema.util import UnitSpec

from . import aemo_nem, amberelectric, open_meteo_solar_forecast, solcast_solar

_LOGGER = logging.getLogger(__name__)

_INVALID_STATES: tuple[str, ...] = ("unknown", "unavailable", "none")


@dataclass(frozen=True)
class EntityMetadata:
    """Metadata about entities extracted from Home Assistant state."""

    entity_id: str
    unit_of_measurement: str | None

    def is_compatible_with(self, accepted_units: "UnitSpec | Sequence[UnitSpec]") -> bool:
        """Check if this entity's unit is compatible with the accepted units."""
        # Import here to avoid circular dependency
        from custom_components.haeo.schema.util import matches_unit_spec  # noqa: PLC0415

        if self.unit_of_measurement is None:
            return False

        # Handle sequence of specs
        if isinstance(accepted_units, list):
            return any(matches_unit_spec(self.unit_of_measurement, spec) for spec in accepted_units)

        # Single spec - cast to UnitSpec since we know it's not a list
        return matches_unit_spec(self.unit_of_measurement, cast("UnitSpec", accepted_units))


# Union of all domain literal types from the extractor modules
ExtractorFormat = aemo_nem.Format | amberelectric.Format | open_meteo_solar_forecast.Format | solcast_solar.Format

# Union of all Extractor class types
DataExtractor = (
    type[aemo_nem.Parser]
    | type[amberelectric.Parser]
    | type[open_meteo_solar_forecast.Parser]
    | type[solcast_solar.Parser]
)

# Dictionary mapping domain strings to their extractor classes
_FORMATS: dict[ExtractorFormat, DataExtractor] = {
    aemo_nem.DOMAIN: aemo_nem.Parser,
    amberelectric.DOMAIN: amberelectric.Parser,
    open_meteo_solar_forecast.DOMAIN: open_meteo_solar_forecast.Parser,
    solcast_solar.DOMAIN: solcast_solar.Parser,
}


def detect_format(state: State) -> ExtractorFormat | None:
    """Detect the forecast data format based on its structure."""

    valid_formats: list[ExtractorFormat] = [domain for domain, parser in _FORMATS.items() if parser.detect(state)]

    if len(valid_formats) == 1:
        return valid_formats[0]

    if len(valid_formats) > 1:
        _LOGGER.warning("Multiple forecast formats detected: %s", valid_formats)

    return None


def _extract_simple_value(state: State, *, entity_id: str) -> float:
    """Extract a simple numeric value from a state, converting to base units.

    Args:
        state: The sensor state
        entity_id: The entity ID for error messages

    Returns:
        The converted value in base units

    Raises:
        ValueError: If the state is unavailable or cannot be converted to a float

    """
    if state.state in _INVALID_STATES:
        msg = f"Sensor {entity_id} is unavailable"
        raise ValueError(msg)

    try:
        raw_value = float(state.state)
    except (TypeError, ValueError) as err:
        msg = f"Cannot parse sensor value for {entity_id}: {state.state}"
        raise ValueError(msg) from err

    device_class = state.attributes.get("device_class")
    unit = state.attributes.get("unit_of_measurement")

    return convert_to_base_unit(raw_value, unit, device_class)


def extract_time_series(state: State, *, entity_id: str) -> float | list[tuple[int, float]]:
    """Extract time series data from a sensor state.

    Attempts to parse the state as a forecast using known formats. If no format
    is detected, falls back to returning the state value as a single float.

    Args:
        state: The sensor state
        entity_id: The entity ID for error messages

    Returns:
        Either a float for simple values, or a list of (timestamp_seconds, value) tuples
        for forecast data sorted by timestamp.
        All values are converted to base units (kW for power, kWh for energy, etc.).

    Raises:
        ValueError: If the state cannot be parsed as either a forecast or simple value

    """
    extractor_type = detect_format(state)

    if extractor_type is not None:
        extracted = _FORMATS[extractor_type].extract(state)
        if extracted:
            # Convert all forecast values to base units
            unit, device_class = get_extracted_units(state)
            return [(ts, convert_to_base_unit(value, unit, device_class)) for ts, value in extracted]

    return _extract_simple_value(state, entity_id=entity_id)


def get_extracted_units(state: State) -> tuple[str | None, SensorDeviceClass | None]:
    """Get the unit and device class for extracted data.

    Args:
        state: The sensor state

    Returns:
        Tuple of (unit, device_class) for the data. Returns state attributes if no format is detected.

    """
    extractor_type = detect_format(state)

    if extractor_type is None:
        unit = state.attributes.get("unit_of_measurement")
        device_class = state.attributes.get("device_class")
        return (unit, device_class)

    extractor = _FORMATS[extractor_type]
    return extractor.UNIT, extractor.DEVICE_CLASS


def extract_entity_metadata(hass: HomeAssistant) -> list["EntityMetadata"]:
    """Extract metadata for all sensor and input_number entities.

    This should be called once and the result passed to schema_for_type to avoid
    repeated entity registry and state lookups.

    Args:
        hass: Home Assistant instance

    Returns:
        List of entity metadata

    """
    entity_reg = er.async_get(hass)
    metadata: list[EntityMetadata] = []

    # Get all sensor and input_number entities
    for entity in entity_reg.entities.values():
        if entity.domain not in ("sensor", "input_number"):
            continue

        # Get current state to check unit
        state = hass.states.get(entity.entity_id)
        if state is None:
            continue

        # Check simple unit_of_measurement
        unit = state.attributes.get("unit_of_measurement")
        if unit:
            metadata.append(EntityMetadata(entity_id=entity.entity_id, unit_of_measurement=unit))
            continue

        # Check forecast format units
        detected_unit, _ = get_extracted_units(state)
        if detected_unit:
            metadata.append(EntityMetadata(entity_id=entity.entity_id, unit_of_measurement=detected_unit))

    return metadata
