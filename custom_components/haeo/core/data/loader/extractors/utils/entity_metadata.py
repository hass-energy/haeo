"""Entity metadata utilities."""

from dataclasses import dataclass

from custom_components.haeo.core.schema.util import UnitSpec


@dataclass(frozen=True)
class EntityMetadata:
    """Metadata about an entity's measurement capabilities."""

    entity_id: str
    unit_of_measurement: str | None

    def is_compatible_with(self, accepted_units: UnitSpec | list[UnitSpec]) -> bool:
        """Check if this entity's unit is compatible with the accepted units."""
        # Avoid circular import with schema module
        from custom_components.haeo.core.schema.util import matches_unit_spec  # noqa: PLC0415

        if self.unit_of_measurement is None:
            return False

        if isinstance(accepted_units, list):
            return any(matches_unit_spec(self.unit_of_measurement, spec) for spec in accepted_units)

        return matches_unit_spec(self.unit_of_measurement, accepted_units)
