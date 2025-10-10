"""TypedDict definitions for element data returned from optimization."""

from typing import Literal, TypedDict


class BatteryElementData(TypedDict):
    """Data for battery element."""

    element_type: Literal["battery"]
    power: list[float]
    energy: list[float]


class GridElementData(TypedDict):
    """Data for grid element."""

    element_type: Literal["grid"]
    power: list[float]


class ConstantLoadElementData(TypedDict):
    """Data for constant load element."""

    element_type: Literal["constant_load"]
    power: list[float]


class ForecastLoadElementData(TypedDict):
    """Data for forecast load element."""

    element_type: Literal["forecast_load"]
    power: list[float]


class GeneratorElementData(TypedDict):
    """Data for generator element."""

    element_type: Literal["generator"]
    power: list[float]


class NetElementData(TypedDict):
    """Data for net element."""

    element_type: Literal["net"]
    power: list[float]


class ConnectionElementData(TypedDict):
    """Data for connection element."""

    element_type: Literal["connection"]
    power: list[float]


# Discriminated union of all element data types
ElementData = (
    BatteryElementData
    | GridElementData
    | ConstantLoadElementData
    | ForecastLoadElementData
    | GeneratorElementData
    | NetElementData
    | ConnectionElementData
)
