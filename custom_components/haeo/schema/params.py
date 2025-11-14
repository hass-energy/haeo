"""Parameters for schema generation and field validation."""

from collections.abc import Sequence
from typing import Any, TypedDict

from custom_components.haeo.data.loader.extractors import EntityMetadata


class SchemaParams(TypedDict, total=False):
    """Parameters that can be passed to schema_for_type and field validators.

    All fields are optional to allow flexibility in what gets passed.
    """

    entity_metadata: Sequence[EntityMetadata]
    participants: Sequence[str]
    current_element_name: str | None
    defaults: dict[str, Any] | None
