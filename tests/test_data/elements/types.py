"""Shared types for element test data."""

from collections.abc import Mapping
from typing import Any, TypedDict, TypeVar

from custom_components.haeo.elements import ElementConfigData, ElementConfigSchema
from custom_components.haeo.model import ModelOutputName
from custom_components.haeo.model.output_data import OutputData

SchemaT = TypeVar("SchemaT", bound=ElementConfigSchema)
DataT = TypeVar("DataT", bound=ElementConfigData)


class ElementValidCase[SchemaT: ElementConfigSchema, DataT: ElementConfigData](TypedDict):
    """Standardized structure for valid element test cases."""

    description: str
    element_type: str
    schema: SchemaT
    data: DataT
    model: list[dict[str, Any]]
    model_outputs: Mapping[str, Mapping[ModelOutputName, OutputData]]
    outputs: Mapping[str, Mapping[str, OutputData]]


__all__ = ["DataT", "ElementValidCase"]
