"""Network building and connectivity helpers for the HAEO integration."""

from collections.abc import Mapping, MutableMapping, Sequence
import logging
from typing import Any, cast

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
import numpy as np

from custom_components.haeo.const import CONF_ELEMENT_TYPE
from custom_components.haeo.elements import ELEMENT_TYPE_CONNECTION, ELEMENT_TYPES, ElementConfigData
from custom_components.haeo.model import Network
from custom_components.haeo.model.elements import ModelElementConfig
from custom_components.haeo.model.reactive import TrackedParam
from custom_components.haeo.repairs import create_disconnected_network_issue, dismiss_disconnected_network_issue
from custom_components.haeo.validation import format_component_summary, validate_network_topology

_LOGGER = logging.getLogger(__name__)


def collect_model_elements(
    participants: Mapping[str, ElementConfigData],
) -> list[ModelElementConfig]:
    """Collect and sort model elements from all participants."""
    all_model_elements: list[ModelElementConfig] = []
    for loaded_params in participants.values():
        element_type = loaded_params[CONF_ELEMENT_TYPE]
        model_elements = ELEMENT_TYPES[element_type].model_elements(loaded_params)
        all_model_elements.extend(model_elements)

    # Sort so connections are added last
    return sorted(
        all_model_elements,
        key=lambda e: e.get("element_type") == ELEMENT_TYPE_CONNECTION,
    )


async def create_network(
    entry: ConfigEntry,
    *,
    periods_seconds: Sequence[int],
    participants: Mapping[str, ElementConfigData],
) -> Network:
    """Create a new Network from configuration."""
    # Convert seconds to hours for model layer
    periods_hours = np.asarray(periods_seconds, dtype=float) / 3600
    net = Network(name=f"haeo_network_{entry.entry_id}", periods=periods_hours)

    if not participants:
        _LOGGER.info("No participants configured for hub - returning empty network")
        return net

    sorted_model_elements = collect_model_elements(participants)

    for model_element_config in sorted_model_elements:
        element_name = model_element_config.get("name")
        try:
            net.add(model_element_config)
        except Exception as e:
            msg = f"Failed to add model element '{element_name}' (type={model_element_config.get('element_type')})"
            _LOGGER.exception(msg)
            raise ValueError(msg) from e

    return net


def update_element(
    network: Network,
    element_config: ElementConfigData,
) -> None:
    """Update TrackedParams for a single element in the network."""
    element_type = element_config[CONF_ELEMENT_TYPE]
    model_elements = ELEMENT_TYPES[element_type].model_elements(element_config)

    def _iter_updates(
        values: Mapping[object, object],
        prefix: tuple[str, ...] = (),
    ) -> list[tuple[tuple[str, ...], object, bool]]:
        updates: list[tuple[tuple[str, ...], object, bool]] = []
        for key, value in values.items():
            if key in ("element_type", "name"):
                continue
            if isinstance(key, tuple):
                if not key or not all(isinstance(part, str) for part in key):
                    msg = f"Invalid update path {key!r} for element {values.get('name')!r}"
                    raise ValueError(msg)
                updates.append((key, value, True))
                continue
            if not isinstance(key, str):
                continue
            if isinstance(value, Mapping):
                updates.extend(_iter_updates(value, (*prefix, key)))
            else:
                updates.append(((*prefix, key), value, False))
        return updates

    def _resolve_path(obj: Any, path: tuple[str, ...], *, element_name: str | None) -> Any:
        current = obj
        for part in path[:-1]:
            if isinstance(current, Mapping):
                if part not in current:
                    msg = f"Invalid update path {path!r} for element {element_name!r}: missing key {part!r}"
                    raise ValueError(msg)
                current = current[part]
                continue
            if hasattr(current, part):
                current = getattr(current, part)
                continue
            msg = f"Invalid update path {path!r} for element {element_name!r}: missing attribute {part!r}"
            raise ValueError(msg)
        return current

    def _set_value(obj: Any, key: str, value: object, *, path: tuple[str, ...], element_name: str | None) -> None:
        if isinstance(obj, MutableMapping):
            if key not in obj:
                msg = f"Invalid update path {path!r} for element {element_name!r}: missing key {key!r}"
                raise ValueError(msg)
            obj[key] = value
            return

        descriptor = getattr(type(obj), key, None)
        if isinstance(descriptor, TrackedParam):
            setattr(obj, key, value)
            return
        if hasattr(obj, key):
            try:
                setattr(obj, key, value)
            except (AttributeError, TypeError) as exc:
                msg = f"Failed to update {path!r} for element {element_name!r}: {exc}"
                raise ValueError(msg) from exc
            return
        msg = f"Invalid update path {path!r} for element {element_name!r}: missing attribute {key!r}"
        raise ValueError(msg)

    for model_element_config in model_elements:
        element_name = model_element_config.get("name")

        if element_name not in network.elements:
            msg = f"Model element '{element_name}' not found in network during update"
            raise ValueError(msg)

        element = network.elements[element_name]
        for path, value, strict in _iter_updates(cast("Mapping[object, object]", model_element_config)):
            try:
                target = _resolve_path(element, path, element_name=element_name)
                _set_value(target, path[-1], value, path=path, element_name=element_name)
            except ValueError:
                if strict:
                    raise


async def evaluate_network_connectivity(
    hass: HomeAssistant,
    entry: ConfigEntry,
    *,
    participants: Mapping[str, ElementConfigData],
) -> None:
    """Validate the network connectivity for an entry and manage repair issues."""
    result = validate_network_topology(participants)

    if result.is_connected:
        dismiss_disconnected_network_issue(hass, entry.entry_id)
        return

    create_disconnected_network_issue(hass, entry.entry_id, result.components)

    summary = format_component_summary(result.components, separator=" | ")
    _LOGGER.warning(
        "Network %s has %d disconnected component(s): %s",
        entry.entry_id,
        result.num_components,
        summary or "no components",
    )


__all__ = [
    "collect_model_elements",
    "create_network",
    "evaluate_network_connectivity",
    "update_element",
]
