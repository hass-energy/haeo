"""Shared fixtures for adapter element tests."""

from collections.abc import Mapping, Sequence
from typing import Final

from homeassistant.core import HomeAssistant
import numpy as np

from custom_components.haeo.core.adapters.policy_compilation import compile_policies
from custom_components.haeo.core.adapters.registry import collect_model_elements
from custom_components.haeo.core.model import ModelOutputName, ModelOutputValue, Network
from custom_components.haeo.core.schema import as_connection_target
from custom_components.haeo.core.schema.elements import ElementConfigData, ElementType
from custom_components.haeo.core.schema.elements.grid import GridConfigData
from custom_components.haeo.core.schema.elements.node import NodeConfigData

FORECAST_TIMES: Final[Sequence[float]] = (0.0, 1800.0)


def set_sensor(hass: HomeAssistant, entity_id: str, value: str, unit: str = "kW") -> None:
    """Set a sensor state in hass."""
    hass.states.async_set(entity_id, value, {"unit_of_measurement": unit})


def set_forecast_sensor(
    hass: HomeAssistant,
    entity_id: str,
    value: str,
    forecast: list[dict[str, object]],
    unit: str = "kW",
) -> None:
    """Set a sensor state with forecast attribute in hass."""
    hass.states.async_set(entity_id, value, {"unit_of_measurement": unit, "forecast": forecast})


def optimize_participants(
    participants: Mapping[str, ElementConfigData],
    *,
    periods: int = 1,
) -> Mapping[str, Mapping[ModelOutputName, ModelOutputValue]]:
    """Build a network of one-hour periods from element configs through their adapters, optimize, and return outputs."""
    compiled = compile_policies(collect_model_elements(participants), [])
    network = Network(name="test", periods=np.ones(periods))
    for element in compiled["elements"]:
        network.add(element)
    network.optimize()
    return {name: element.outputs() for name, element in network.elements.items()}


def bus_node(name: str) -> NodeConfigData:
    """Return a passive bus node."""
    return NodeConfigData(element_type=ElementType.NODE, name=name, role={"is_source": False, "is_sink": False})


def grid_at(name: str, bus: str, *, import_price: float, export_price: float, periods: int = 1) -> GridConfigData:
    """Return an unconstrained grid on the given bus with constant prices."""
    return GridConfigData(
        element_type=ElementType.GRID,
        name=name,
        connection=as_connection_target(bus),
        pricing={
            "price_source_target": np.full(periods, import_price),
            "price_target_source": np.full(periods, export_price),
        },
        power_limits={},
    )
