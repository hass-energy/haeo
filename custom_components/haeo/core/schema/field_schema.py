"""Field schema metadata utilities."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class FieldSchemaInfo:
    """Schema metadata for a config field."""

    value_type: Any
    is_optional: bool
