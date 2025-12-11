"""Shared types for element test data."""

from collections.abc import Mapping
from typing import Any, TypedDict, TypeVar

from custom_components.haeo.elements import ElementConfigData, ElementConfigSchema
from custom_components.haeo.model import ModelOutputName
from custom_components.haeo.model.output_data import OutputData

SchemaT = TypeVar("SchemaT", bound=ElementConfigSchema, covariant=True)
DataT = TypeVar("DataT", bound=ElementConfigData, covariant=True)


class ElementValidCase[SchemaT: ElementConfigSchema, DataT: ElementConfigData](TypedDict):
    """Standardized structure for valid element test cases."""

    description: str
    element_type: str
    schema: SchemaT
    data: DataT
    model: list[dict[str, Any]]
    model_outputs: Mapping[str, Mapping[ModelOutputName, OutputData]]
    outputs: Mapping[str, Mapping[str, OutputData]]


class InvalidSchemaCase[SchemaT: ElementConfigSchema](TypedDict):
    """Schema invalid case (schema cast to keep typing)."""

    description: str
    schema: SchemaT


class InvalidModelCase[DataT: ElementConfigData](TypedDict):
    """Invalid runtime model parameters for an element."""

    description: str
    element_type: str
    params: DataT


__all__ = [
    "ElementConfigData",
    "ElementConfigSchema",
    "DataT",
    "ElementValidCase",
    "InvalidModelCase",
    "InvalidSchemaCase",
    "SchemaT",
]
