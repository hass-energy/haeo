"""Shared fixtures for adapter element tests."""

from collections.abc import Mapping, Sequence
from typing import Any, Final

from homeassistant.core import HomeAssistant
import numpy as np

from custom_components.haeo.core.adapters.policy_compilation import compile_policies
from custom_components.haeo.core.adapters.registry import collect_model_elements
from custom_components.haeo.core.model import ModelOutputName, ModelOutputValue, Network
from custom_components.haeo.core.schema.elements import ElementConfigData

FORECAST_TIMES: Final[Sequence[float]] = (0.0, 1800.0)


def set_sensor(hass: HomeAssistant, entity_id: str, value: str, unit: str = "kW") -> None:
    """Set a sensor state in hass."""
    hass.states.async_set(entity_id, value, {"unit_of_measurement": unit})


def set_forecast_sensor(
    hass: HomeAssistant,
    entity_id: str,
    value: str,
    forecast: list[dict[str, Any]],
    unit: str = "kW",
) -> None:
    """Set a sensor state with forecast attribute in hass."""
    hass.states.async_set(entity_id, value, {"unit_of_measurement": unit, "forecast": forecast})


def optimize_participants(
    participants: Mapping[str, ElementConfigData],
) -> Mapping[str, Mapping[ModelOutputName, ModelOutputValue]]:
    """Build a one-hour network from element configs through their adapters, optimize it, and return model outputs."""
    compiled = compile_policies(collect_model_elements(participants), [])
    network = Network(name="test", periods=np.array([1.0]))
    for element in compiled["elements"]:
        network.add(element)
    network.optimize()
    return {name: element.outputs() for name, element in network.elements.items()}
