"""Entity metadata extraction utilities."""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

if TYPE_CHECKING:
    from custom_components.haeo.schema.util import UnitSpec


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


def extract_entity_metadata(hass: HomeAssistant) -> list[EntityMetadata]:
    """Extract metadata for all sensor and input_number entities.

    This should be called once and the result passed to schema_for_type to avoid
    repeated entity registry and state lookups.

    Args:
        hass: Home Assistant instance

    Returns:
        List of entity metadata

    """
    # Import here to avoid circular dependency
    from .time_series import get_extracted_units  # noqa: PLC0415

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

        # Use extractor system to get unit (handles both simple and forecast formats)
        unit, _ = get_extracted_units(state)
        if unit:
            metadata.append(EntityMetadata(entity_id=entity.entity_id, unit_of_measurement=unit))

    return metadata
