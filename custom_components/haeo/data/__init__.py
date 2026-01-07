"""High-level data loading entrypoint.

This module exposes functions to create and update networks for optimization:
- `create_network()`: Initial network creation from configuration
- `update_network()`: Update existing network parameters for warm start

All field handling is delegated to specialised Loader implementations
found in sibling modules.

The adapter layer transforms configuration elements into model elements:
    Configuration Element (with entity IDs) →
    Adapter.load() →
    Configuration Data (with loaded values) →
    Adapter.model_elements() →
    Model Elements (pure optimization)
"""

from collections.abc import Mapping, Sequence
import contextlib
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from custom_components.haeo.const import CONF_ELEMENT_TYPE
from custom_components.haeo.elements import (
    ELEMENT_TYPE_CONNECTION,
    ELEMENT_TYPES,
    ElementConfigData,
    ElementConfigSchema,
)
from custom_components.haeo.model import Network

_LOGGER = logging.getLogger(__name__)


def _collect_model_elements(
    participants: Mapping[str, ElementConfigData],
) -> list[dict[str, Any]]:
    """Collect and sort model elements from all participants.

    Returns model elements sorted so connections come last (ensures
    source/target elements exist when connections are registered).
    """
    all_model_elements: list[dict[str, Any]] = []
    for loaded_params in participants.values():
        element_type = loaded_params[CONF_ELEMENT_TYPE]
        model_elements = ELEMENT_TYPES[element_type].model_elements(loaded_params)
        all_model_elements.extend(model_elements)

    # Sort so connections are added last
    return sorted(
        all_model_elements,
        key=lambda e: e.get("element_type") == ELEMENT_TYPE_CONNECTION,
    )


def config_available(config: ElementConfigSchema, *, hass: HomeAssistant, **kwargs: Any) -> bool:
    """Check if all required sensors/forecasts are available for a config.

    Delegates to the element-specific available() function from the registry.
    """
    element_type = config[CONF_ELEMENT_TYPE]
    entry = ELEMENT_TYPES[element_type]
    return entry.available(config, hass=hass, **kwargs)


async def load_element_configs(
    hass: HomeAssistant,
    participants: Mapping[str, ElementConfigSchema],
    forecast_times: Sequence[float],
) -> dict[str, ElementConfigData]:
    """Load sensor values for all element configurations.

    Converts ElementConfigSchema (with entity IDs) to ElementConfigData (with loaded values).

    Args:
        hass: Home Assistant instance
        participants: Mapping of element names to configurations with entity IDs
        forecast_times: Rounded timestamps for each optimization period (epoch seconds)

    Returns:
        Mapping of element names to loaded configurations with values

    Raises:
        ValueError: when required sensor/forecast data is missing

    """
    loaded_configs: dict[str, ElementConfigData] = {}
    forecast_times_list = list(forecast_times)

    for element_name, element_config in participants.items():
        entry = ELEMENT_TYPES[element_config[CONF_ELEMENT_TYPE]]

        # Load all fields using the element-specific load function
        loaded_params: ElementConfigData = await entry.load(
            element_config,
            hass=hass,
            forecast_times=forecast_times_list,
        )
        loaded_configs[element_name] = loaded_params

    return loaded_configs


async def create_network(
    entry: ConfigEntry,
    *,
    periods_seconds: Sequence[int],
    participants: Mapping[str, ElementConfigData],
) -> Network:
    """Create a new Network from configuration.

    This is the initial creation phase - use `update_network()` for
    subsequent updates to an existing network.

    Args:
        entry: Config entry
        periods_seconds: Sequence of optimization period durations in seconds
        participants: Mapping of element names to loaded configurations (with values)

    Returns:
        Network instance ready for optimization (may be empty if no participants)

    Raises:
        ValueError: when element creation fails.

    """
    # ==================================================================================
    # Unit boundary: seconds → hours
    # ==================================================================================
    # The coordinator and data loading layers work in seconds (practical for timestamps).
    # The model/optimization layer works in hours (necessary for kW·h = kWh math).
    # ==================================================================================
    periods_hours = [s / 3600 for s in periods_seconds]
    net = Network(name=f"haeo_network_{entry.entry_id}", periods=periods_hours)

    if not participants:
        _LOGGER.info("No participants configured for hub - returning empty network")
        return net

    sorted_model_elements = _collect_model_elements(participants)

    for model_element_config in sorted_model_elements:
        element_name = model_element_config.get("name")
        try:
            net.add(**model_element_config)
        except Exception as e:
            msg = f"Failed to add model element '{element_name}' (type={model_element_config.get('element_type')})"
            _LOGGER.exception(msg)
            raise ValueError(msg) from e

    return net


def update_network(
    network: Network,
    participants: Mapping[str, ElementConfigData],
) -> None:
    """Update TrackedParams on existing network elements for warm start.

    Updates parameter values on elements that already exist in the network.
    Elements not in the network are skipped (no new elements are created).

    Args:
        network: Existing network to update
        participants: Mapping of element names to loaded configurations (with values)

    """
    if not participants:
        return

    sorted_model_elements = _collect_model_elements(participants)

    for model_element_config in sorted_model_elements:
        element_name = model_element_config.get("name")

        if element_name not in network.elements:
            _LOGGER.warning(
                "Element '%s' not found in network during warm start update - skipping",
                element_name,
            )
            continue

        element = network.elements[element_name]
        for param_name, param_value in model_element_config.items():
            # Skip non-parameter fields
            # Update TrackedParam using element's __setitem__ interface
            # KeyError indicates not a TrackedParam (e.g., source/target on connections)
            with contextlib.suppress(KeyError):
                element[param_name] = param_value


__all__ = [
    "config_available",
    "create_network",
    "load_element_configs",
    "update_network",
]
