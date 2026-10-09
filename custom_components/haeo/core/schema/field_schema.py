"""Field schema metadata utilities."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class FieldSchemaInfo:
    """Schema metadata for a config field."""

    value_type: object
    is_optional: bool
